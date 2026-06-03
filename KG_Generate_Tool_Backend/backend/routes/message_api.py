from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from flask import Blueprint, jsonify, request
from bson.regex import Regex

from routes.llmGenKG_api import get_mongo_event_collection

message_bp = Blueprint("message_api", __name__)

_TIME_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
]


def _parse_time(value: Any, end_of_day: bool = False) -> Optional[datetime]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    for fmt in _TIME_FORMATS:
        try:
            dt = datetime.strptime(text, fmt)
            if fmt == "%Y-%m-%d" and end_of_day:
                return dt.replace(hour=23, minute=59, second=59)
            return dt
        except ValueError:
            continue

    try:
        # 兼容 ISO 格式
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        if text.count(":") == 0 and end_of_day:
            return dt.replace(hour=23, minute=59, second=59)
        return dt
    except ValueError:
        return None


def _extract_event_time(item: dict) -> Optional[datetime]:
    raw_data = item.get("raw_data") if isinstance(item.get("raw_data"), dict) else {}
    candidates = [
        item.get("event_time"),
        item.get("publish_time"),
        item.get("publishTime"),
        item.get("trade_date"),
        item.get("date"),
        item.get("time"),
        item.get("created_at"),
        item.get("createdAt"),
        raw_data.get("新闻时间"),
        raw_data.get("发布时间"),
        raw_data.get("发布日期"),
        raw_data.get("event_time"),
        raw_data.get("publish_time"),
    ]
    for value in candidates:
        dt = _parse_time(value)
        if dt is not None:
            return dt
    return None


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _is_dashboard_full_scan_request(data: dict, size: int) -> bool:
    """识别看板全量统计请求：无关键词过滤，且前端请求大页容量。"""
    if size < 5000:
        return False
    return not any(
        str(data.get(key) or "").strip()
        for key in ("keyword", "stock_code", "event_type")
    )


@message_bp.route("/api/message/list_all", methods=["POST"])
def list_all_messages():
    """统一事件列表查询：支持关键词、类型、时间范围、排序与分页。"""
    client = None
    try:
        data = request.get_json(silent=True) or {}

        page = max(1, _safe_int(data.get("page"), 1))
        size = min(max(1, _safe_int(data.get("size"), 20)), 200000)
        skip = (page - 1) * size

        stock_code = str(data.get("stock_code") or "").strip()
        keyword = str(data.get("keyword") or "").strip()
        event_type = str(data.get("event_type") or "").strip()

        start_raw = data.get("start_time") or data.get("start_date")
        end_raw = data.get("end_time") or data.get("end_date")
        start_dt = _parse_time(start_raw)
        end_dt = _parse_time(end_raw, end_of_day=True)

        sort_field = str(data.get("sort_field") or "event_time").strip()
        sort_order = -1 if _safe_int(data.get("sort_order"), -1) < 0 else 1

        client, collection = get_mongo_event_collection()

        conditions = []

        if stock_code:
            reg = Regex(stock_code, "i")
            conditions.append(
                {
                    "$or": [
                        {"data.symbol": reg},
                        {"data.company_of_interest": reg},
                    ]
                }
            )

        if keyword:
            reg = Regex(keyword, "i")
            conditions.append(
                {
                    "$or": [
                        {"data.title": reg},
                        {"data.event_description": reg},
                        {"data.summary": reg},
                        {"data.event_name": reg},
                        {"data.content": reg},
                    ]
                }
            )

        if event_type:
            conditions.append({"data.event_type": event_type})

        # 时间范围统一在 Python 层做精确过滤，避免遗漏使用不同时间字段的记录。

        query_filter = {"$and": conditions} if conditions else {}

        sort_map = {
            "event_time": "data.event_time",
            "trade_date": "data.trade_date",
            "event_type": "data.event_type",
            "symbol": "data.symbol",
            "_id": "_id",
        }
        mongo_sort_field = sort_map.get(sort_field, "data.event_time")

        cursor = collection.find(query_filter).sort(mongo_sort_field, sort_order)

        filtered_docs = []
        for doc in cursor:
            item = doc.get("data") or {}
            event_dt = _extract_event_time(item)

            if start_dt and (event_dt is None or event_dt < start_dt):
                continue
            if end_dt and (event_dt is None or event_dt > end_dt):
                continue

            filtered_docs.append((doc, item))

        total = len(filtered_docs)
        if _is_dashboard_full_scan_request(data, size):
            page_docs = filtered_docs
            page = 1
            size = total if total > 0 else size
        else:
            page_docs = filtered_docs[skip : skip + size]

        messages = []
        for doc, item in page_docs:
            oid = item.get("_id") or doc.get("_id")
            messages.append(
                {
                    "_id": oid,
                    "id": str(oid) if oid is not None else "",
                    "title": item.get("title") or item.get("event_name") or "",
                    "content": item.get("content") or item.get("summary") or "",
                    "event_description": item.get("event_description") or item.get("content") or "",
                    "event_time": item.get("event_time") or item.get("publish_time") or "",
                    "symbol": item.get("symbol") or item.get("company_of_interest") or "",
                    "company_of_interest": item.get("company_of_interest") or "",
                    "event_type": item.get("event_type") or "",
                    "event_subtype": item.get("event_subtype") or "",
                    "impact_level": item.get("impact_level") or "",
                    "sentiment": item.get("sentiment") or "",
                    "raw_data": item.get("raw_data") or item,
                }
            )

        return jsonify(
            {
                "code": 0,
                "msg": "ok",
                "data": {
                    "messages": messages,
                    "total": total,
                    "page": page,
                    "size": size,
                },
            }
        )
    except Exception as e:
        return jsonify({"code": 1, "msg": str(e), "data": {"messages": [], "total": 0}}), 500
    finally:
        if client:
            client.close()
