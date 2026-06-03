import hashlib
import json
import re
import time
import traceback
import uuid
from datetime import datetime
from decimal import Decimal
from flask import Blueprint, jsonify, request, send_file, Response
from database import get_client  # MySQL connection
import pandas as pd
from sqlalchemy import create_engine, text
from tqdm import tqdm
from pyvis.network import Network
import networkx as nx
import openai
from typing import Any, Dict, List, Optional, Union
import os
from neo4j import GraphDatabase
from pymongo import MongoClient
from threading import Lock, Thread
from agents.kg_quality_analysis_agent import (
    generate_kg_quality_analysis_report,
    generate_kg_quality_analysis_report_stream,
)

llmGenKG_bp = Blueprint('llmGenKG', __name__)

# 配置部分
MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '20040725',
    'database': 'finkg1',
    'charset': 'utf8mb4'
}

# Neo4j 配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "20040909"


class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def execute_query(self, query, parameters=None):
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return list(result)


# DeepSeek API配置
DEEPSEEK_API_KEY = "sk-ef3bb4d2e83f4d78849ba0145ad8b7e4"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# -------------------------
# 低成本省 token 工具（最小侵入，可一键回滚）
# -------------------------
_LLM_CACHE_LOCK = Lock()
_LLM_CACHE: Dict[str, Dict] = {}
_MASTER_TASKS_LOCK = Lock()
_MASTER_TASKS: Dict[str, Dict[str, Any]] = {}


def _env_int(name: str, default: int) -> int:
    try:
        v = os.getenv(name)
        return int(v) if v is not None and str(v).strip() else default
    except Exception:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")


def _smart_trim(text: str, limit: int) -> str:
    """
    在尽量不影响抽取效果的前提下压缩输入长度：
    - 保留开头/结尾（公告常在开头/结尾给关键信息）
    - 从中间挑选“信息密度高”的句子（包含数字/金额/比例/关键动词）
    """
    t = (text or "").strip()
    if not t or len(t) <= limit:
        return t

    head_len = min(2200, max(800, limit // 3))
    tail_len = min(1400, max(600, limit // 5))
    head = t[:head_len]
    tail = t[-tail_len:]
    mid = t[head_len:len(t) - tail_len]

    # 句切分：尽量宽松，兼容换行/分号
    parts = re.split(r"[。；;\n\r]+", mid)
    scored = []
    for s in parts:
        s2 = s.strip()
        if len(s2) < 12:
            continue
        score = 0
        if re.search(r"\d", s2):
            score += 2
        if re.search(r"(亿元|万元|%|比例|期限|日期|增持|减持|收购|出售|签署|中标|回购|解除|质押|担保|投资|并购|重组)", s2):
            score += 2
        if len(s2) >= 40:
            score += 1
        scored.append((score, s2))

    scored.sort(key=lambda x: x[0], reverse=True)
    picked = "。".join([s for _, s in scored[:24]])

    merged = f"{head}\n{picked}\n{tail}".strip()
    return merged[:limit]


def _cache_get(key: str):
    if not key:
        return None
    with _LLM_CACHE_LOCK:
        item = _LLM_CACHE.get(key)
        if not item:
            return None
        exp = item.get("expire_at")
        if exp and time.time() > exp:
            _LLM_CACHE.pop(key, None)
            return None
        return item.get("value")


def _cache_set(key: str, value, ttl_seconds: int):
    if not key:
        return
    with _LLM_CACHE_LOCK:
        # 简单限长，避免内存膨胀
        max_items = _env_int("LLM_CACHE_MAX_ITEMS", 256)
        if len(_LLM_CACHE) >= max_items:
            # FIFO 式淘汰（字典顺序在 py3.7+ 保序）
            oldest = next(iter(_LLM_CACHE.keys()), None)
            if oldest:
                _LLM_CACHE.pop(oldest, None)
        _LLM_CACHE[key] = {
            "expire_at": time.time() + max(1, ttl_seconds),
            "value": value,
        }


def _usage_log(tag: str, response):
    if not _env_bool("LLM_LOG_USAGE", True):
        return
    usage = getattr(response, "usage", None)
    if usage:
        try:
            print(f"[LLM usage] {tag}: prompt={getattr(usage, 'prompt_tokens', None)} "
                  f"completion={getattr(usage, 'completion_tokens', None)} total={getattr(usage, 'total_tokens', None)}")
        except Exception:
            print(f"[LLM usage] {tag}: {usage}")


# 初始化SQLAlchemy引擎
def get_sqlalchemy_engine():
    connection_str = f"mysql+pymysql://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}?charset={MYSQL_CONFIG['charset']}"
    return create_engine(connection_str)


# 清理公告文本
def clean_text(text: str) -> str:
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


_NODE_GENERIC_BLACKLIST = {
    "公司", "企业", "公告", "事项", "情况", "影响", "相关", "方面", "市场", "板块",
    "业务", "数据", "项目", "领域", "行业", "消息", "信息", "产品", "服务",
}


def _normalize_node_value(value: str) -> str:
    v = clean_text(str(value or ""))
    if not v:
        return ""
    v = v.replace("（", "(").replace("）", ")")
    v = re.sub(r"[\s\u3000]+", " ", v).strip()
    v = v.strip("，,。；;:：|/")
    return v


def _is_node_whitelisted(value: str, node_key: str, node_type: Any) -> bool:
    v = str(value or "")
    k = str(node_key or "")
    t = str(node_type or "").strip().lower()
    if t in ("1", "event", "事件"):
        return True
    if re.search(r"\b\d{6}(?:\.(?:SH|SZ))?\b", v, flags=re.IGNORECASE):
        return True
    if re.search(r"\b\d{5}\.HK\b", v, flags=re.IGNORECASE):
        return True
    if any(x in v for x in ("公司", "集团", "银行", "证券", "基金", "交易所", "证监", "法院")):
        return True
    if any(x in k for x in ("主体", "标的", "收购方", "被收购方", "监管", "机构")):
        return True
    return False


def _node_quality_score(node: dict) -> float:
    props = node.get("properties") if isinstance(node.get("properties"), dict) else {}
    score = float(props.get("confidence", 0.55) or 0.55)
    ch = str(props.get("channel") or "")
    if ch == "A+B":
        score += 0.5
    elif ch == "B":
        score += 0.3
    if props.get("sample_id"):
        score += 0.15
    if props.get("context"):
        score += 0.1
    if _is_node_whitelisted(node.get("value"), node.get("key"), node.get("type")):
        score += 0.25
    return score


def _sanitize_nodes_quality(nodes: list, project_id: str) -> list:
    """节点白名单/黑名单与归一策略：清理泛化节点并统一命名。"""
    if not nodes:
        return []

    min_len = _env_int("KG_NODE_MIN_VALUE_LEN", 2)
    grouped = {}

    for raw in nodes or []:
        if not isinstance(raw, dict):
            continue
        n = dict(raw)
        props = dict(n.get("properties") or {})
        t_raw = str(n.get("type", "0")).strip().lower()
        t_norm = 1 if t_raw in ("1", "event", "事件") else 0
        v_norm = _normalize_node_value(n.get("value"))
        if not v_norm or len(v_norm) < min_len:
            continue

        is_white = _is_node_whitelisted(v_norm, n.get("key"), t_norm)
        if (v_norm in _NODE_GENERIC_BLACKLIST or re.fullmatch(r"[\W_]+", v_norm)) and not is_white:
            continue

        n["type"] = t_norm
        n["value"] = v_norm
        n["key"] = str(n.get("key") or ("事件" if t_norm == 1 else "实体")).strip() or ("事件" if t_norm == 1 else "实体")
        props.setdefault("normalized", True)
        props.setdefault("project_id", project_id)
        n["properties"] = props
        key = (str(t_norm), v_norm.lower())
        grouped.setdefault(key, []).append(n)

    out = []
    for (_, _), items in grouped.items():
        best = max(items, key=_node_quality_score)
        bp = dict(best.get("properties") or {})
        aliases = set()
        for it in items:
            iv = str(it.get("value") or "").strip()
            if iv and iv != best.get("value"):
                aliases.add(iv)
            ip = it.get("properties") if isinstance(it.get("properties"), dict) else {}
            a = ip.get("aliases")
            if isinstance(a, list):
                for x in a:
                    if str(x or "").strip():
                        aliases.add(str(x).strip())
            for k, v in ip.items():
                if k not in bp and v not in (None, ""):
                    bp[k] = v
        if aliases:
            bp["aliases"] = sorted(aliases)
        best["properties"] = bp
        if not best.get("id"):
            best["id"] = hashlib.md5(
                f"{project_id}_{best.get('type')}_{best.get('value')}".encode("utf-8")
            ).hexdigest()
        out.append(best)

    return out


def _legacy_relation_candidates_from_sample(sample_nodes: list, content: str, max_pairs: int = 140) -> list:
    """兼容旧版：同样本内 value 出现即入候选（用于评测基线对照）。"""
    if not sample_nodes or not content:
        return []
    pairs = []
    seen = set()
    values = [
        (str(n.get("id") or "").strip(), str(n.get("value") or "").strip())
        for n in sample_nodes
        if str(n.get("id") or "").strip() and str(n.get("value") or "").strip()
    ]
    for fid, fv in values:
        if not fv or fv not in content:
            continue
        for tid, tv in values:
            if not tv or fid == tid or tv not in content:
                continue
            k = (fid, tid)
            if k in seen:
                continue
            seen.add(k)
            pairs.append((fid, tid, str(content)[:200]))
            if len(pairs) >= max_pairs:
                return pairs
    return pairs


def get_mongo_event_collection():
    """获取 MongoDB event_data 集合。"""
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    mongo_db_name = os.getenv("MONGO_DB", "finkg1")
    mongo_collection_name = os.getenv("MONGO_COLLECTION", "event_data")
    client = MongoClient(mongo_uri)
    return client, client[mongo_db_name][mongo_collection_name]


def fetch_samples_from_mongo(sample_ids: list):
    """根据样本 ID 列表从 MongoDB 获取样本 JSON 数据。"""
    if not sample_ids:
        return []

    str_ids = [str(i) for i in sample_ids if i is not None and str(i).strip() and str(i) != 'None']
    if not str_ids:
        return []

    client = None
    try:
        client, collection = get_mongo_event_collection()
        cursor = collection.find({"data._id": {"$in": str_ids}})

        samples = []
        for doc in cursor:
            item = doc.get("data", {})
            item_id = str(item.get("_id") or doc.get("item_id") or "")
            if not item_id:
                continue
            samples.append({
                "id": item_id,
                "title": item.get("title") or item.get("event_name") or "",
                "content": (
                    item.get("event_description")
                    or item.get("content")
                    or (item.get("raw_data") or {}).get("新闻内容")
                    or item.get("summary")
                    or ""
                ),
                "event_time": item.get("event_time", ""),
                "raw_data": item
            })

        # 按请求顺序返回，保证前端可复现
        order_map = {sid: idx for idx, sid in enumerate(str_ids)}
        samples.sort(key=lambda x: order_map.get(str(x.get("id", "")), 10 ** 9))
        return samples
    except Exception as e:
        print(f"[MasterAgent] 从 MongoDB 获取样本失败: {e}")
        traceback.print_exc()
        return []
    finally:
        if client:
            client.close()


def extract_nodes_rule_based(content: str, project_id: str) -> Dict:
    """
    通道A（高召回）：规则+关键词粗抽。
    说明：这是轻量启发式抽取，用于减少漏召回，后续由 LLM 通道与 MergeAgent 纠偏。
    """
    if not content:
        return {"nodes": []}
    patterns = [
        (
            "事件",
            r"(签署|收购|增持|减持|中标|停牌|复牌|重组|并购|诉讼|处罚|回购|涨停|跌停|股价异动|价格异动|业绩预增|业绩预减|扭亏|亏损扩大|盈利预警|回购注销|限售解禁|大宗交易|股份质押|增持计划|减持计划|问询函|立案调查|业绩快报|分红派息|融资担保|关联交易|龙头异动事件|行业跌幅异常事件|下跌一致性事件)"
        ),
        (
            "实体",
            r"([A-Za-z0-9\u4e00-\u9fa5]{2,30}(?:公司|集团|银行|证券|基金|板块|指数|油田|油气|原油|黄金|期货))"
        ),
    ]
    nodes = []
    seen = set()
    for node_key, pattern in patterns:
        for m in re.finditer(pattern, content):
            value = (m.group(0) or "").strip()
            if not value:
                continue
            ntype = 1 if node_key == "事件" else 0
            dedupe_key = (ntype, value)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            node_id = hashlib.md5(f"rb_{ntype}_{value}_{project_id}".encode("utf-8")).hexdigest()
            nodes.append({
                "id": node_id,
                "type": ntype,
                "value": value,
                "key": node_key,
                "properties": {
                    "project_id": project_id,
                    "source": "规则抽取",
                    "channel": "A",
                    "confidence": 0.55,
                    "context": content[max(0, m.start() - 30): m.end() + 30],
                },
            })
    return {"nodes": nodes}


def _merge_nodes_dual_channel(rule_nodes: list, llm_nodes: list) -> list:
    merged = {}
    for n in rule_nodes or []:
        key = (str(n.get("type")), str(n.get("value", "")).strip().lower())
        item = dict(n)
        props = dict(item.get("properties") or {})
        props["confidence"] = max(float(props.get("confidence", 0.55)), 0.55)
        props["channel"] = "A"
        item["properties"] = props
        merged[key] = item
    for n in llm_nodes or []:
        key = (str(n.get("type")), str(n.get("value", "")).strip().lower())
        if key in merged:
            base = merged[key]
            bp = dict(base.get("properties") or {})
            np = dict(n.get("properties") or {})
            bp.update(np)
            bp["channel"] = "A+B"
            bp["confidence"] = max(float(bp.get("confidence", 0.55)), 0.9)
            base["properties"] = bp
            if not base.get("id"):
                base["id"] = n.get("id")
            merged[key] = base
        else:
            item = dict(n)
            props = dict(item.get("properties") or {})
            props["channel"] = "B"
            props["confidence"] = max(float(props.get("confidence", 0.75)), 0.75)
            item["properties"] = props
            merged[key] = item
    return list(merged.values())


def run_node_agent(
    samples: list,
    project_id: str,
    batch_size: int = 20,
    mode: str = "full",
    persistence_mode: str = "replace",
):
    """Node Agent：双通道抽取（A 高召回 + B 高精度）并合并打分后入库。"""
    from agents.property_enrichment_agent import enrich_nodes_properties

    all_nodes = []
    step = max(1, int(batch_size or 20))
    for i in range(0, len(samples or []), step):
        batch = samples[i:i + step]
        for sample in batch:
            content = clean_text(sample.get("content", ""))
            if not content:
                continue
            rule_result = extract_nodes_rule_based(content, project_id)
            llm_result = extract_nodes_with_llm(content, project_id)
            merged_nodes = _merge_nodes_dual_channel(
                rule_result.get("nodes", []),
                llm_result.get("nodes", []),
            )
            sid = str(sample.get("id", "") or "").strip()
            for node in merged_nodes:
                node.setdefault("properties", {})
                if isinstance(node["properties"], dict) and sid:
                    node["properties"]["sample_id"] = sid
            all_nodes.extend(merged_nodes)

    persist = str(persistence_mode or "replace").strip().lower()
    if all_nodes:
        # 在整个全量列表中去重，避免存入数据库时报 Duplicate entry 错
        unique_nodes = {}
        for n in all_nodes:
            nid = n.get("id")
            if nid and nid not in unique_nodes:
                unique_nodes[nid] = n
        all_nodes_dedup = list(unique_nodes.values())
        if _env_bool("KG_NODE_SANITIZE_ENABLED", True):
            all_nodes_dedup = _sanitize_nodes_quality(all_nodes_dedup, project_id)
        all_nodes_dedup = enrich_nodes_properties(all_nodes_dedup, samples, project_id)

        if persist == "merge":
            merge_nodes_to_database(all_nodes_dedup, project_id)
            return get_nodes_from_database(project_id)
        save_nodes_to_database(all_nodes_dedup, project_id)
        return all_nodes_dedup
    return all_nodes


def _infer_cooccurrence_relation(content: str) -> tuple:
    """
    规则通道：根据正文关键词推断 type/value，尽量避免通篇「相关」。
    返回 (relation_type, relation_val)
    """
    if any(k in content for k in ("发布", "披露", "公告", "公告称", "公布")):
        return "披露关系", "发布公告"
    if any(k in content for k in ("涨停", "跌停", "涨跌幅", "股价", "股价异动", "价格异动", "振幅", "成交量", "换手率", "放量", "缩量")):
        return "行情波动关系", "触发市场异动"
    if any(k in content for k in ("净利润", "营收", "收入", "亏损", "扭亏", "预增", "预减", "业绩快报", "盈利预警")):
        return "业绩关系", "披露业绩变动"
    if any(k in content for k in ("问询函", "警示函", "处罚", "立案", "调查", "监管", "交易所")):
        return "监管关系", "触发监管事项"
    if any(k in content for k in ("融资", "借款", "发债", "债券", "担保", "质押", "授信")):
        return "融资关系", "发生融资安排"
    if any(k in content for k in ("板块", "指数", "领涨", "领跌", "赛道", "行业")):
        return "行业联动关系", "带动板块波动"
    if any(k in content for k in ("导致", "引发", "促使", "使得", "造成", "带来")):
        return "因果关系", "因果影响"
    if any(k in content for k in ("随后", "之后", "继而", "此后", "其后", "先于", "此前")):
        return "时序关系", "时间先后"
    if any(k in content for k in ("控股", "持股", "参股", "子公司", "母公司", "表决权", "一致行动")):
        return "股权关系", "股权联系"
    if any(k in content for k in ("签订", "协议", "合同", "认购", "认购书")):
        return "协议关系", "协议约定"
    if any(k in content for k in ("供应", "采购", "客户", "供应商", "中标", "招标", "订单")):
        return "供应链关系", "业务往来"
    if any(k in content for k in ("任职", "董事", "监事", "高管", "法定代表人", "聘任", "辞职")):
        return "人事关系", "人事关联"
    if any(k in content for k in ("担保", "质押", "抵押", "借款", "还款", "债务")):
        return "财务关联", "债权债务"
    if any(k in content for k in ("收购", "并购", "重组", "注入", "出售", "转让")):
        return "资产交易关系", "并购或交易"
    # 仅共现、无语义线索时：不用「相关」一词，避免与 LLM 泛化重合
    return "文本共现", "同段共现"


def _should_drop_placeholder_cooccurrence_edge(edge: dict) -> bool:
    """
    丢弃「文本共现 / 同段共现 / 同样本关联」等占位边。
    设置 KG_KEEP_COOC_EDGES=true 可保留旧行为。
    """
    if _env_bool("KG_KEEP_COOC_EDGES", False):
        return False
    if not isinstance(edge, dict):
        return True
    t = (edge.get("type") or "").strip()
    v = (edge.get("value") or "").strip()
    if t == "文本共现":
        return True
    if v in {"同段共现", "同样本关联"}:
        return True
    if t == "语义关系" and v in {"披露事项关联", "业务往来", "人事关联", "财务往来"}:
        return False
    if t in {"同样本关系", "样本关联"}:
        return True
    return False


def _slice_context_by_keywords(content: str, keywords: list, fallback: int = 90) -> str:
    text = clean_text(content or "")
    if not text:
        return ""
    for kw in keywords:
        idx = text.find(kw)
        if idx >= 0:
            start = max(0, idx - 18)
            end = min(len(text), idx + 68)
            return text[start:end]
    return text[:fallback]


def _infer_semantic_repair_edge(from_node: dict, to_node: dict, sample_text: str) -> Optional[dict]:
    content = clean_text(sample_text or "")
    if not content:
        return None

    from_type = str(from_node.get("type", "")).strip().lower()
    to_type = str(to_node.get("type", "")).strip().lower()
    from_value = str(from_node.get("value", "")).strip()
    to_value = str(to_node.get("value", "")).strip()

    def _pack(rel_type: str, rel_value: str, keywords: list) -> dict:
        return {
            "type": rel_type,
            "value": rel_value,
            "context": _slice_context_by_keywords(content, keywords),
        }

    entity_event_pair = {from_type, to_type} <= {"0", "1", "实体", "事件", "event"} and from_type != to_type
    if entity_event_pair:
        entity_node = from_node if from_type in ("0", "实体") else to_node
        event_node = to_node if entity_node is from_node else from_node
        event_text = " ".join([
            str(event_node.get("value", "")),
            str(event_node.get("key", "")),
            str((event_node.get("properties") or {}).get("context", "")),
            content,
        ])

        if any(k in event_text for k in ("公告", "发布", "披露", "公布")):
            rel = _pack("披露关系", "发布公告", ["发布", "披露", "公告", "公布"])
        elif any(k in event_text for k in ("涨停", "跌停", "涨跌幅", "股价", "股价异动", "价格异动", "成交量", "换手率", "放量", "缩量", "板块")):
            rel = _pack("行情波动关系", "触发市场异动", ["涨停", "跌停", "涨跌幅", "股价", "价格异动", "成交量", "换手率", "板块"])
        elif any(k in event_text for k in ("净利润", "营收", "亏损", "扭亏", "预增", "预减", "业绩快报", "盈利预警")):
            rel = _pack("业绩关系", "披露业绩变动", ["净利润", "营收", "亏损", "扭亏", "预增", "预减", "业绩快报", "盈利预警"])
        elif any(k in event_text for k in ("问询函", "处罚", "立案", "调查", "监管", "警示函")):
            rel = _pack("监管关系", "触发监管事项", ["问询函", "处罚", "立案", "调查", "监管", "警示函"])
        elif any(k in event_text for k in ("增持", "减持", "回购", "股权", "质押", "解禁")):
            rel = _pack("股权关系", "发生股权变动", ["增持", "减持", "回购", "股权", "质押", "解禁"])
        elif any(k in event_text for k in ("融资", "借款", "担保", "发债", "债券", "授信")):
            rel = _pack("融资关系", "发生融资安排", ["融资", "借款", "担保", "发债", "债券", "授信"])
        else:
            return None

        if entity_node is from_node:
            return {"from": from_node, "to": to_node, **rel}
        return {"from": to_node, "to": from_node, **rel}

    pair_text = f"{from_value} {to_value} {content}"
    if any(k in pair_text for k in ("签署", "协议", "合同", "合作")):
        return {"from": from_node, "to": to_node, **_pack("协议关系", "签署合作协议", ["签署", "协议", "合同", "合作"])}
    if any(k in pair_text for k in ("供应", "采购", "客户", "供应商", "订单", "中标")):
        return {"from": from_node, "to": to_node, **_pack("供应链关系", "形成业务往来", ["供应", "采购", "客户", "供应商", "订单", "中标"])}
    if any(k in pair_text for k in ("持股", "增持", "减持", "控股", "实控人", "股东")):
        return {"from": from_node, "to": to_node, **_pack("股权关系", "形成股权联系", ["持股", "增持", "减持", "控股", "实控人", "股东"])}
    if any(k in pair_text for k in ("处罚", "问询", "监管", "调查", "警示函")):
        return {"from": from_node, "to": to_node, **_pack("监管关系", "实施监管动作", ["处罚", "问询", "监管", "调查", "警示函"])}
    return None


def _repair_isolated_nodes_with_sample_semantic_edges(
    nodes: list,
    edges: list,
    project_id: str,
    samples: list,
) -> list:
    """
    仅针对孤立节点做保守补边，但只在样本文本中能推断出真实语义关系时才补。
    明确禁止生成「同样本关联」这类无业务意义的伪边。
    """
    if _env_bool("KG_DISABLE_ISOLATED_EDGE_REPAIR", False):
        return edges or []

    safe_edges = list(edges or [])
    if not nodes:
        return safe_edges

    node_map = {
        str(n.get("id")): n
        for n in (nodes or [])
        if isinstance(n, dict) and n.get("id")
    }
    if not node_map:
        return safe_edges

    degree = {nid: 0 for nid in node_map.keys()}
    undirected_pairs = set()
    for e in safe_edges:
        sid = str(e.get("from") or e.get("source") or "")
        tid = str(e.get("to") or e.get("target") or "")
        if sid in degree:
            degree[sid] += 1
        if tid in degree:
            degree[tid] += 1
        if sid and tid and sid != tid:
            undirected_pairs.add(tuple(sorted([sid, tid])))

    isolated_ids = [nid for nid, d in degree.items() if d == 0]
    if not isolated_ids:
        return safe_edges

    min_count = max(1, _env_int("KG_ISOLATED_REPAIR_MIN_COUNT", 2))
    if len(isolated_ids) < min_count:
        return safe_edges

    max_add = max(1, _env_int("KG_ISOLATED_REPAIR_MAX_EDGES", 80))
    max_per_sample = max(1, _env_int("KG_ISOLATED_REPAIR_MAX_PER_SAMPLE", 3))
    sample_text_map = {
        str((sample or {}).get("id", "")).strip(): clean_text((sample or {}).get("content", ""))
        for sample in (samples or [])
        if str((sample or {}).get("id", "")).strip()
    }

    # 仅在同一 sample_id 内补语义明确的边，降低误连风险。
    sample_groups: Dict[str, list] = {}
    for nid in isolated_ids:
        n = node_map.get(nid) or {}
        props = n.get("properties") if isinstance(n.get("properties"), dict) else {}
        sample_id = str(props.get("sample_id") or "").strip()
        if not sample_id:
            continue
        sample_groups.setdefault(sample_id, []).append(n)

    added = []
    for sample_id, group_nodes in sample_groups.items():
        if len(added) >= max_add:
            break
        if len(group_nodes) < 2:
            continue

        events = []
        entities = []
        for n in group_nodes:
            ntype = str(n.get("type", "")).strip().lower()
            if ntype in ("1", "event", "事件"):
                events.append(n)
            else:
                entities.append(n)

        candidates = []
        if events and entities:
            anchor = events[0]
            for ent in entities:
                candidates.append((str(ent.get("id")), str(anchor.get("id"))))
        else:
            # 兜底：同样本且同为孤立，仅连一条最小生成边
            ordered = sorted(group_nodes, key=lambda x: str(x.get("id")))
            for i in range(len(ordered) - 1):
                candidates.append((str(ordered[i].get("id")), str(ordered[i + 1].get("id"))))

        local_added = 0
        sample_text = sample_text_map.get(sample_id, "")
        for sid, tid in candidates:
            if len(added) >= max_add or local_added >= max_per_sample:
                break
            if not sid or not tid or sid == tid:
                continue
            pair_key = tuple(sorted([sid, tid]))
            if pair_key in undirected_pairs:
                continue
            from_node = node_map.get(sid)
            to_node = node_map.get(tid)
            if not from_node or not to_node:
                continue
            inferred = _infer_semantic_repair_edge(from_node, to_node, sample_text)
            if not inferred:
                continue

            edge_id = hashlib.md5(
                f"iso_{sid}_{tid}_{project_id}_{sample_id}_{inferred['type']}_{inferred['value']}".encode("utf-8")
            ).hexdigest()
            added.append({
                "id": edge_id,
                "type": inferred["type"],
                "from": inferred["from"].get("id"),
                "to": inferred["to"].get("id"),
                "from_node": inferred["from"],
                "to_node": inferred["to"],
                "value": inferred["value"],
                "eventRel": inferred["value"],
                "project_id": project_id,
                "properties": {
                    "source": "语义补边",
                    "channel": "repair",
                    "confidence": 0.58,
                    "sample_id": sample_id,
                    "repair": True,
                    "context": inferred["context"],
                },
            })
            undirected_pairs.add(pair_key)
            local_added += 1

    if added:
        print(f"[RelationAgent] 语义补边: +{len(added)}")
    return safe_edges + added


_GENERIC_RELATION_VALUES = frozenset({
    "相关", "关联", "影响", "涉及", "有关", "联系", "关系",
})


def _normalize_relation_edge(edge: dict) -> dict:
    """将 LLM/规则输出的泛化 relation value 替换为更可读的短语，并同步 eventRel。"""
    if not isinstance(edge, dict):
        return edge
    v = (edge.get("value") or "").strip()
    t = (edge.get("type") or "").strip()
    props = edge.get("properties") if isinstance(edge.get("properties"), dict) else {}
    ctx = clean_text(str(props.get("context") or ""))
    short_or_generic = (
        len(v) < 2
        or v in _GENERIC_RELATION_VALUES
        or v in {"无", "不明", "-", "—"}
    )
    if not short_or_generic:
        if not edge.get("eventRel"):
            edge["eventRel"] = v
        return edge
    inferred_type, inferred_val = _infer_cooccurrence_relation(ctx) if ctx else (None, None)
    if ctx and inferred_val != "同段共现":
        edge["type"] = inferred_type or t or "语义关系"
        edge["value"] = inferred_val
    else:
        type_defaults = {
            "因果关系": "因果影响",
            "时序关系": "时间先后",
            "股权关系": "股权联系",
            "协议关系": "协议约定",
            "供应链关系": "业务往来",
            "人事关系": "人事关联",
            "财务关联": "财务往来",
            "资产交易关系": "并购或交易",
            "文本共现": "同段共现",
        }
        edge["value"] = type_defaults.get(t, "披露事项关联")
        edge["type"] = t if t else "语义关系"
    edge["eventRel"] = edge["value"]
    return edge


def _normalize_finance_edge_direction(edge: dict) -> dict:
    """将常见金融实体-事件边归一到“主体/实体 -> 事件/事项”的方向。"""
    if not isinstance(edge, dict):
        return edge
    from_node = edge.get("from_node") if isinstance(edge.get("from_node"), dict) else {}
    to_node = edge.get("to_node") if isinstance(edge.get("to_node"), dict) else {}
    from_type = str(from_node.get("type", "")).strip().lower()
    to_type = str(to_node.get("type", "")).strip().lower()
    rel_type = str(edge.get("type", "")).strip()

    entity_like = {"0", "实体"}
    event_like = {"1", "事件", "event"}
    entity_first_types = {
        "披露关系",
        "行情波动关系",
        "业绩关系",
        "监管关系",
        "股权关系",
        "融资关系",
        "行业联动关系",
        "资产交易关系",
    }
    if from_type in event_like and to_type in entity_like and rel_type in entity_first_types:
        edge["from"], edge["to"] = edge.get("to"), edge.get("from")
        edge["from_node"], edge["to_node"] = to_node, from_node
    return edge


def _edge_quality_score(edge: dict) -> float:
    props = edge.get("properties") if isinstance(edge.get("properties"), dict) else {}
    conf = float(props.get("confidence", 0.55))
    v = (edge.get("value") or "").strip()
    generic = len(v) < 2 or v in _GENERIC_RELATION_VALUES or v in {"无", "不明"}
    score = conf
    if not generic:
        score += 2.0
    else:
        score -= 2.0
    if 3 <= len(v) <= 24:
        score += 0.35
    ch = props.get("channel") or ""
    if ch == "B":
        score += 0.35
    elif ch == "A+B":
        score += 0.55
    if edge.get("type") == "文本共现":
        score -= 0.2
    return score


def _nodes_for_sample(nodes: list, sample: dict, sample_content: str, max_nodes: int = 80) -> list:
    """优先按 sample_id 取节点；为防漏召回，再补充 value 出现在样本文本中的节点。"""
    sid = str((sample or {}).get("id") or "").strip()
    content = str(sample_content or "")
    selected = []
    seen = set()

    for n in nodes or []:
        if not isinstance(n, dict):
            continue
        nid = str(n.get("id") or "").strip()
        if not nid or nid in seen:
            continue
        props = n.get("properties") if isinstance(n.get("properties"), dict) else {}
        nsid = str(props.get("sample_id") or "").strip()
        val = str(n.get("value") or "").strip()
        if nsid and sid and nsid == sid:
            selected.append(n)
            seen.add(nid)
            continue
        if val and len(val) >= 2 and val in content:
            selected.append(n)
            seen.add(nid)

    # 保守上限，避免单样本节点过多导致 LLM 抽取不稳定。
    if len(selected) > max_nodes:
        selected = selected[:max_nodes]
    return selected


def _split_sentences_for_rel(text: str) -> list:
    t = str(text or "").strip()
    if not t:
        return []
    # 兼容中文公告常见断句符。
    parts = re.split(r"(?<=[。！？!?；;\n\r])", t)
    out = []
    for p in parts:
        s = str(p or "").strip()
        if len(s) >= 6:
            out.append(s)
    return out


def _build_relation_candidates_from_sample(sample_nodes: list, content: str, max_pairs: int = 140) -> list:
    """基于句级共现生成候选对，降低“同文全量两两配对”噪声。返回 [(from_id, to_id, context)]."""
    if not sample_nodes or not content:
        return []

    id_to_node = {
        str(n.get("id")): n
        for n in sample_nodes
        if isinstance(n, dict) and n.get("id") and str(n.get("value") or "").strip()
    }
    if not id_to_node:
        return []

    sentences = _split_sentences_for_rel(content)
    if not sentences:
        sentences = [str(content)[:500]]

    candidates = []
    seen = set()

    def _mentions(sentence: str) -> list:
      out = []
      for nid, node in id_to_node.items():
          val = str(node.get("value") or "").strip()
          if len(val) < 2:
              continue
          if val in sentence:
              out.append(nid)
      return out

    # 句内候选
    mention_per_sentence = []
    for s in sentences:
        ids = _mentions(s)
        mention_per_sentence.append((s, ids))
        if len(ids) < 2:
            continue
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                fid, tid = ids[i], ids[j]
                k = (fid, tid, s)
                if k in seen:
                    continue
                seen.add(k)
                candidates.append((fid, tid, s[:260]))
                if len(candidates) >= max_pairs:
                    return candidates

    # 邻句桥接候选（减少跨句漏掉关系）
    for idx in range(len(mention_per_sentence) - 1):
        s1, ids1 = mention_per_sentence[idx]
        s2, ids2 = mention_per_sentence[idx + 1]
        if not ids1 or not ids2:
            continue
        merged_ctx = f"{s1} {s2}"[:260]
        for fid in ids1:
            for tid in ids2:
                if fid == tid:
                    continue
                k = (fid, tid, merged_ctx)
                if k in seen:
                    continue
                seen.add(k)
                candidates.append((fid, tid, merged_ctx))
                if len(candidates) >= max_pairs:
                    return candidates

    # 兜底：若候选过少，补少量全局组合避免漏召回
    if len(candidates) < 4:
        ids = list(id_to_node.keys())[:18]
        fallback_ctx = str(content)[:220]
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                fid, tid = ids[i], ids[j]
                k = (fid, tid, fallback_ctx)
                if k in seen:
                    continue
                seen.add(k)
                candidates.append((fid, tid, fallback_ctx))
                if len(candidates) >= max_pairs:
                    return candidates

    return candidates


def extract_relations_rule_based(nodes: list, samples: list, project_id: str) -> Dict:
    """通道A（高召回）：关系粗抽。"""
    if not nodes or not samples:
        return {"edges": []}
    id_to_node = {str(n.get("id")): n for n in nodes if n.get("id")}
    edges = []
    seen = set()
    max_pairs = _env_int("KG_RULE_REL_CANDIDATE_MAX", 140)
    for sample in samples:
        content = clean_text(sample.get("content", ""))
        if not content:
            continue
        sample_nodes = _nodes_for_sample(
            nodes,
            sample,
            content,
            max_nodes=_env_int("KG_RULE_SAMPLE_NODE_MAX", 90),
        )
        if _env_bool("KG_REL_SENTENCE_CANDIDATE_ENABLED", True):
            candidates = _build_relation_candidates_from_sample(sample_nodes, content, max_pairs=max_pairs)
        else:
            candidates = _legacy_relation_candidates_from_sample(sample_nodes, content, max_pairs=max_pairs)
        for fid, tid, local_ctx in candidates:
            if fid == tid:
                continue
            from_node = id_to_node.get(fid)
            to_node = id_to_node.get(tid)
            if not from_node or not to_node:
                continue
            inferred = _infer_semantic_repair_edge(from_node, to_node, local_ctx or content)
            if not inferred:
                relation_type, relation_val = _infer_cooccurrence_relation(local_ctx or content)
                if (
                    relation_type == "文本共现"
                    and relation_val == "同段共现"
                    and not _env_bool("KG_RULE_EDGE_ALLOW_COOC", False)
                ):
                    continue
                actual_from = from_node
                actual_to = to_node
                actual_type = relation_type
                actual_value = relation_val
                actual_context = (local_ctx or content)[:160]
            else:
                actual_from = inferred["from"]
                actual_to = inferred["to"]
                actual_type = inferred["type"]
                actual_value = inferred["value"]
                actual_context = str(inferred.get("context") or local_ctx or content)[:180]

            edge_key = (
                str(actual_from.get("id")),
                str(actual_to.get("id")),
                actual_type,
                actual_value,
            )
            if edge_key in seen:
                continue
            seen.add(edge_key)

            edge_id = hashlib.md5(
                f"rb_{actual_from.get('id')}_{actual_to.get('id')}_{actual_type}_{actual_value}".encode("utf-8")
            ).hexdigest()
            edges.append({
                "id": edge_id,
                "type": actual_type,
                "from": actual_from.get("id"),
                "to": actual_to.get("id"),
                "from_node": actual_from,
                "to_node": actual_to,
                "value": actual_value,
                "eventRel": actual_value,
                "project_id": project_id,
                "properties": {
                    "source": "规则抽取",
                    "channel": "A",
                    "confidence": 0.56,
                    "context": actual_context,
                    "sample_id": str((sample or {}).get("id") or "").strip(),
                },
            })
    return {"edges": edges}


def _is_key_node_for_recall(node: dict, degree: dict) -> bool:
    if not isinstance(node, dict):
        return False
    nid = str(node.get("id") or "").strip()
    if not nid:
        return False
    if int(degree.get(nid, 0) or 0) > 0:
        return False
    props = node.get("properties") if isinstance(node.get("properties"), dict) else {}
    conf = float(props.get("confidence", 0.0) or 0.0)
    mention = int(props.get("mention_count", 0) or 0)
    t = str(node.get("type") or "").strip().lower()
    has_ticker = bool(props.get("tickers"))
    return conf >= float(os.getenv("KG_REL_KEY_NODE_MIN_CONF", "0.72") or 0.72) or mention >= 2 or t in ("1", "event", "事件") or has_ticker


def _find_pair_context(content: str, left: str, right: str) -> str:
    sentences = _split_sentences_for_rel(content)
    for s in sentences:
        if left in s and right in s:
            return s[:220]
    for i in range(len(sentences) - 1):
        s2 = f"{sentences[i]} {sentences[i + 1]}"
        if left in s2 and right in s2:
            return s2[:220]
    return str(content or "")[:220]


def _second_pass_key_node_recall(nodes: list, edges: list, samples: list, project_id: str) -> list:
    """关键节点补抽二次 pass：对高价值孤立节点补少量关系，避免明显漏判。"""
    if not nodes or not samples:
        return list(edges or [])

    out = list(edges or [])
    max_add = _env_int("KG_REL_SECOND_PASS_MAX_ADD", 80)
    if max_add <= 0:
        return out

    id_to_node = {str(n.get("id")): n for n in nodes if isinstance(n, dict) and n.get("id")}
    degree = {nid: 0 for nid in id_to_node.keys()}
    seen = set()
    for e in out:
        fid = str(e.get("from") or "")
        tid = str(e.get("to") or "")
        if fid in degree:
            degree[fid] += 1
        if tid in degree:
            degree[tid] += 1
        seen.add((fid, tid, str(e.get("type") or "")))

    added = 0
    for sample in samples:
        if added >= max_add:
            break
        content = clean_text((sample or {}).get("content", ""))
        if not content:
            continue
        sample_nodes = _nodes_for_sample(
            nodes,
            sample,
            content,
            max_nodes=_env_int("KG_REL_SECOND_PASS_SAMPLE_NODE_MAX", 80),
        )
        key_nodes = [n for n in sample_nodes if _is_key_node_for_recall(n, degree)]
        if not key_nodes:
            continue
        for key_node in key_nodes:
            if added >= max_add:
                break
            kv = str(key_node.get("value") or "").strip()
            kid = str(key_node.get("id") or "").strip()
            if not kv or not kid:
                continue

            partner_candidates = []
            for n in sample_nodes:
                nid = str(n.get("id") or "").strip()
                if not nid or nid == kid:
                    continue
                nv = str(n.get("value") or "").strip()
                if not nv:
                    continue
                if nv in content and kv in content:
                    partner_candidates.append((n, _find_pair_context(content, kv, nv)))

            for partner, ctx in partner_candidates[:4]:
                pid = str(partner.get("id") or "").strip()
                if not pid or pid == kid:
                    continue
                inferred = _infer_semantic_repair_edge(key_node, partner, ctx)
                if inferred:
                    actual_from = inferred["from"]
                    actual_to = inferred["to"]
                    actual_type = inferred["type"]
                    actual_value = inferred["value"]
                else:
                    actual_type, actual_value = _infer_cooccurrence_relation(ctx)
                    if (
                        actual_type == "文本共现"
                        and actual_value == "同段共现"
                        and not _env_bool("KG_RULE_EDGE_ALLOW_COOC", False)
                    ):
                        continue
                    actual_from = key_node
                    actual_to = partner
                k = (str(actual_from.get("id") or ""), str(actual_to.get("id") or ""), str(actual_type or ""))
                if not k[0] or not k[1] or k in seen:
                    continue
                seen.add(k)
                edge_id = hashlib.md5(
                    f"sp_{project_id}_{sample.get('id')}_{k[0]}_{k[1]}_{actual_type}_{actual_value}".encode("utf-8")
                ).hexdigest()
                out.append(
                    {
                        "id": edge_id,
                        "type": actual_type,
                        "from": k[0],
                        "to": k[1],
                        "from_node": actual_from,
                        "to_node": actual_to,
                        "value": actual_value,
                        "eventRel": actual_value,
                        "project_id": project_id,
                        "properties": {
                            "source": "二次补抽",
                            "channel": "A2",
                            "confidence": 0.63,
                            "context": str(ctx or "")[:200],
                            "sample_id": str((sample or {}).get("id") or "").strip(),
                            "second_pass": True,
                        },
                    }
                )
                degree[k[0]] = int(degree.get(k[0], 0) or 0) + 1
                degree[k[1]] = int(degree.get(k[1], 0) or 0) + 1
                added += 1
                if added >= max_add:
                    break
    if added:
        print(f"[RelationAgent] 关键节点二次补抽: +{added}")
    return out


def _merge_edges_dual_channel(rule_edges: list, llm_edges: list) -> list:
    """
    同一对节点 (from,to) 且相同类型只保留一条边：按语义质量分择优，避免完全重复的关系堆叠。
    若规则与 LLM 均给出该对边，标记 channel=A+B。
    """
    grouped = {}

    def _push(channel: str, raw: dict):
        if not raw or not raw.get("from") or not raw.get("to"):
            return
        e = dict(raw)
        props = dict(e.get("properties") or {})
        props.setdefault("channel", channel)
        if "confidence" not in props:
            props["confidence"] = 0.52 if channel == "A" else 0.75
        e["properties"] = props
        e = _normalize_relation_edge(e)
        # 用 (from, to, type) 进行分组，允许两节点之间存在多种细分关系类型
        pair = (str(e["from"]), str(e["to"]), str(e.get("type", "语义关系")))
        grouped.setdefault(pair, []).append((channel, e))

    for e in rule_edges or []:
        _push("A", e)
    for e in llm_edges or []:
        _push("B", e)

    out = []
    for pair, items in grouped.items():
        def _sort_key(it):
            ch, ed = it
            s = _edge_quality_score(ed)
            pri = 1 if ch == "B" else 0
            return (s + pri * 0.05, len((ed.get("value") or "")))

        _, best_edge = max(items, key=_sort_key)
        merged = dict(best_edge)
        chs = {it[0] for it in items}
        mp = dict(merged.get("properties") or {})
        if chs >= {"A", "B"}:
            mp["channel"] = "A+B"
            mp["confidence"] = max(float(mp.get("confidence", 0)), 0.88)
        merged["properties"] = mp
        out.append(merged)
    return out


def _prioritize_incremental_edges(edges: list, nodes: list, samples: list) -> list:
    """增量模式优先保留与本轮新增样本相关的边，降低新增节点孤立概率。"""
    if not edges:
        return []

    sample_ids = {
        str((s or {}).get("id") or "").strip()
        for s in (samples or [])
        if str((s or {}).get("id") or "").strip()
    }
    if not sample_ids:
        return list(edges)

    node_sample = {}
    for n in (nodes or []):
        if not isinstance(n, dict):
            continue
        nid = str(n.get("id") or "").strip()
        if not nid:
            continue
        props = n.get("properties") if isinstance(n.get("properties"), dict) else {}
        sid = str(props.get("sample_id") or "").strip()
        if sid:
            node_sample[nid] = sid

    def _edge_rank(e):
        if not isinstance(e, dict):
            return (0, 0.0)
        src = str(e.get("from") or e.get("source") or "").strip()
        dst = str(e.get("to") or e.get("target") or "").strip()
        props = e.get("properties") if isinstance(e.get("properties"), dict) else {}
        edge_sid = str(props.get("sample_id") or "").strip()
        hit_new = (
            (edge_sid and edge_sid in sample_ids)
            or (src and node_sample.get(src, "") in sample_ids)
            or (dst and node_sample.get(dst, "") in sample_ids)
        )
        conf = float(props.get("confidence") or 0.0)
        return (1 if hit_new else 0, conf)

    ranked = sorted((e for e in (edges or []) if isinstance(e, dict)), key=_edge_rank, reverse=True)
    return ranked


def extract_relations_only(nodes: list, samples: list, project_id: str, mode: str = "full") -> list:
    """双通道关系抽取：A 粗抽 + B LLM 精抽，最后 MergeAgent 融合。"""
    from agents.property_enrichment_agent import enrich_edges_properties

    if not nodes:
        return []
    rule_result = extract_relations_rule_based(nodes, samples, project_id)
    llm_result = extract_relations_with_llm(
        nodes=nodes,
        relation_type='general',
        project_id=project_id,
        announcements=samples
    )
    merged = _merge_edges_dual_channel(
        rule_result.get("edges", []),
        llm_result.get("edges", []),
    )
    merged = [e for e in merged if not _should_drop_placeholder_cooccurrence_edge(e)]
    if _env_bool("KG_REL_SECOND_PASS_ENABLED", True):
        merged = _second_pass_key_node_recall(nodes, merged, samples, project_id)
    merged = _repair_isolated_nodes_with_sample_semantic_edges(nodes, merged, project_id, samples)
    merged = enrich_edges_properties(merged, nodes, samples, project_id)
    if mode == "incremental":
        # 增量模式优先保留「触达本轮新增样本节点」的边，再做上限截断。
        prioritized = _prioritize_incremental_edges(merged, nodes, samples)
        max_edges = max(200, _env_int("KG_INCREMENTAL_REL_MAX", 420))
        return prioritized[:max_edges]
    return merged


def run_relation_agent(nodes: list, samples: list, project_id: str):
    """Relation Agent：基于节点和样本抽取关系并入库。"""
    edges = extract_relations_only(nodes, samples, project_id)
    if edges:
        save_edges_to_databases(edges, project_id, relation_type='general')
    return edges


def run_conflict_agent(edges: list, deep_check: bool = False):
    """
    Conflict Agent：检测关系冲突。
    规则（轻量版）：
    1) 同一对节点出现双向因果关系，视为潜在冲突；
    2) 同一 from->to 出现不同类型关系，视为潜在冲突。
    """
    if not edges:
        return []

    conflicts = []
    edge_index = {}
    for edge in edges:
        k = (edge.get("from"), edge.get("to"))
        edge_index.setdefault(k, []).append(edge)

    # 规则1：双向因果冲突
    for (src, dst), edge_list in edge_index.items():
        reverse_list = edge_index.get((dst, src), [])
        if not reverse_list:
            continue
        has_causal_forward = any(e.get("type") == "因果关系" for e in edge_list)
        has_causal_reverse = any(e.get("type") == "因果关系" for e in reverse_list)
        if has_causal_forward and has_causal_reverse:
            conflicts.append({
                "type": "语义冲突",
                "from": src,
                "to": dst,
                "reason": "双向因果关系通常不同时成立",
                "evidence_ref": [e.get("id") for e in edge_list + reverse_list if e.get("id")],
                "message": "检测到双向因果关系，建议人工复核",
                "disposition": "needs-review",
            })

    # 规则2：同向多类型冲突
    for (src, dst), edge_list in edge_index.items():
        relation_types = {e.get("type") for e in edge_list if e.get("type")}
        if len(relation_types) > 1:
            conflicts.append({
                "type": "语义冲突",
                "from": src,
                "to": dst,
                "reason": f"同一方向存在多种关系类型: {', '.join(sorted(relation_types))}",
                "evidence_ref": [e.get("id") for e in edge_list if e.get("id")],
                "message": f"同一方向存在多种关系类型: {', '.join(sorted(relation_types))}",
                "disposition": "needs-review",
            })

    if deep_check:
        for (src, dst), edge_list in edge_index.items():
            # 数值冲突：同一方向 value 出现多个不同数值
            nums = set()
            for e in edge_list:
                text_val = f"{e.get('value', '')} {((e.get('properties') or {}).get('context', ''))}"
                nums.update(re.findall(r"\d+(?:\.\d+)?%?", text_val))
            if len(nums) > 1:
                conflicts.append({
                    "type": "数值冲突",
                    "from": src,
                    "to": dst,
                    "reason": f"同一关系出现多个数值: {', '.join(sorted(nums)[:5])}",
                    "evidence_ref": [e.get("id") for e in edge_list if e.get("id")],
                    "message": "检测到数值不一致，建议优先按可信来源修正",
                    "disposition": "needs-review",
                })

            # 来源冲突：抽取来源混杂且置信低
            sources = {
                str((e.get("properties") or {}).get("source", ""))
                for e in edge_list
            }
            avg_conf = sum([
                float((e.get("properties") or {}).get("confidence", 0.5))
                for e in edge_list
            ]) / max(1, len(edge_list))
            if len(sources) > 1 and avg_conf < 0.75:
                conflicts.append({
                    "type": "来源冲突",
                    "from": src,
                    "to": dst,
                    "reason": f"多来源结果不一致，平均置信度偏低({avg_conf:.2f})",
                    "evidence_ref": [e.get("id") for e in edge_list if e.get("id")],
                    "message": "建议人工复核或补充高质量样本",
                    "disposition": "needs-review",
                })

    # 去重
    unique = {}
    for c in conflicts:
        if c.get("disposition") != "needs-review":
            c["disposition"] = "auto-resolve"
        key = (c["type"], c["from"], c["to"], c.get("reason", ""))
        unique[key] = c
    return list(unique.values())


def run_graph_agent(nodes: list, edges: list, conflicts: list, project_id: str):
    """Graph Agent：组织前端可视化图数据。"""
    graph_nodes = []
    for node in nodes:
        node_type = node.get("type")
        graph_nodes.append({
            "id": node.get("id"),
            "label": node.get("value"),
            "type": "event" if str(node_type) == "1" else "entity",
            "raw": node
        })

    graph_edges = []
    for edge in edges:
        graph_edges.append({
            "id": edge.get("id"),
            "source": edge.get("from"),
            "target": edge.get("to"),
            "label": edge.get("value"),
            "type": edge.get("type"),
            "raw": edge
        })

    return {
        "project_id": project_id,
        "nodes": graph_nodes,
        "edges": graph_edges,
        "conflicts": conflicts,
        "stats": {
            "node_count": len(graph_nodes),
            "edge_count": len(graph_edges),
            "conflict_count": len(conflicts)
        }
    }


@llmGenKG_bp.route('/master_agent_run', methods=['POST'])
def run_master_agent_api():
    """
    Master Agent（LangGraph 多功能 Agent 协作）：
    1. 接收样本 ID 列表并从 MongoDB 获取样本
    2. Node Agent：节点抽取并写入 MySQL
    3. Stale Agent：清理本项目下过时 MySQL 关系与 Neo4j 图数据
    4. Relation Agent：关系抽取并双写 MySQL + Neo4j
    5. Conflict Agent：冲突检测
    6. Graph Agent：组装前端可视化数据
    7. 保存抽取历史并返回
    """
    try:
        if not request.is_json:
            return jsonify({
                "success": False,
                "status": 400,
                "message": "请求必须为 JSON"
            }), 400

        data = request.get_json() or {}
        project_id = data.get("project_id")
        sample_ids = data.get("sample_ids") or data.get("announcement_ids") or []
        run_id = data.get("run_id")
        resume_from = data.get("resume_from")
        plan_overrides = data.get("build_plan") if isinstance(data.get("build_plan"), dict) else {}

        if not project_id:
            return jsonify({
                "success": False,
                "status": 400,
                "message": "project_id 不能为空"
            }), 400
        if not isinstance(sample_ids, list) or not sample_ids:
            return jsonify({
                "success": False,
                "status": 400,
                "message": "sample_ids 必须是非空数组"
            }), 400

        samples = fetch_samples_from_mongo(sample_ids)
        if not samples:
            return jsonify({
                "success": False,
                "status": 404,
                "message": "未在 MongoDB 中找到对应样本",
                "data": {
                    "project_id": project_id,
                    "sample_ids": sample_ids
                }
            }), 404

        incremental_snapshot = None
        try:
            from agents.incremental_kg_impact import get_incremental_impact_record
            incremental_snapshot = get_incremental_impact_record(project_id)
        except Exception as _snap_e:
            print(f"[MasterAgent] 读取增量影响快照失败: {_snap_e}")

        from agents.master_build_workflow import invoke_master_build
        final_state = invoke_master_build(
            project_id=project_id,
            sample_ids=sample_ids,
            samples=samples,
            run_id=run_id,
            resume_from=resume_from,
            plan_overrides=plan_overrides,
            has_incremental_impact=bool(incremental_snapshot),
        )
        if final_state.get("error"):
            return jsonify({
                "success": False,
                "status": 500,
                "message": final_state["error"],
            }), 500

        nodes = final_state.get("nodes") or []
        edges = final_state.get("edges") or []
        conflicts = final_state.get("conflicts") or []
        graph_data = final_state.get("graph") or {}

        _uid = (data.get("user_id") or data.get("creator") or data.get("username")
                or request.headers.get("X-User-Id"))
        _uid = str(_uid).strip() if _uid else None

        try:
            from agents.incremental_kg_impact import clear_incremental_impact_for_project
            clear_incremental_impact_for_project(project_id)
        except Exception as _inc_e:
            print(f"[MasterAgent] 清除增量影响标记失败: {_inc_e}")

        payload = _finalize_master_build_payload(
            project_id,
            sample_ids,
            run_id_hint=str(final_state.get("run_id") or ""),
            build_plan=final_state.get("build_plan"),
            graph_enrichment=final_state.get("graph_enrichment"),
            needs_stale_cleanup=bool(final_state.get("needs_stale_cleanup")),
            incremental_impact_before_build=incremental_snapshot,
            samples_override=samples,
            nodes=nodes,
            edges=edges,
            conflicts=conflicts,
            graph=graph_data,
        )

        save_extraction_history(
            project_id,
            "master",
            sample_ids,
            payload.get("nodes") or [],
            payload.get("edges") or [],
            run_id=final_state.get("run_id"),
            user_id=_uid,
            workflow_meta=dict(payload.get("workflow_meta") or {}),
        )

        return jsonify({
            "success": True,
            "status": 200,
            "message": "Master Agent 执行成功",
            "data": payload
        })
    except Exception as e:
        print(f"[MasterAgent] 执行失败: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "status": 500,
            "message": f"Master Agent 执行失败: {str(e)}"
        }), 500


def _iter_master_agent_stream_lines(data: Dict[str, Any], request_user_id: Optional[str] = None):
    """复用一键构建 NDJSON 事件生成逻辑，供流式接口与异步任务共用。"""
    project_id = data.get("project_id")
    sample_ids = data.get("sample_ids") or data.get("announcement_ids") or []
    run_id = data.get("run_id")
    resume_from = data.get("resume_from")
    plan_overrides = data.get("build_plan") if isinstance(data.get("build_plan"), dict) else {}

    if not project_id:
        raise ValueError("project_id 不能为空")
    if not isinstance(sample_ids, list) or not sample_ids:
        raise ValueError("sample_ids 必须是非空数组")

    force_full = bool(data.get("force_full_rebuild"))
    delta = analyze_master_build_sample_delta(project_id, sample_ids)
    if force_full:
        delta = {"kind": "full", "reason": "force_full_rebuild"}
    elif delta.get("kind") == "noop" and not _mysql_nodes_edges_nonempty(project_id):
        delta = {"kind": "full", "reason": "noop_but_graph_empty"}

    incremental_snapshot = None
    try:
        from agents.incremental_kg_impact import get_incremental_impact_record
        incremental_snapshot = get_incremental_impact_record(project_id)
    except Exception as _snap_e:
        print(f"[MasterAgent/stream] 读取增量影响快照失败: {_snap_e}")

    from agents.master_build_workflow import iter_master_build_ndjson
    from agents.checkpoint_manager_agent import make_run_id

    _uid = (data.get("user_id") or data.get("creator") or data.get("username") or request_user_id)
    _uid = str(_uid).strip() if _uid else None

    kind = delta.get("kind")

    if kind == "noop":
        sd = {
            "kind": "noop",
            "resolved_mode": "noop",
            "message": "样本集合相对上次一键构建无变化，无需重新抽取。请在左侧「抽取历史」查看或切换历史 run。",
            "reason": delta.get("reason"),
        }
        payload = build_master_snapshot_payload_from_project_db(
            project_id,
            sample_ids,
            sample_delta=sd,
        )
        payload["workflow_meta"]["sample_delta"] = sd
        yield json.dumps(
            {
                "status": "progress",
                "stage": "noop_skip",
                "phase": "nodes",
                "progress": 100,
                "label": "样本未变化，跳过 LLM 抽取",
            },
            ensure_ascii=False,
        ) + "\n"
        yield json.dumps({"status": "complete", "success": True, "data": payload}, ensure_ascii=False) + "\n"
        return

    removed = list(delta.get("removed_sample_ids") or [])
    if removed and kind in ("prune_only", "incremental_and_prune"):
        stats = remove_graph_data_for_sample_ids(project_id, removed)
        yield json.dumps(
            {
                "status": "progress",
                "stage": "sample_prune",
                "phase": "nodes",
                "progress": 12,
                "label": f"已移除 {len(removed)} 个样本对应子图（节点 {stats.get('deleted_nodes', 0)}）",
            },
            ensure_ascii=False,
        ) + "\n"

    if kind == "prune_only":
        sd = {
            "kind": "prune_only",
            "resolved_mode": "prune",
            "removed_sample_ids": removed,
            "prune_stats": stats if removed else {},
            "message": "已按移除的样本清理图谱，其余部分保持不变。",
        }
        final_run_id = run_id or make_run_id(prefix=f"master_{project_id}")
        payload = build_master_snapshot_payload_from_project_db(
            project_id,
            sample_ids,
            run_id_hint=final_run_id,
            sample_delta=sd,
        )
        payload["workflow_meta"]["run_id"] = final_run_id
        payload["workflow_meta"]["sample_delta"] = sd
        try:
            save_extraction_history(
                project_id,
                "master",
                sample_ids,
                payload["nodes"],
                payload["edges"],
                run_id=final_run_id,
                user_id=_uid,
                workflow_meta=dict(payload["workflow_meta"]),
            )
            try:
                from agents.incremental_kg_impact import clear_incremental_impact_for_project
                clear_incremental_impact_for_project(project_id)
            except Exception:
                pass
        except Exception as pe:
            yield json.dumps(
                {"status": "error", "success": False, "message": f"保存抽取历史失败: {pe}"},
                ensure_ascii=False,
            ) + "\n"
            return
        yield json.dumps({"status": "complete", "success": True, "data": payload}, ensure_ascii=False) + "\n"
        return

    inc_modes = ("incremental_only", "incremental_and_prune")
    if kind in inc_modes:
        new_ids = delta.get("added_sample_ids") or []
        if not new_ids:
            sd = {
                "kind": "incremental_empty_after_prune",
                "resolved_mode": "prune",
                "message": "仅移除样本已完成清理，无新增样本需抽取。",
            }
            final_run_id = run_id or make_run_id(prefix=f"master_{project_id}")
            payload = build_master_snapshot_payload_from_project_db(
                project_id,
                sample_ids,
                run_id_hint=final_run_id,
                sample_delta=sd,
            )
            payload["workflow_meta"]["run_id"] = final_run_id
            payload["workflow_meta"]["sample_delta"] = sd
            try:
                save_extraction_history(
                    project_id,
                    "master",
                    sample_ids,
                    payload["nodes"],
                    payload["edges"],
                    run_id=final_run_id,
                    user_id=_uid,
                    workflow_meta=dict(payload["workflow_meta"]),
                )
                try:
                    from agents.incremental_kg_impact import clear_incremental_impact_for_project
                    clear_incremental_impact_for_project(project_id)
                except Exception:
                    pass
            except Exception as pe:
                yield json.dumps(
                    {"status": "error", "success": False, "message": f"保存失败: {pe}"},
                    ensure_ascii=False,
                ) + "\n"
                return
            yield json.dumps({"status": "complete", "success": True, "data": payload}, ensure_ascii=False) + "\n"
            return

        samples_new = fetch_samples_from_mongo(new_ids)
        if not samples_new:
            yield json.dumps(
                {
                    "status": "error",
                    "success": False,
                    "message": "未在 MongoDB 中找到新增样本",
                },
                ensure_ascii=False,
            ) + "\n"
            return
        merged_plan = {
            **(plan_overrides or {}),
            "mode": "incremental",
            "persistence_mode": "merge",
            "strict_stale_cleanup": False,
        }
        has_impact = bool(incremental_snapshot) or True
        for line in iter_master_build_ndjson(
            project_id=project_id,
            sample_ids=new_ids,
            samples=samples_new,
            run_id=run_id,
            resume_from=resume_from,
            plan_overrides=merged_plan,
            has_incremental_impact=has_impact,
            incremental_snapshot=incremental_snapshot,
            user_id=_uid,
            history_sample_ids=sample_ids,
        ):
            yield line
        return

    samples = fetch_samples_from_mongo(sample_ids)
    if not samples:
        yield json.dumps(
            {
                "status": "error",
                "success": False,
                "message": "未在 MongoDB 中找到对应样本",
            },
            ensure_ascii=False,
        ) + "\n"
        return
    has_impact = bool(incremental_snapshot)
    for line in iter_master_build_ndjson(
        project_id=project_id,
        sample_ids=sample_ids,
        samples=samples,
        run_id=run_id,
        resume_from=resume_from,
        plan_overrides=plan_overrides,
        has_incremental_impact=has_impact,
        incremental_snapshot=incremental_snapshot,
        user_id=_uid,
        history_sample_ids=sample_ids,
    ):
        yield line


@llmGenKG_bp.route('/master_agent_run_stream', methods=['POST'])
def run_master_agent_stream_api():
    """
    一键构建 NDJSON 流：每完成 LangGraph 一节点推送 progress，最后一行 complete。
    Content-Type: application/x-ndjson
    """
    try:
        if not request.is_json:
            return jsonify({
                "success": False,
                "status": 400,
                "message": "请求必须为 JSON"
            }), 400

        data = request.get_json() or {}
        return Response(
            _iter_master_agent_stream_lines(data, request.headers.get("X-User-Id")),
            mimetype='application/x-ndjson; charset=utf-8',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
            },
        )
    except ValueError as ve:
        return jsonify({
            "success": False,
            "status": 400,
            "message": str(ve)
        }), 400
    except Exception as e:
        print(f"[MasterAgent/stream] 执行失败: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "status": 500,
            "message": f"Master Agent 流式执行失败: {str(e)}"
        }), 500


def _upsert_master_task(task_id: str, patch: Dict[str, Any]):
    with _MASTER_TASKS_LOCK:
        task = dict(_MASTER_TASKS.get(task_id) or {})
        task.update(patch or {})
        task["updated_at"] = datetime.now().isoformat()
        _MASTER_TASKS[task_id] = task
        return dict(task)


def _run_master_agent_async_task(task_id: str, data: Dict[str, Any], request_user_id: Optional[str]):
    _upsert_master_task(task_id, {"status": "running", "message": "任务后台执行中"})
    try:
        for raw_line in _iter_master_agent_stream_lines(data, request_user_id):
            line = str(raw_line or "").strip()
            if not line:
                continue
            payload = None
            try:
                payload = json.loads(line)
            except Exception:
                continue

            if payload.get("status") == "progress":
                _upsert_master_task(
                    task_id,
                    {
                        "status": "running",
                        "progress": int(payload.get("progress") or 0),
                        "phase": payload.get("phase") or "nodes",
                        "label": payload.get("label") or payload.get("stage") or "",
                        "message": payload.get("label") or "任务后台执行中",
                    },
                )
            elif payload.get("status") == "complete" and payload.get("success"):
                run_id = str(payload.get("data", {}).get("workflow_meta", {}).get("run_id") or "").strip()
                _upsert_master_task(
                    task_id,
                    {
                        "status": "success",
                        "progress": 100,
                        "phase": "relations",
                        "message": "构建完成",
                        "run_id": run_id,
                    },
                )
            elif payload.get("status") == "error":
                _upsert_master_task(
                    task_id,
                    {
                        "status": "error",
                        "error": payload.get("message") or "后台构建失败",
                        "message": payload.get("message") or "后台构建失败",
                    },
                )
                return

        task = dict(_MASTER_TASKS.get(task_id) or {})
        if task.get("status") not in ("success", "error"):
            _upsert_master_task(
                task_id,
                {
                    "status": "error",
                    "error": "后台构建未返回完成状态，请稍后重试",
                    "message": "后台构建未返回完成状态",
                },
            )
    except Exception as e:
        traceback.print_exc()
        _upsert_master_task(
            task_id,
            {
                "status": "error",
                "error": f"后台构建执行失败: {str(e)}",
                "message": "后台构建执行失败",
            },
        )


@llmGenKG_bp.route('/master_agent_run_async', methods=['POST'])
def run_master_agent_async_api():
    """提交一键构建后台任务，立即返回 task_id，前端可轮询状态。"""
    try:
        if not request.is_json:
            return jsonify({
                "success": False,
                "status": 400,
                "message": "请求必须为 JSON"
            }), 400

        data = request.get_json() or {}
        project_id = data.get("project_id")
        sample_ids = data.get("sample_ids") or data.get("announcement_ids") or []
        if not project_id:
            return jsonify({
                "success": False,
                "status": 400,
                "message": "project_id 不能为空"
            }), 400
        if not isinstance(sample_ids, list) or not sample_ids:
            return jsonify({
                "success": False,
                "status": 400,
                "message": "sample_ids 必须是非空数组"
            }), 400

        task_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        request_uid = request.headers.get("X-User-Id")
        _upsert_master_task(
            task_id,
            {
                "task_id": task_id,
                "status": "pending",
                "progress": 0,
                "phase": "nodes",
                "label": "任务已提交，等待执行",
                "message": "任务已提交，等待执行",
                "project_id": str(project_id),
                "run_id": str(data.get("run_id") or "").strip(),
                "created_at": created_at,
            },
        )

        thread = Thread(
            target=_run_master_agent_async_task,
            args=(task_id, data, request_uid),
            daemon=True,
        )
        thread.start()

        return jsonify({
            "success": True,
            "status": 200,
            "message": "后台构建任务已提交",
            "data": {
                "task_id": task_id,
                "project_id": str(project_id),
                "status": "pending",
                "run_id": str(data.get("run_id") or "").strip(),
            }
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "status": 500,
            "message": f"提交后台构建任务失败: {str(e)}"
        }), 500


@llmGenKG_bp.route('/master_agent_task_status', methods=['GET'])
def get_master_agent_task_status_api():
    try:
        task_id = str(request.args.get("task_id") or "").strip()
        if not task_id:
            return jsonify({
                "success": False,
                "status": 400,
                "message": "task_id 不能为空"
            }), 400

        with _MASTER_TASKS_LOCK:
            task = dict(_MASTER_TASKS.get(task_id) or {})
        if not task:
            return jsonify({
                "success": False,
                "status": 404,
                "message": "任务不存在或已过期"
            }), 404

        return jsonify({
            "success": True,
            "status": 200,
            "message": "获取成功",
            "data": task,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "status": 500,
            "message": f"获取任务状态失败: {str(e)}"
        }), 500


def run_incremental_graph_for_project(project_id: str) -> Dict[str, Any]:
    """
    合并式增量图谱更新：仅处理 kg_incremental_impact 中记录的受影响样本，
    节点/边 upsert，Neo4j 不完全清空。
    """
    from agents.incremental_kg_impact import (
        clear_incremental_impact_for_project,
        get_incremental_impact_record,
    )
    from agents.master_build_workflow import invoke_master_build

    rec = get_incremental_impact_record(project_id)
    if not rec or not int(rec.get("pending") or 0):
        return {"skipped": True, "reason": "not_pending"}

    aids = rec.get("affected_sample_ids") or []
    if isinstance(aids, str):
        try:
            aids = json.loads(aids)
        except json.JSONDecodeError:
            aids = []
    if not isinstance(aids, list) or not aids:
        return {"skipped": True, "reason": "no_affected_ids"}

    samples = fetch_samples_from_mongo(aids)
    if not samples:
        return {"skipped": True, "reason": "mongo_empty", "sample_ids": aids}

    final_state = invoke_master_build(
        project_id=str(project_id),
        sample_ids=aids,
        samples=samples,
        plan_overrides={
            "mode": "incremental",
            "persistence_mode": "merge",
            "strict_stale_cleanup": False,
        },
        has_incremental_impact=True,
    )

    if final_state.get("error"):
        return {"success": False, "error": final_state["error"], "run_id": final_state.get("run_id")}

    history_sample_ids = _get_project_sample_ids(project_id) or aids
    payload = _finalize_master_build_payload(
        str(project_id),
        history_sample_ids,
        run_id_hint=str(final_state.get("run_id") or ""),
        build_plan=final_state.get("build_plan"),
        graph_enrichment=final_state.get("graph_enrichment"),
        needs_stale_cleanup=bool(final_state.get("needs_stale_cleanup")),
        nodes=final_state.get("nodes") or [],
        edges=final_state.get("edges") or [],
        conflicts=final_state.get("conflicts") or [],
        graph=final_state.get("graph") or {},
    )

    try:
        save_extraction_history(
            project_id,
            "incremental",
            history_sample_ids,
            payload.get("nodes") or [],
            payload.get("edges") or [],
            run_id=final_state.get("run_id"),
            workflow_meta=dict(payload.get("workflow_meta") or {}),
        )
    except Exception as _h:
        print(f"[IncrementalKG] 抽取历史写入失败: {_h}")

    try:
        clear_incremental_impact_for_project(project_id)
    except Exception as _c:
        print(f"[IncrementalKG] 清除 pending 失败: {_c}")

    return {
        "success": True,
        "nodes_count": len(payload.get("nodes") or []),
        "edges_count": len(payload.get("edges") or []),
        "run_id": final_state.get("run_id"),
        "build_plan": final_state.get("build_plan"),
    }


def run_incremental_graph_for_projects(project_ids: list) -> Dict[str, Any]:
    """批量增量（供同步任务调用）。"""
    out = {}
    max_n = _env_int("KG_AUTO_INCREMENTAL_MAX_PROJECTS", 8)
    for pid in (project_ids or [])[:max_n]:
        try:
            out[str(pid)] = run_incremental_graph_for_project(str(pid))
        except Exception as e:
            out[str(pid)] = {"success": False, "error": str(e)}
    return out


def _extract_conflict_count_from_meta(workflow_meta: Dict[str, Any]) -> int:
    wm = workflow_meta or {}
    quality_report = wm.get("quality_report") if isinstance(wm.get("quality_report"), dict) else {}
    stats = quality_report.get("stats") if isinstance(quality_report.get("stats"), dict) else {}
    quality_score = wm.get("quality_score") if isinstance(wm.get("quality_score"), dict) else {}
    metrics = quality_score.get("metrics") if isinstance(quality_score.get("metrics"), dict) else {}
    for v in (
        wm.get("conflict_count"),
        quality_report.get("conflict_count"),
        stats.get("conflict_count"),
        metrics.get("conflict_count"),
    ):
        try:
            if v is not None:
                return int(float(v))
        except Exception:
            continue
    return 0


def _extract_conflict_details_from_meta(workflow_meta: Dict[str, Any]) -> list:
    wm = workflow_meta or {}
    for v in (
        wm.get("conflicts"),
        wm.get("conflict_details"),
        wm.get("conflict_list"),
        ((wm.get("graph") or {}).get("conflicts") if isinstance(wm.get("graph"), dict) else None),
    ):
        if isinstance(v, list):
            return v
    return []


def _enrich_workflow_meta_with_conflicts(project_id: str, run_id: str, workflow_meta: Dict[str, Any]) -> Dict[str, Any]:
    """若 workflow_meta 只有冲突统计无明细，则基于该 run 边快照重建冲突详情。"""
    wm = workflow_meta if isinstance(workflow_meta, dict) else {}
    conflict_count = _extract_conflict_count_from_meta(wm)
    details = _extract_conflict_details_from_meta(wm)
    if conflict_count <= 0 or details:
        return wm

    snap = _load_extraction_snapshot(project_id, run_id)
    edges = snap.get("edges") if isinstance(snap, dict) else []
    if not isinstance(edges, list) or not edges:
        return wm

    rebuilt = run_conflict_agent(edges, deep_check=True)
    if not rebuilt:
        return wm

    wm = dict(wm)
    wm["conflicts"] = rebuilt
    wm["conflict_details"] = rebuilt

    # 回写缓存快照，避免每次查询重复重算。
    engine = None
    try:
        engine = get_sqlalchemy_engine()
        with engine.connect() as conn:
            up = text(
                """
                UPDATE extraction_history
                SET workflow_meta_snapshot = :workflow_meta_snapshot
                WHERE project_id = :project_id AND run_id = :run_id
                """
            )
            conn.execute(
                up,
                {
                    "workflow_meta_snapshot": _json_dumps_safe(wm),
                    "project_id": project_id,
                    "run_id": run_id,
                },
            )
            conn.commit()
    except Exception as _e:
        print(f"[workflow_meta] 回写冲突明细失败: {_e}")
    finally:
        if engine is not None:
            engine.dispose()
    return wm


@llmGenKG_bp.route('/incremental_graph_sync', methods=['POST'])
def incremental_graph_sync_api():
    """手动或调度触发：对指定项目执行增量图谱合并构建。"""
    try:
        data = request.get_json() or {}
        project_id = data.get("project_id")
        if not project_id:
            return jsonify({"success": False, "status": 400, "message": "project_id 不能为空"}), 400
        result = run_incremental_graph_for_project(str(project_id))
        if result.get("skipped"):
            return jsonify({"success": True, "status": 200, "message": "跳过", "data": result})
        if not result.get("success"):
            return jsonify(
                {"success": False, "status": 500, "message": result.get("error", "增量失败"), "data": result}
            ), 500
        return jsonify({"success": True, "status": 200, "message": "增量图谱更新完成", "data": result})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "status": 500, "message": str(e)}), 500


@llmGenKG_bp.route('/get_workflow_report_by_run', methods=['GET'])
def get_workflow_report_by_run_api():
    """按 project_id + run_id 获取构建流程报告（workflow_meta）。"""
    try:
        project_id = str(request.args.get('project_id') or '').strip()
        run_id = str(request.args.get('run_id') or '').strip()
        if not project_id or not run_id:
            return jsonify({
                'success': False,
                'message': 'project_id 与 run_id 不能为空',
                'status': 400,
            }), 400

        _ensure_extraction_history_schema()
        engine = get_sqlalchemy_engine()
        with engine.connect() as conn:
            q = text(
                """
                SELECT run_id, project_id, created_at, workflow_meta_snapshot
                FROM extraction_history
                WHERE project_id = :project_id AND run_id = :run_id
                LIMIT 1
                """
            )
            row = conn.execute(q, {'project_id': project_id, 'run_id': run_id}).fetchone()
        engine.dispose()

        if not row:
            return jsonify({
                'success': False,
                'message': '未找到对应构建记录',
                'status': 404,
            }), 404

        raw_meta = None
        created_at = None
        if hasattr(row, '_mapping'):
            raw_meta = row._mapping.get('workflow_meta_snapshot')
            created_at = row._mapping.get('created_at')
        else:
            raw_meta = getattr(row, 'workflow_meta_snapshot', None)
            created_at = getattr(row, 'created_at', None)

        workflow_meta = {}
        if raw_meta:
            try:
                workflow_meta = json.loads(raw_meta) if isinstance(raw_meta, str) else (raw_meta or {})
            except Exception:
                workflow_meta = {}

        if workflow_meta:
            workflow_meta = _enrich_workflow_meta_with_conflicts(project_id, run_id, workflow_meta)

        return jsonify({
            'success': True,
            'message': '获取成功',
            'status': 200,
            'data': {
                'project_id': project_id,
                'run_id': run_id,
                'created_at': created_at.isoformat() if hasattr(created_at, 'isoformat') else str(created_at or ''),
                'workflow_meta': workflow_meta,
            },
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取构建报告失败: {str(e)}',
            'status': 500,
        }), 500


@llmGenKG_bp.route('/analyze_quality_report_ai', methods=['POST'])
def analyze_quality_report_ai_api():
    """基于 workflow_meta 生成简洁的 AI 质量分析报告。"""
    try:
        data = request.get_json() or {}
        project_id = str(data.get('project_id') or '').strip()
        run_id = str(data.get('run_id') or '').strip()
        want_stream = str(data.get('stream') or '').strip().lower() in ('1', 'true', 'yes', 'y', 'on')
        user_hint = str(data.get('user_hint') or '').strip()
        workflow_meta = data.get('workflow_meta') if isinstance(data.get('workflow_meta'), dict) else None
        conflict_details = data.get('conflicts') if isinstance(data.get('conflicts'), list) else []

        if not project_id and not workflow_meta:
            return jsonify({
                'success': False,
                'message': 'project_id 与 workflow_meta 至少提供一个',
                'status': 400,
            }), 400

        if not workflow_meta:
            # 优先按 run_id 精确读取；否则读取该项目最新一条含 workflow_meta 的记录。
            if run_id:
                snap = _load_extraction_snapshot(project_id, run_id)
                workflow_meta = snap.get('workflow_meta') if isinstance(snap.get('workflow_meta'), dict) else {}
            else:
                _ensure_extraction_history_schema()
                engine = get_sqlalchemy_engine()
                try:
                    with engine.connect() as conn:
                        q = text(
                            """
                            SELECT run_id, workflow_meta_snapshot
                            FROM extraction_history
                            WHERE project_id = :project_id
                            ORDER BY created_at DESC
                            LIMIT 1
                            """
                        )
                        row = conn.execute(q, {'project_id': project_id}).fetchone()
                    if row:
                        raw_meta = row._mapping.get('workflow_meta_snapshot') if hasattr(row, '_mapping') else getattr(row, 'workflow_meta_snapshot', None)
                        if raw_meta:
                            workflow_meta = json.loads(raw_meta) if isinstance(raw_meta, str) else (raw_meta or {})
                        if not run_id:
                            run_id = str(row._mapping.get('run_id') if hasattr(row, '_mapping') else getattr(row, 'run_id', '') or '').strip()
                finally:
                    engine.dispose()

        workflow_meta = workflow_meta if isinstance(workflow_meta, dict) else {}
        if not workflow_meta:
            return jsonify({
                'success': False,
                'message': '未找到可分析的 workflow_meta 数据',
                'status': 404,
            }), 404

        if project_id and run_id:
            workflow_meta = _enrich_workflow_meta_with_conflicts(project_id, run_id, workflow_meta)

        final_run_id = str(run_id or workflow_meta.get('run_id') or '').strip()
        if want_stream:
            stream_iter, metrics = generate_kg_quality_analysis_report_stream(
                workflow_meta=workflow_meta,
                conflict_details=conflict_details,
                user_hint=user_hint,
            )

            def generate():
                yield json.dumps({
                    'status': 'start',
                    'data': {
                        'project_id': project_id,
                        'run_id': final_run_id,
                        'metrics': metrics,
                    },
                }, ensure_ascii=False) + "\n"

                full_text = []
                for chunk in stream_iter:
                    if not chunk:
                        continue
                    full_text.append(str(chunk))
                    yield json.dumps({'status': 'chunk', 'data': {'text': str(chunk)}}, ensure_ascii=False) + "\n"

                yield json.dumps({
                    'status': 'complete',
                    'success': True,
                    'data': {
                        'project_id': project_id,
                        'run_id': final_run_id,
                        'analysis_report': ''.join(full_text),
                        'metrics': metrics,
                    },
                }, ensure_ascii=False) + "\n"

            return Response(
                generate(),
                mimetype='application/x-ndjson; charset=utf-8',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no',
                },
            )

        report_text, metrics = generate_kg_quality_analysis_report(
            workflow_meta=workflow_meta,
            conflict_details=conflict_details,
            user_hint=user_hint,
        )

        return jsonify({
            'success': True,
            'message': '生成成功',
            'status': 200,
            'data': {
                'project_id': project_id,
                'run_id': final_run_id,
                'analysis_report': report_text,
                'metrics': metrics,
            },
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'AI 分析失败: {str(e)}',
            'status': 500,
        }), 500


@llmGenKG_bp.route('/analyze_quality_report_ai_stream', methods=['POST'])
def analyze_quality_report_ai_stream_api():
    """流式生成 AI 质量分析报告（NDJSON）。"""
    try:
        data = request.get_json() or {}
        project_id = str(data.get('project_id') or '').strip()
        run_id = str(data.get('run_id') or '').strip()
        user_hint = str(data.get('user_hint') or '').strip()
        workflow_meta = data.get('workflow_meta') if isinstance(data.get('workflow_meta'), dict) else None
        conflict_details = data.get('conflicts') if isinstance(data.get('conflicts'), list) else []

        if not project_id and not workflow_meta:
            return jsonify({
                'success': False,
                'message': 'project_id 与 workflow_meta 至少提供一个',
                'status': 400,
            }), 400

        if not workflow_meta:
            if run_id:
                snap = _load_extraction_snapshot(project_id, run_id)
                workflow_meta = snap.get('workflow_meta') if isinstance(snap.get('workflow_meta'), dict) else {}
            else:
                _ensure_extraction_history_schema()
                engine = get_sqlalchemy_engine()
                try:
                    with engine.connect() as conn:
                        q = text(
                            """
                            SELECT run_id, workflow_meta_snapshot
                            FROM extraction_history
                            WHERE project_id = :project_id
                            ORDER BY created_at DESC
                            LIMIT 1
                            """
                        )
                        row = conn.execute(q, {'project_id': project_id}).fetchone()
                    if row:
                        raw_meta = row._mapping.get('workflow_meta_snapshot') if hasattr(row, '_mapping') else getattr(row, 'workflow_meta_snapshot', None)
                        if raw_meta:
                            workflow_meta = json.loads(raw_meta) if isinstance(raw_meta, str) else (raw_meta or {})
                        if not run_id:
                            run_id = str(row._mapping.get('run_id') if hasattr(row, '_mapping') else getattr(row, 'run_id', '') or '').strip()
                finally:
                    engine.dispose()

        workflow_meta = workflow_meta if isinstance(workflow_meta, dict) else {}
        if not workflow_meta:
            return jsonify({
                'success': False,
                'message': '未找到可分析的 workflow_meta 数据',
                'status': 404,
            }), 404

        if project_id and run_id:
            workflow_meta = _enrich_workflow_meta_with_conflicts(project_id, run_id, workflow_meta)

        stream_iter, metrics = generate_kg_quality_analysis_report_stream(
            workflow_meta=workflow_meta,
            conflict_details=conflict_details,
            user_hint=user_hint,
        )
        final_run_id = str(run_id or workflow_meta.get('run_id') or '').strip()

        def generate():
            yield json.dumps({
                'status': 'start',
                'data': {
                    'project_id': project_id,
                    'run_id': final_run_id,
                    'metrics': metrics,
                },
            }, ensure_ascii=False) + "\n"

            full_text = []
            for chunk in stream_iter:
                if not chunk:
                    continue
                full_text.append(str(chunk))
                yield json.dumps({'status': 'chunk', 'data': {'text': str(chunk)}}, ensure_ascii=False) + "\n"

            yield json.dumps({
                'status': 'complete',
                'success': True,
                'data': {
                    'project_id': project_id,
                    'run_id': final_run_id,
                    'analysis_report': ''.join(full_text),
                    'metrics': metrics,
                },
            }, ensure_ascii=False) + "\n"

        return Response(
            generate(),
            mimetype='application/x-ndjson; charset=utf-8',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
            },
        )
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'AI 流式分析失败: {str(e)}',
            'status': 500,
        }), 500


def extract_nodes_with_llm(combined_text: str, project_id: str) -> Dict:
    """使用DeepSeek API从合并的公告文本中提取节点"""
    from openai import OpenAI

    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL
    )

    print("\n====== 开始处理公告 ======")
    print(f"合并公告内容前100字符: {combined_text[:100]}...")

    try:
        # 输入裁剪：默认 6000 字符，可通过环境变量调节
        node_input_limit = _env_int("NODE_EXTRACT_INPUT_CHARS", 6000)
        trimmed_text = _smart_trim(combined_text, node_input_limit)

        system_prompt = """你是面向上市公司信息披露（公告/重大事项）的金融信息抽取模型，任务是从给定文本中抽取可用于知识图谱的节点。

【节点类型】
- type=1（事件）：可观察的公司行为或状态变化，优先使用公告中的规范表述（如「重大资产重组」「关联交易」「回购注销」「限售解禁」）。
- type=0（实体）：事件中涉及的具体对象——公司全称/简称、自然人、子公司、交易对手、标的资产、监管机构等。

【质量约束】
- 禁止输出泛化词作为节点值：如「公司」「企业」「事项」「公告」「影响」「相关」「情况」等单独作为 value。
- 实体优先使用公告原文中的正式名称；同一实体在同一输出中命名应一致。
- 事件 key 填写细粒度类型标签（如「股权变动」「对外担保」「诉讼仲裁」）；实体 key 填写语义角色（如「收购方」「标的」「中介机构」）。
- properties.context：摘录或概括该节点在文中的依据（建议 25～120 字），须可复核。

【输出】仅输出合法 JSON（字段 nodes），勿输出解释性文字。"""

        # 可选缓存：相同文本+提示词不重复消耗额度
        cache_ttl = _env_int("LLM_CACHE_TTL_SECONDS", 3600)
        use_cache = _env_bool("LLM_CACHE_ENABLED", True)
        cache_key = ""
        if use_cache:
            cache_key = hashlib.sha256(
                f"deepseek-chat|nodes|{system_prompt}|{trimmed_text}".encode("utf-8", errors="ignore")
            ).hexdigest()
            cached = _cache_get(cache_key)
            if cached is not None:
                return cached

        user_prompt = f"""【任务】基于下列公告文本抽取图谱节点，输出 JSON：{{ "nodes": [ ... ] }}。

【公告正文】
{trimmed_text}

【JSON Schema 说明】
- nodes[].type：整数 0 或 1。
- nodes[].value：字符串，来自原文或可核对的规范简称。
- nodes[].key：事件类型标签或实体角色标签（中文短语）。
- nodes[].properties.context：必填，支撑该节点成立的原文依据或精炼概括。
- nodes[].properties.project_id：固定填 "{project_id}"。
- nodes[].properties.source：固定填 "LLM抽取"。
- id 字段可先占位，后端会重写。

【边界】勿臆造原文未出现的数值、日期与主体名称；不确定则宁可少抽。"""

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=_env_int("NODE_EXTRACT_MAX_TOKENS", 2000)
        )
        _usage_log("extract_nodes_with_llm", response)

        result_str = response.choices[0].message.content
        json_str = (
            result_str.split('```json')[1].split('```')[0] if '```json' in result_str
            else result_str.split('```')[1].split('```')[0] if '```' in result_str
            else result_str
        )

        result = json.loads(json_str)

        if "nodes" not in result:
            raise ValueError("返回结果缺少nodes字段")

        # 添加ID生成函数
        def generate_node_id(project_id, node_type, value):
            # 实体归一：相同项目、相同节点类型与内容值，赋予相同的固定 ID。
            # 防止多次提取同一实体导致出现大量“节点孤岛”碎片内容。
            unique_str = f"{project_id}_{node_type}_{value.strip()}"
            return hashlib.md5(unique_str.encode('utf-8')).hexdigest()

        for node in result.get("nodes", []):
            node["id"] = generate_node_id(project_id, node.get("type", "0"), node.get("value", ""))
            node["properties"] = node.get("properties", {})
            node["properties"]["project_id"] = project_id
            node["properties"]["source"] = "LLM抽取"

        if use_cache and cache_key:
            _cache_set(cache_key, result, cache_ttl)
        return result

    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}\n原始响应: {result_str[:500]}...")
        return {"nodes": []}
    except Exception as e:
        print(f"API调用异常: {type(e).__name__}: {str(e)}")
        return {"nodes": []}


def save_nodes_to_database(nodes: list, project_id: str):
    """将节点保存到数据库（覆盖：先删后插）"""
    engine = get_sqlalchemy_engine()
    try:
        with engine.connect() as connection:
            # 关键步骤1：先删除该项目之前的节点
            delete_stmt = text("DELETE FROM node_table WHERE project_id = :project_id")
            connection.execute(delete_stmt, {"project_id": project_id})
            connection.commit()

            # 关键步骤2：插入新节点
            for node in nodes:
                insert_stmt = text("""
                    INSERT INTO node_table 
                    (id, type, value, `key`, project_id, properties) 
                    VALUES 
                    (:id, :type, :value, :key, :project_id, :properties)
                """)
                connection.execute(insert_stmt, {
                    "id": node["id"],
                    "type": node["type"],
                    "value": node["value"],
                    "key": node["key"],
                    "project_id": project_id,
                    "properties": json.dumps(node.get("properties", {})),
                })
            connection.commit()
        return True
    except Exception as e:
        print(f"保存节点到数据库失败: {str(e)}")
        traceback.print_exc()
        return False


def merge_nodes_to_database(nodes: list, project_id: str):
    """增量合并节点：按 id upsert，不删除历史节点"""
    if not nodes:
        return True
    engine = get_sqlalchemy_engine()
    try:
        upsert = text("""
            INSERT INTO node_table 
            (id, type, value, `key`, project_id, properties) 
            VALUES 
            (:id, :type, :value, :key, :project_id, :properties)
            ON DUPLICATE KEY UPDATE
                type = VALUES(type),
                value = VALUES(value),
                `key` = VALUES(`key`),
                properties = VALUES(properties)
        """)
        with engine.connect() as connection:
            for node in nodes:
                connection.execute(upsert, {
                    "id": node["id"],
                    "type": node["type"],
                    "value": node["value"],
                    "key": node["key"],
                    "project_id": project_id,
                    "properties": json.dumps(node.get("properties", {})),
                })
            connection.commit()
        return True
    except Exception as e:
        print(f"合并节点到数据库失败: {str(e)}")
        traceback.print_exc()
        return False


@llmGenKG_bp.route('/extract_nodes_with_llm', methods=['POST'])
def extract_nodes_with_llm_api():
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        announcement_ids = data.get('announcement_ids', [])

        if not project_id:
            return jsonify({
                'success': False,
                'message': '项目ID不能为空',
                'status': 400
            }), 400

        print(f"\n=== 开始节点抽取流程 ===")
        print(f"项目ID: {project_id}")
        print(f"待处理公告数量: {len(announcement_ids)}")

        # 获取公告/样本数据（优先从 MongoDB event_data 获取，与 getProjectAnnouncements 一致）
        print("\n[步骤1/3] 从 MongoDB 获取样本数据...")
        samples = fetch_samples_from_mongo(announcement_ids)
        if not samples:
            print("未找到样本数据，尝试从 MySQL 获取...")
            announcements_df = fetch_announcements_by_ids(announcement_ids)
            if announcements_df is None or announcements_df.empty:
                print("未找到公告数据")
                return jsonify({
                    'success': False,
                    'message': f'未找到项目 {project_id} 的样本数据，请确认已选样本来自 MongoDB 或 MySQL',
                    'status': 404
                }), 404
            samples = [
                {'id': row['id'], 'title': row.get('title', ''), 'content': row.get('content', '')}
                for _, row in announcements_df.iterrows()
            ]
        total_announcements = len(samples)
        processed_count = 0
        all_nodes = []
        print(f"成功获取 {total_announcements} 条样本数据")

        def update_progress(progress, message):
            """生成进度更新消息"""
            print(f"进度更新: {progress}% - {message}")
            return json.dumps({
                'progress': progress,
                'message': message,
                'status': 'processing'
            })

        # 流式响应
        def generate():
            nonlocal processed_count, all_nodes

            print("\n[步骤2/3] 开始处理公告内容...")
            # 处理每条样本
            for idx, row in enumerate(samples):
                content = clean_text(row.get('content', ''))
                print(f"\n处理公告 {processed_count + 1}/{total_announcements}:")
                print(f"样本ID: {row.get('id', '')}")
                print(f"标题: {row.get('title', '')}")
                print(f"内容摘要: {content[:100]}...")

                # 使用LLM抽取节点
                print("调用DeepSeek API抽取节点...")
                extraction_result = extract_nodes_with_llm(content, project_id)
                nodes = extraction_result.get("nodes", [])
                print(f"抽取到 {len(nodes)} 个节点")

                if nodes:
                    print("抽取到的节点示例:")
                    for i, node in enumerate(nodes[:3]):  # 打印前3个节点作为示例
                        print(f"  {i + 1}. ID:{node['id']} 类型:{node['type']} 值:{node['value']} 键:{node['key']}")

                all_nodes.extend(nodes)

                # 更新进度
                processed_count += 1
                progress = int((processed_count / total_announcements) * 100)
                yield update_progress(progress, f"正在处理公告 {processed_count}/{total_announcements}") + "\n"

            print("\n[步骤3/3] 保存节点到数据库...")
            # 处理完成后保存节点
            if all_nodes:
                print(f"准备保存 {len(all_nodes)} 个节点到数据库")
                save_success = save_nodes_to_database(all_nodes, project_id)
                if not save_success:
                    print("保存节点到数据库失败")
                    yield json.dumps({
                        'progress': progress,
                        'message': '保存节点到数据库失败',
                        'status': 'processing'
                    }) + "\n"
                    return
                print("节点保存成功")

            # 保存抽取历史
            history_run_id = save_extraction_history(project_id, 'nodes', announcement_ids, all_nodes, [])

            # 最终结果
            print("\n=== 节点抽取完成 ===")
            print(f"总计抽取节点数: {len(all_nodes)}")
            print(f"事件节点数: {sum(1 for node in all_nodes if node['type'] == 1)}")
            print(f"实体节点数: {sum(1 for node in all_nodes if node['type'] == 0)}")

            yield json.dumps({
                'status': 'complete',
                'progress': 100,
                'message': '节点抽取完成',
                'data': {
                    'nodes': all_nodes,
                    'count': len(all_nodes),
                    'project_id': project_id,
                    'run_id': history_run_id,
                }
            }) + "\n"

        return Response(
            generate(),
            mimetype='application/x-ndjson',
            headers={
                'Content-Type': 'application/x-ndjson',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            }
        )  # 使用NDJSON格式

    except Exception as e:
        print(f"\nLLM节点抽取异常: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'LLM节点抽取失败: {str(e)}',
            'status': 500
        }), 500


def fetch_announcements_by_ids(announcement_ids):
    if not announcement_ids:
        return None

    engine = get_sqlalchemy_engine()
    try:
        query = text("""
            SELECT id, title, content, date, stock_num 
            FROM finkg1.announce_data
            WHERE id IN :ids
            ORDER BY date DESC
        """)

        with engine.connect() as connection:
            result = connection.execute(query, {'ids': tuple(announcement_ids)})
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            return df if not df.empty else None

    except Exception as e:
        print(f"获取公告数据异常: {str(e)}")
        traceback.print_exc()
        return None
    finally:
        engine.dispose()


@llmGenKG_bp.route('/get_nodes_by_project', methods=['GET'])
def get_nodes_by_project():
    """根据项目ID从数据库获取所有节点（已去重）"""
    try:
        project_id = request.args.get('project_id')
        if not project_id:
            return jsonify({
                'success': False,
                'message': '项目ID不能为空',
                'status': 400
            }), 400

        engine = get_sqlalchemy_engine()
        with engine.connect() as connection:
            query = text("""
                SELECT id, type, value, `key`, properties 
                FROM node_table 
                WHERE project_id = :project_id
                ORDER BY type DESC, value ASC
            """)
            result = connection.execute(query, {"project_id": project_id})
            nodes = []
            seen_ids = set()
            for row in result:
                if row.id not in seen_ids:
                    seen_ids.add(row.id)
                    nodes.append({
                        "id": row.id,
                        "type": row.type,
                        "value": row.value,
                        "key": row.key,
                        "properties": json.loads(row.properties) if isinstance(row.properties, str) else row.properties
                    })

            return jsonify({
                'success': True,
                'message': '获取节点成功',
                'status': 200,
                'data': {
                    'nodes': nodes,
                    'count': len(nodes),
                    'project_id': project_id
                }
            })

    except Exception as e:
        print(f"获取节点异常: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'获取节点失败: {str(e)}',
            'status': 500
        }), 500
    finally:
        engine.dispose()


@llmGenKG_bp.route('/delete_nodes_by_project', methods=['POST'])
def delete_nodes_by_project():
    """根据项目ID删除所有节点"""
    engine = None
    try:
        # 获取项目ID（支持两种方式）
        project_id = None

        # 方式1：从JSON body获取
        if request.is_json:
            data = request.get_json()
            project_id = data.get('project_id')
        # 方式2：从URL参数获取
        else:
            project_id = request.args.get('project_id')

        if not project_id:
            return jsonify({
                'success': False,
                'message': '项目ID不能为空',
                'status': 400
            }), 400

        engine = get_sqlalchemy_engine()
        with engine.connect() as connection:
            # 删除该项目所有节点
            delete_stmt = text("DELETE FROM node_table WHERE project_id = :project_id")
            result = connection.execute(delete_stmt, {"project_id": project_id})
            connection.commit()

            deleted_count = result.rowcount
            print(f"已删除项目 {project_id} 的 {deleted_count} 个节点")

            return jsonify({
                'success': True,
                'message': f'成功删除 {deleted_count} 个节点',
                'status': 200,
                'data': {
                    'deleted_count': deleted_count,
                    'project_id': project_id
                }
            })

    except Exception as e:
        print(f"删除节点异常: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'删除节点失败: {str(e)}',
            'status': 500
        }), 500
    finally:
        if engine is not None:
            engine.dispose()


# 关系抽取类型映射
RELATION_TYPES = {
    'causal': '因果关系',
    'temporal': '时序关系',
    'general': '通用关系'
}

# 关系抽取提示词模板
RELATION_PROMPTS = {
    'causal': """你是上市公司披露文本上的「因果关系」抽取器。仅在给定节点列表与公告片段可支撑时建立因果边。

【输出】JSON：{"edges":[{"from":"节点ID","to":"节点ID","type":"因果关系","value":"短语","context":"摘录"}]}
【约束】
- from 为因/条件侧，to 为果/结果侧；不得颠倒。
- value：2～10 字因果表述（如「业绩下滑拖累股价」「流动性收紧抬升融资成本」），禁止单独使用「相关」「影响」。
- context：30～90 字，须含可复核的因果线索（原文摘录或忠实概括）。
- 若文本无法支持因果链条，返回空 edges 数组。

仅输出 JSON，勿 markdown。""",

    'temporal': """你是上市公司披露文本上的「时序关系」抽取器：识别程序性先后、事件的时间顺序。

【输出】JSON：{"edges":[{"from":"前序节点ID","to":"后续节点ID","type":"时序关系","value":"短语","context":"摘录"}]}
【约束】
- from 时间上先于 to；若公告未体现先后，不要编造。
- value：如「先于」「之后」「同日披露」「审议在前」等具体先后表述（禁止单独「相关」）。
- context：须包含时间或程序顺序线索（如「董事会审议通过后提交股东大会」）。

仅输出 JSON，勿 markdown。""",

    'general': """你是面向金融知识图谱的多类型关系抽取器，输入为节点清单 + 公告片段。任务是在可证据支撑的前提下抽边。

【优先关注的金融关系类型】披露关系、行情波动关系、业绩关系、股权关系、融资关系、协议关系、供应链关系、人事关系、监管关系、行业联动关系、资产交易关系、因果关系、时序关系。
【金融敏感度要求】对股价涨跌、成交量放大、换手率变化、板块联动、业绩预增预减、增减持、回购、质押、担保、问询函、处罚、并购重组、关联交易等信号保持高敏感度，优先把这些金融事实转成关系。
【语义要求】
- 关系必须表达真实业务语义，不得因为节点处于同一篇样本就连边。
- 例如：若文本体现“A公司发布B公告/披露某事项”，应抽为「披露关系 / 发布公告」或「披露关系 / 披露事项」；不得写成「同样本关联」。
- 若文本体现公司或板块触发股价异动、业绩变动、监管动作，应优先使用金融语义关系类型。

【每条边】from / to（须来自节点列表）、type（中文）、value（2～12 字具体短语）、context（25～90 字，支撑该关系的原文依据）。
严禁 value 仅为「相关」「影响」「关联」「涉及」。无法判断时宁可不输出该边。
严禁使用「文本共现」「同段共现」「单纯共现」「同样本关联」作为关系类型或 value——这类不是真实语义关系，一律不得输出。

【输出】仅 JSON：{"edges":[...]}，勿 markdown。""",
}


def extract_relations_with_llm(nodes: list, relation_type: str, project_id: str, announcements: list) -> Dict:
    """使用 DeepSeek API 从节点和公告文本中抽取关系（分批抽取，降低截断风险）。"""
    from openai import OpenAI

    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL
    )

    print(f"\n====== 开始{RELATION_TYPES[relation_type]}抽取 ======")
    print(f"待分析节点数量: {len(nodes)}")
    print(f"关系类型: {relation_type} ({RELATION_TYPES[relation_type]})")
    print(f"相关公告数量: {len(announcements)}")

    # 全量节点映射（用于回填 from_node/to_node）
    nodes_map = {node['id']: node for node in nodes}

    # 分批抽取，避免单次输出过长导致 JSON 截断
    batch_size = _env_int("REL_EXTRACT_BATCH_SIZE", 20)
    max_edges_per_batch = _env_int("REL_EXTRACT_MAX_EDGES_PER_BATCH", 30)
    use_sample_scoped = _env_bool("REL_EXTRACT_SAMPLE_SCOPED", True)
    ann_each_chars = _env_int("REL_EXTRACT_ANN_EACH_CHARS", 3000)
    ann_take_n = _env_int("REL_EXTRACT_ANN_TAKE_N", 8)

    extraction_units = []
    if use_sample_scoped and announcements:
        for ann in (announcements or [])[:ann_take_n]:
            content = clean_text((ann or {}).get('content', ''))[:ann_each_chars]
            if not content:
                continue
            sample_nodes = _nodes_for_sample(
                nodes,
                ann,
                content,
                max_nodes=_env_int("REL_EXTRACT_SAMPLE_NODE_MAX", 80),
            )
            if len(sample_nodes) < 2:
                continue
            extraction_units.append(
                {
                    "sample_id": str((ann or {}).get("id") or "").strip(),
                    "content": content,
                    "nodes": sample_nodes,
                }
            )

    if not extraction_units:
        ann_total_chars = _env_int("REL_EXTRACT_ANN_TOTAL_CHARS", 10000)
        combined_content = "\n\n".join(
            [clean_text((ann or {}).get('content', ''))[:ann_each_chars] for ann in (announcements or [])[:ann_take_n]]
        )[:ann_total_chars]
        extraction_units = [
            {
                "sample_id": "",
                "content": combined_content,
                "nodes": list(nodes or []),
            }
        ]

    all_processed_edges = []

    total_batches = 0
    for unit in extraction_units:
        unit_nodes = unit.get("nodes") or []
        node_batches = [unit_nodes[i:i + batch_size] for i in range(0, len(unit_nodes), batch_size)]
        total_batches += len(node_batches)

    running_batch = 0
    for unit in extraction_units:
        unit_nodes = unit.get("nodes") or []
        unit_content = str(unit.get("content") or "")
        sample_id = str(unit.get("sample_id") or "").strip()
        if not unit_content or len(unit_nodes) < 2:
            continue
        node_batches = [unit_nodes[i:i + batch_size] for i in range(0, len(unit_nodes), batch_size)]

        for batch_nodes in node_batches:
            running_batch += 1
            try:
                nodes_info = "\n".join([
                    f"ID: {node['id']} | 类型: {'事件' if node['type'] == 1 else '实体'} | 值: {node['value']} | 键: {node['key']}"
                    for node in batch_nodes
                ])

                print(
                    f"\n[关系抽取] 第 {running_batch}/{max(1, total_batches)} 批，"
                    f"sample_id={sample_id or '-'}，节点数: {len(batch_nodes)}"
                )
                print("[关系抽取] 节点摘要:")
                print(nodes_info[:500] + "..." if len(nodes_info) > 500 else nodes_info)
                print("[关系抽取] 公告摘要:")
                print(unit_content[:500] + "..." if len(unit_content) > 500 else unit_content)

                user_content = (
                    "【任务】在给定节点集合与公告摘录范围内抽取有证据支撑的金融语义关系边。\n"
                    "【硬性约束】边的 value 不得仅为「相关」「关联」「影响」「涉及」等泛词；"
                    "须为 2～12 字可复核短语（示例：「发布公告」「触发股价异动」「披露业绩预增」「收到监管问询函」）。\n"
                    "【金融优先级】优先识别披露、股价波动、板块联动、业绩变化、增减持、回购、质押、融资担保、并购重组、关联交易、监管问询/处罚等关系。\n"
                    "【禁止】不得因为节点同处一篇公告就生成『同样本关联』、『同段共现』之类关系；无明确证据时宁缺毋滥。\n"
                    "【输出】仅 JSON，顶层字段 edges；每条含 from、to、type、value、context（25～90 字，须可回溯原文）。\n"
                    f"【数量】本批最多 {max_edges_per_batch} 条边，超出请截断。\n"
                    f"【样本ID】{sample_id or 'unknown'}\n\n"
                    f"【节点列表】\n{nodes_info}\n\n"
                    f"【公告摘录】\n{unit_content}"
                )

                print("[关系抽取] 正在调用 DeepSeek API...")
                start_time = time.time()
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": RELATION_PROMPTS[relation_type]},
                        {"role": "user", "content": user_content}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=_env_int("REL_EXTRACT_MAX_TOKENS", 3000)
                )
                _usage_log(f"extract_relations_with_llm/batch={running_batch}", response)
                elapsed_time = time.time() - start_time
                print(f"[关系抽取] 第 {running_batch} 批调用完成，耗时: {elapsed_time:.2f}秒")

                result_str = response.choices[0].message.content or "{}"
                json_str = (
                    result_str.split('```json')[1].split('```')[0] if '```json' in result_str
                    else result_str.split('```')[1].split('```')[0] if '```' in result_str
                    else result_str
                )

                try:
                    result = json.loads(json_str)
                except json.JSONDecodeError as e:
                    print(f"[关系抽取] 第 {running_batch} 批 JSON 解析失败: {e}")
                    print(f"[关系抽取] 原始响应片段: {result_str[:500]}...")
                    continue

                if "edges" not in result or not isinstance(result["edges"], list):
                    print(f"[关系抽取] 第 {running_batch} 批返回缺少 edges 或格式错误，跳过")
                    continue

                if len(result["edges"]) > max_edges_per_batch:
                    result["edges"] = result["edges"][:max_edges_per_batch]
                print(f"[关系抽取] 第 {running_batch} 批初步抽取到 {len(result['edges'])} 条关系")

                for edge in result["edges"]:
                    from_id = edge.get('from')
                    to_id = edge.get('to')
                    if from_id not in nodes_map or to_id not in nodes_map:
                        print(f"[关系抽取] 警告: 跳过无效关系，节点不存在: {from_id} -> {to_id}")
                        continue

                    edge_id = hashlib.md5(
                        f"{from_id}_{to_id}_{edge.get('type', '')}_{edge.get('value', '')}_{sample_id}".encode()
                    ).hexdigest()

                    processed_edge = {
                        "id": edge_id,
                        "type": edge.get("type", "通用关系"),
                        "from": from_id,
                        "to": to_id,
                        "from_node": nodes_map[from_id],
                        "to_node": nodes_map[to_id],
                        "value": edge.get("value", ""),
                        "eventRel": edge.get("eventRel", edge.get("value", "")),
                        "project_id": project_id,
                        "properties": edge.get("properties", {})
                    }

                    if isinstance(processed_edge["properties"], str):
                        try:
                            processed_edge["properties"] = json.loads(processed_edge["properties"])
                        except json.JSONDecodeError:
                            processed_edge["properties"] = {"raw": processed_edge["properties"]}

                    processed_edge["properties"]["source"] = "LLM抽取"
                    processed_edge["properties"]["extraction_method"] = relation_type
                    processed_edge["properties"]["context"] = edge.get("context", "")
                    processed_edge["properties"]["channel"] = "B"
                    if sample_id:
                        processed_edge["properties"]["sample_id"] = sample_id
                    processed_edge["properties"].setdefault("confidence", 0.78)
                    processed_edge = _normalize_relation_edge(processed_edge)
                    processed_edge = _normalize_finance_edge_direction(processed_edge)
                    all_processed_edges.append(processed_edge)

            except Exception as e:
                print(f"[关系抽取] 第 {running_batch} 批处理异常: {type(e).__name__}: {str(e)}")
                traceback.print_exc()
                continue

    # 去重：同一对节点+同类型关系保留质量分更高的一条，避免重复
    best_by_pair = {}
    for edge in all_processed_edges:
        # 修改为 (from, to, type) 进行分组，允许多重关系存在
        pair = (edge["from"], edge["to"], edge.get("type", ""))
        prev = best_by_pair.get(pair)
        if prev is None or _edge_quality_score(edge) > _edge_quality_score(prev):
            best_by_pair[pair] = edge
    deduped_edges = list(best_by_pair.values())

    print(f"\n[关系抽取] 分批完成，总关系数: {len(all_processed_edges)}，去重后: {len(deduped_edges)}")
    print("[关系抽取] 处理后的关系示例(前3条):")
    for i, edge in enumerate(deduped_edges[:3]):
        print(f"  {i + 1}. {edge['from_node']['value']} -> {edge['to_node']['value']} | 类型: {edge['type']} | 关系: {edge['value']}")

    return {"edges": deduped_edges}


def get_announcements_by_project(project_id: str) -> list:
    """根据项目ID获取相关公告数据（优先 MongoDB，回退 MySQL）。"""
    client = None
    cursor = None
    try:
        client = get_client()
        cursor = client.cursor()

        # 获取项目中的公告ID列表
        project_query = "SELECT data_list FROM finkg1.graph_project WHERE id = %s"
        cursor.execute(project_query, (project_id,))
        project_result = cursor.fetchone()

        if not project_result:
            return []

        id_list = []
        if project_result['data_list']:
            try:
                id_list = json.loads(project_result['data_list'])
                if not isinstance(id_list, list):
                    id_list = []
            except json.JSONDecodeError:
                id_list = []

        if not id_list:
            return []

        # 优先从 MongoDB event_data 读取（与样本选择流程一致）
        mongo_samples = fetch_samples_from_mongo(id_list)
        if mongo_samples:
            return [
                {
                    "id": str(item.get("id", "")),
                    "title": item.get("title", ""),
                    "content": item.get("content", ""),
                    "date": item.get("event_time", ""),
                    "stock_num": (item.get("raw_data") or {}).get("symbol", "")
                }
                for item in mongo_samples
            ]

        # MongoDB 没拿到时回退 MySQL
        placeholders = ','.join(['%s'] * len(id_list))
        announcement_query = f"""
            SELECT id, title, content, date, stock_num 
            FROM finkg1.announce_data
            WHERE id IN ({placeholders})
            ORDER BY date DESC
            LIMIT 10
        """
        cursor.execute(announcement_query, tuple(id_list))
        result = cursor.fetchall()

        return [
            {
                "id": str(row['id']),
                "title": row['title'],
                "content": row['content'],
                "date": str(row['date']) if row['date'] else '',
                "stock_num": row['stock_num']
            }
            for row in result
        ]

    except Exception as e:
        print(f"获取公告数据异常: {str(e)}")
        traceback.print_exc()
        return []
    finally:
        if cursor:
            cursor.close()
        if client:
            client.close()


def save_edges_to_databases(
    edges: list,
    project_id: str,
    relation_type: str = None,
    *,
    replace_graph: bool = True,
):
    """将边(关系)保存到 MySQL 和 Neo4j；replace_graph=False 时为增量合并（upsert，不整体删除）。"""
    mysql_success = save_edges_to_mysql(
        edges, project_id, relation_type, replace_all=replace_graph
    )

    neo4j_success = save_edges_to_neo4j(
        edges, project_id, replace_project=replace_graph
    )

    return mysql_success and neo4j_success


def save_edges_to_mysql(
    edges: list,
    project_id: str,
    relation_type: str = None,
    *,
    replace_all: bool = True,
):
    """将边(关系)保存到 MySQL；replace_all=False 时不 DELETE，仅 INSERT .. ON DUPLICATE KEY UPDATE"""
    engine = get_sqlalchemy_engine()
    try:
        with engine.connect() as connection:
            if replace_all:
                if relation_type == 'general':
                    delete_stmt = text("DELETE FROM edge_table WHERE project_id = :project_id")
                    connection.execute(delete_stmt, {"project_id": project_id})
                elif relation_type:
                    delete_stmt = text("""
                        DELETE FROM edge_table 
                        WHERE project_id = :project_id AND properties->>'$.extraction_method' = :relation_type
                    """)
                    connection.execute(delete_stmt, {
                        "project_id": project_id,
                        "relation_type": relation_type
                    })
                else:
                    delete_stmt = text("DELETE FROM edge_table WHERE project_id = :project_id")
                    connection.execute(delete_stmt, {"project_id": project_id})

                connection.commit()

            insert_plain = text("""
                INSERT INTO edge_table 
                (id, type, `from`, `to`, eventRel, value, properties, project_id) 
                VALUES 
                (:id, :type, :from, :to, :eventRel, :value, :properties, :project_id)
            """)
            upsert_stmt = text("""
                INSERT INTO edge_table 
                (id, type, `from`, `to`, eventRel, value, properties, project_id) 
                VALUES 
                (:id, :type, :from, :to, :eventRel, :value, :properties, :project_id)
                ON DUPLICATE KEY UPDATE
                    type = VALUES(type),
                    `from` = VALUES(`from`),
                    `to` = VALUES(`to`),
                    eventRel = VALUES(eventRel),
                    value = VALUES(value),
                    properties = VALUES(properties)
            """)

            use_stmt = insert_plain if replace_all else upsert_stmt

            for edge in edges:
                properties = edge.get("properties", {})
                if relation_type and 'extraction_method' not in properties:
                    properties['extraction_method'] = relation_type

                params = {
                    "id": edge["id"],
                    "type": edge["type"],
                    "from": edge["from"],
                    "to": edge["to"],
                    "eventRel": edge["eventRel"],
                    "value": edge["value"],
                    "properties": json.dumps(properties),
                    "project_id": project_id
                }
                connection.execute(use_stmt, params)
            connection.commit()
        return True
    except Exception as e:
        print(f"保存关系到 MySQL 失败: {str(e)}")
        traceback.print_exc()
        return False
    finally:
        engine.dispose()


def save_edges_to_neo4j(
    edges: list,
    project_id: str,
    *,
    replace_project: bool = True,
):
    """将边(关系)保存到 Neo4j；replace_project=False 时不删除项目子图，仅合并本批涉轨节点与关系。"""
    neo4j = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        if replace_project:
            print(f"[Neo4j] 开始清理项目 {project_id} 的旧数据...")
            delete_rels_query = """
                MATCH ()-[r]-()
                WHERE r.project_id = $project_id
                DELETE r
            """
            neo4j.execute_query(delete_rels_query, {"project_id": project_id})

            delete_nodes_query = """
                MATCH (n:KnowledgeNode)
                WHERE n.project_id = $project_id
                DELETE n
            """
            neo4j.execute_query(delete_nodes_query, {"project_id": project_id})

            print(f"[Neo4j] 准备导入新数据...")
            nodes = get_nodes_from_database(project_id)
        else:
            all_rows = get_nodes_from_database(project_id)
            if edges:
                needed = set()
                for edge in edges or []:
                    if edge.get("from"):
                        needed.add(edge["from"])
                    if edge.get("to"):
                        needed.add(edge["to"])
                nodes = [n for n in all_rows if n.get("id") in needed]
            else:
                nodes = all_rows
            print(f"[Neo4j] 增量合并：同步节点 {len(nodes)} 个，关系 {len(edges or [])} 条")

        nodes_map = {node['id']: node for node in nodes}

        # 创建 / 同步节点
        print(f"[Neo4j] 正在 MERGE {len(nodes)} 个节点...")
        for node in nodes:
            # node_table 中的 node['type'] 来自 LLM 抽取，通常为 0/1 或 '0'/'1'
            # 这里统一映射到 Neo4j 可读的“实体/事件”，以便前端渲染区分颜色
            node_type_raw = node.get('type')
            node_type_str = str(node_type_raw).strip().lower()
            node_type = "事件" if node_type_str in ("1", "event", "事件") else "实体"

            query = """
                MERGE (n:KnowledgeNode {id: $id})
                SET n.type = $type,
                    n.value = $value,
                    n.key = $key,
                    n.name = $value,  
                    n.project_id = $project_id,
                    n += $properties
            """
            neo4j.execute_query(query, {
                "id": node['id'],
                "type": node_type,
                "value": node['value'],
                "key": node['key'],
                "project_id": project_id,
                "properties": node.get('properties', {})
            })

        # 第四步：创建关系
        print(f"[Neo4j] 正在创建 {len(edges)} 条关系...")
        print("边的数据：", edges)
        for edge in edges:
            from_node = nodes_map.get(edge['from'])
            to_node = nodes_map.get(edge['to'])

            if not from_node or not to_node:
                print(f"[Neo4j] 警告: 跳过无效关系，节点不存在: {edge['from']} -> {edge['to']}")
                continue

            # 定义关系类型
            rel_type = edge['type'].replace("关系", "").upper()

            query = """
                MATCH (a:KnowledgeNode {id: $from_id})
                MATCH (b:KnowledgeNode {id: $to_id})
                MERGE (a)-[r:%s]->(b)
                SET r.value = $value,
                    r.eventRel = $eventRel,
                    r.project_id = $project_id,
                    r += $properties
            """ % rel_type

            neo4j.execute_query(query, {
                "from_id": edge['from'],
                "to_id": edge['to'],
                "value": edge['value'],
                "eventRel": edge['eventRel'],
                "project_id": project_id,
                "properties": edge.get('properties', {})
            })

        print("[Neo4j] 数据导入完成")
        return True
    except Exception as e:
        print(f"[Neo4j] 保存关系到 Neo4j 失败: {str(e)}")
        traceback.print_exc()
        return False
    finally:
        neo4j.close()


# 保留原有的关系抽取API
@llmGenKG_bp.route('/extract_relations', methods=['POST'])
def extract_relations_api():
    """关系抽取API（返回表格数据）"""
    try:
        # 确保请求包含 JSON 数据
        if not request.is_json:
            return jsonify({
                'success': False,
                'message': '请求必须包含 JSON 数据',
                'status': 400
            }), 400
        data = request.get_json()
        project_id = data.get('project_id')
        relation_type = data.get('relation_type', 'general')
        model_base = data.get('model_base', 'llm')

        if not project_id:
            print("[关系抽取API] 错误: 缺少项目ID")
            return jsonify({
                'success': False,
                'message': '项目ID不能为空',
                'status': 400
            }), 400

        print(f"\n=== 开始关系抽取流程 ===")
        print(f"项目ID: {project_id}")
        print(f"关系类型: {relation_type}")
        print(f"模型基础: {model_base}")

        # 获取项目节点
        print("\n[关系抽取API] 从数据库获取节点数据...")
        nodes = get_nodes_from_database(project_id)
        if not nodes:
            print(f"[关系抽取API] 错误: 未找到项目 {project_id} 的节点数据")
            return jsonify({
                'success': False,
                'message': f'未找到项目 {project_id} 的节点数据',
                'status': 404
            }), 404

        print(f"获取到 {len(nodes)} 个节点")

        # 获取相关公告数据
        print("\n[关系抽取API] 获取相关公告数据...")
        announcements = get_announcements_by_project(project_id)
        if not announcements:
            print(f"[关系抽取API] 警告: 未找到项目 {project_id} 的公告数据")
            announcements = []

        print(f"获取到 {len(announcements)} 条相关公告")

        # 抽取关系
        if model_base == 'llm':
            print("\n[关系抽取API] 开始使用LLM抽取关系...")
            extraction_result = extract_relations_with_llm(nodes, relation_type, project_id, announcements)
        else:
            print("\n[关系抽取API] 使用非LLM方法抽取关系")
            extraction_result = {"edges": []}

        edges = extraction_result.get("edges", [])
        print(f"\n[关系抽取API] 抽取完成，共获得 {len(edges)} 条关系")

        # 准备返回给前端的数据（包含完整节点信息）
        frontend_edges = []
        for edge in edges:
            frontend_edge = {
                "id": edge["id"],
                "type": edge["type"],
                "from": edge["from"],
                "to": edge["to"],
                "from_node": {
                    "id": edge["from_node"]["id"],
                    "type": edge["from_node"]["type"],
                    "value": edge["from_node"]["value"],
                    "key": edge["from_node"]["key"]
                },
                "to_node": {
                    "id": edge["to_node"]["id"],
                    "type": edge["to_node"]["type"],
                    "value": edge["to_node"]["value"],
                    "key": edge["to_node"]["key"]
                },
                "value": edge["value"],
                "eventRel": edge["eventRel"],
                "properties": edge["properties"]
            }
            frontend_edges.append(frontend_edge)

        # 保存关系到数据库（MySQL 和 Neo4j）
        if edges:
            print("[关系抽取API] 正在保存关系到数据库...")
            save_success = save_edges_to_databases(edges, project_id, relation_type)
            if not save_success:
                print("[关系抽取API] 错误: 保存关系到数据库失败")
                return jsonify({
                    'success': False,
                    'message': '保存关系到数据库失败',
                    'status': 500
                }), 500
            print("[关系抽取API] 关系保存成功")

        # 保存抽取历史（含节点+关系快照）
        sample_ids = []
        try:
            client = get_client()
            cur = client.cursor()
            cur.execute("SELECT data_list FROM finkg1.graph_project WHERE id = %s", (project_id,))
            row = cur.fetchone()
            if row and row.get('data_list'):
                sample_ids = json.loads(row['data_list']) if isinstance(row['data_list'], str) else row['data_list'] or []
            cur.close()
            client.close()
        except Exception:
            pass
        history_run_id = save_extraction_history(project_id, 'relations', sample_ids, nodes, edges)

        return jsonify({
            'success': True,
            'message': '关系抽取完成',
            'status': 200,
            'data': {
                'edges': frontend_edges,  # 返回给前端的数据包含完整节点信息
                'count': len(frontend_edges),
                'project_id': project_id,
                'run_id': history_run_id,
            }
        })

    except Exception as e:
        print(f"\n[关系抽取API] 异常: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'关系抽取失败: {str(e)}',
            'status': 500
        }), 500


@llmGenKG_bp.route('/delete_edges_by_project', methods=['POST'])
def delete_edges_by_project():
    """根据项目ID删除所有关系（MySQL 和 Neo4j）"""
    engine = None
    try:
        # 获取项目ID（支持两种方式）
        project_id = None

        # 方式1：从JSON body获取
        if request.is_json:
            data = request.get_json()
            project_id = data.get('project_id')
        # 方式2：从URL参数获取
        else:
            project_id = request.args.get('project_id')

        if not project_id:
            return jsonify({
                'success': False,
                'message': '项目ID不能为空',
                'status': 400
            }), 400

        # 删除 MySQL 中的关系
        engine = get_sqlalchemy_engine()
        with engine.connect() as connection:
            # 删除该项目所有关系
            delete_stmt = text("DELETE FROM edge_table WHERE project_id = :project_id")
            result = connection.execute(delete_stmt, {"project_id": project_id})
            connection.commit()

            deleted_count = result.rowcount
            print(f"已删除项目 {project_id} 的 {deleted_count} 条 MySQL 关系")

        # 删除 Neo4j 中的关系
        neo4j_success = delete_neo4j_project_data(project_id)
        if not neo4j_success:
            raise Exception("删除 Neo4j 数据失败")

        return jsonify({
            'success': True,
            'message': f'成功删除 {deleted_count} 条关系',
            'status': 200,
            'data': {
                'deleted_count': deleted_count,
                'project_id': project_id
            }
        })

    except Exception as e:
        print(f"删除关系异常: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'删除关系失败: {str(e)}',
            'status': 500
        }), 500
    finally:
        if engine is not None:
            engine.dispose()


def delete_neo4j_project_data(project_id: str):
    """删除 Neo4j 中指定项目的所有数据"""
    neo4j = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        # 删除关系
        query = """
            MATCH ()-[r]-()
            WHERE r.project_id = $project_id
            DELETE r
        """
        neo4j.execute_query(query, {"project_id": project_id})

        # 删除节点
        query = """
            MATCH (n:KnowledgeNode)
            WHERE n.project_id = $project_id
            DELETE n
        """
        neo4j.execute_query(query, {"project_id": project_id})

        return True
    except Exception as e:
        print(f"删除 Neo4j 项目数据失败: {str(e)}")
        return False
    finally:
        neo4j.close()


def delete_mysql_edges_for_project(project_id: str) -> bool:
    """删除该项目在 MySQL edge_table 中的全部关系（过时关系清理）。"""
    engine = get_sqlalchemy_engine()
    try:
        with engine.connect() as connection:
            connection.execute(
                text("DELETE FROM edge_table WHERE project_id = :project_id"),
                {"project_id": project_id}
            )
            connection.commit()
        return True
    except Exception as e:
        print(f"[StaleAgent] 删除 MySQL 关系失败: {e}")
        traceback.print_exc()
        return False
    finally:
        engine.dispose()


def run_stale_graph_cleanup(project_id: str) -> bool:
    """
    Stale Agent：在写入新一轮关系前，清理该项目下过时的图数据。
    - MySQL：删除 edge_table 中该 project_id 的全部旧边
    - Neo4j：删除该 project_id 下全部旧节点与关系（新图在 Relation 持久化阶段由 save_edges_to_neo4j 重建）
    """
    mysql_ok = delete_mysql_edges_for_project(project_id)
    neo4j_ok = delete_neo4j_project_data(project_id)
    if not mysql_ok or not neo4j_ok:
        print(f"[StaleAgent] 清理未完全成功 mysql_ok={mysql_ok} neo4j_ok={neo4j_ok}")
        return False
    return True


def count_mysql_edges_for_project(project_id: str) -> int:
    """MySQL 中该项目关系行数。"""
    engine = get_sqlalchemy_engine()
    try:
        with engine.connect() as conn:
            q = text("SELECT COUNT(*) AS c FROM edge_table WHERE project_id = :pid")
            return int(conn.execute(q, {"pid": project_id}).scalar() or 0)
    except Exception as e:
        print(f"[StaleAssess] 统计 MySQL 边失败: {e}")
        return 0
    finally:
        engine.dispose()


def count_neo4j_knowledge_nodes(project_id: str) -> int:
    """Neo4j 中该项目 KnowledgeNode 数量。"""
    neo4j = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        rows = neo4j.execute_query(
            "MATCH (n:KnowledgeNode) WHERE n.project_id = $project_id RETURN count(n) AS c",
            {"project_id": project_id},
        )
        if not rows:
            return 0
        return int(rows[0]["c"])
    except Exception as e:
        print(f"[StaleAssess] 统计 Neo4j 节点失败: {e}")
        return 0
    finally:
        neo4j.close()


def should_run_stale_graph_cleanup(project_id: str) -> bool:
    """
    动态判断是否需要执行「过时图数据」清理：
    当前图中若已有 MySQL 关系或 Neo4j 节点，则本轮一键构建需先清理，
    避免旧边/旧图与节点抽取结果不一致。（首建无图则跳过，减少无谓删除。）
    """
    edges_n = count_mysql_edges_for_project(project_id)
    neo_n = count_neo4j_knowledge_nodes(project_id)
    return edges_n > 0 or neo_n > 0


@llmGenKG_bp.route('/kg_incremental_status', methods=['GET'])
def kg_incremental_status():
    """
    查询项目在操作库增量同步后是否被标记为「图谱可能受影响」（pending）。
    可与一键构建前的提示文案联动。
    """
    try:
        project_id = request.args.get('project_id')
        if not project_id:
            return jsonify({
                'success': False,
                'message': 'project_id 不能为空',
                'status': 400
            }), 400
        from agents.incremental_kg_impact import get_incremental_impact_record

        rec = get_incremental_impact_record(project_id)
        pending = bool(rec and int(rec.get('pending') or 0) == 1)
        return jsonify({
            'success': True,
            'status': 200,
            'data': {
                'project_id': project_id,
                'pending': pending,
                'record': rec,
            }
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e),
            'status': 500
        }), 500


@llmGenKG_bp.route('/get_neo4j_graph', methods=['GET'])
def get_neo4j_graph():
    """从 Neo4j 数据库获取图谱数据（节点和关系）用于前端可视化"""
    try:
        project_id = request.args.get('project_id')
        if not project_id:
            return jsonify({
                'success': False,
                'message': '项目ID不能为空',
                'status': 400
            }), 400

        neo4j = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        try:
            # 从 Neo4j 获取节点数据
            nodes_query = """
                MATCH (n:KnowledgeNode)
                WHERE n.project_id = $project_id
                RETURN n.id as id, n.type as type, n.value as value, n.key as key, n.name as name, properties(n) as props
            """
            nodes_result = neo4j.execute_query(nodes_query, {"project_id": project_id})
            
            nodes = []
            nodes_map = {}
            for node_row in nodes_result:
                node_data = {
                    "id": node_row['id'],
                    "type": node_row['type'],
                    "value": node_row['value'],
                    "key": node_row['key'],
                    "name": node_row['name'] or node_row['value'],
                    "properties": node_row['props'] or {}
                }
                nodes.append(node_data)
                nodes_map[node_row['id']] = node_data
            
            # 从 Neo4j 获取关系数据
            edges_query = """
                MATCH (a:KnowledgeNode {project_id: $project_id})-[r]-(b:KnowledgeNode {project_id: $project_id})
                RETURN a.id as from_id, b.id as to_id, type(r) as rel_type, r.value as value, r.eventRel as eventRel, properties(r) as props
            """
            edges_result = neo4j.execute_query(edges_query, {"project_id": project_id})
            
            edges = []
            edge_set = set()
            for edge_row in edges_result:
                # 避免重复关系（无向）
                edge_key = tuple(sorted([edge_row['from_id'], edge_row['to_id']]))
                if edge_key not in edge_set:
                    edge_set.add(edge_key)
                    edges.append({
                        "id": f"{edge_row['from_id']}-{edge_row['to_id']}",
                        "type": edge_row['rel_type'],
                        "from": edge_row['from_id'],
                        "to": edge_row['to_id'],
                        "value": edge_row['value'] or '',
                        "eventRel": edge_row['eventRel'] or '',
                        "properties": edge_row['props'] or {}
                    })

            return jsonify({
                'success': True,
                'message': '从 Neo4j 获取图谱数据成功',
                'status': 200,
                'data': {
                    'nodes': nodes,
                    'edges': edges,
                    'project_id': project_id
                }
            })
        finally:
            neo4j.close()
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'从 Neo4j 获取图谱数据失败: {str(e)}',
            'status': 500
        }), 500


def get_nodes_from_database(project_id: str) -> list:
    """从数据库获取节点数据（已去重）"""
    engine = get_sqlalchemy_engine()
    try:
        with engine.connect() as connection:
            query = text("""
                SELECT id, type, value, `key`, properties 
                FROM node_table 
                WHERE project_id = :project_id
            """)
            result = connection.execute(query, {"project_id": project_id})
            nodes = []
            seen_ids = set()
            for row in result:
                if row.id not in seen_ids:
                    seen_ids.add(row.id)
                    nodes.append({
                        "id": row.id,
                        "type": row.type,
                        "value": row.value,
                        "key": row.key,
                        "properties": json.loads(row.properties) if isinstance(row.properties, str) else row.properties
                    })
            return nodes
    except Exception as e:
        print(f"获取节点数据异常: {str(e)}")
        return []
    finally:
        engine.dispose()


@llmGenKG_bp.route('/get_edges_by_project', methods=['GET'])
def get_edges_by_project():
    """根据项目ID获取所有关系（包含完整节点信息）"""
    try:
        project_id = request.args.get('project_id')
        if not project_id:
            return jsonify({
                'success': False,
                'message': '项目ID不能为空',
                'status': 400
            }), 400

        # 获取节点数据
        nodes = get_nodes_from_database(project_id)
        nodes_map = {node['id']: node for node in nodes}

        # 获取边数据
        edges = []
        engine = get_sqlalchemy_engine()
        with engine.connect() as connection:
            query = text("""
                SELECT id, type, `from` as from_, `to`, eventRel, value, properties 
                FROM edge_table 
                WHERE project_id = :project_id
            """)
            result = connection.execute(query, {"project_id": project_id})

            for row in result:
                from_node = nodes_map.get(row.from_)
                to_node = nodes_map.get(row.to)

                if not from_node or not to_node:
                    continue  # 跳过无效关系

                edges.append({
                    "id": row.id,
                    "type": row.type,
                    "from": row.from_,
                    "to": row.to,
                    "from_node": {
                        "id": from_node["id"],
                        "type": from_node["type"],
                        "value": from_node["value"],
                        "key": from_node["key"]
                    },
                    "to_node": {
                        "id": to_node["id"],
                        "type": to_node["type"],
                        "value": to_node["value"],
                        "key": to_node["key"]
                    },
                    "value": row.value,
                    "eventRel": row.eventRel,
                    "properties": json.loads(row.properties) if isinstance(row.properties, str) else row.properties
                })

        return jsonify({
            'success': True,
            'message': '获取关系成功',
            'status': 200,
            'data': {
                'edges': edges,
                'count': len(edges),
                'project_id': project_id
            }
        })

    except Exception as e:
        print(f"获取关系异常: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'获取关系失败: {str(e)}',
            'status': 500
        }), 500
    finally:
        engine.dispose()


@llmGenKG_bp.route('/update_node', methods=['PATCH', 'POST'])
def update_node():
    """更新节点：支持修改 value, type, key, properties，同步 MySQL 和 Neo4j"""
    try:
        data = request.get_json() or {}
        project_id = data.get('project_id')
        node_id = data.get('node_id')
        if not project_id or not node_id:
            return jsonify({
                'success': False,
                'message': 'project_id 和 node_id 不能为空',
                'status': 400
            }), 400

        updates = {}
        if 'value' in data:
            updates['value'] = data['value']
        if 'type' in data:
            updates['type'] = data['type']
        if 'key' in data:
            updates['key'] = data['key']
        if 'properties' in data:
            updates['properties'] = data['properties']

        if not updates:
            return jsonify({
                'success': False,
                'message': '没有要更新的字段',
                'status': 400
            }), 400

        engine = get_sqlalchemy_engine()
        with engine.connect() as connection:
            # 构建动态 UPDATE
            set_parts = []
            params = {"project_id": project_id, "node_id": node_id}
            if 'value' in updates:
                set_parts.append("value = :value")
                params['value'] = updates['value']
            if 'type' in updates:
                set_parts.append("type = :type")
                params['type'] = updates['type']
            if 'key' in updates:
                set_parts.append("`key` = :key")
                params['key'] = updates['key']
            if 'properties' in updates:
                set_parts.append("properties = :properties")
                props = updates['properties']
                params['properties'] = json.dumps(props) if isinstance(props, dict) else props

            update_stmt = text(f"""
                UPDATE node_table 
                SET {', '.join(set_parts)}
                WHERE project_id = :project_id AND id = :node_id
            """)
            result = connection.execute(update_stmt, params)
            connection.commit()
            if result.rowcount == 0:
                return jsonify({
                    'success': False,
                    'message': f'未找到节点 {node_id}',
                    'status': 404
                }), 404

        # 同步到 Neo4j
        nodes = get_nodes_from_database(project_id)
        node = next((n for n in nodes if n['id'] == node_id), None)
        if node:
            neo4j = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
            try:
                props = node.get('properties', {})
                query = """
                    MATCH (n:KnowledgeNode {id: $id})
                    WHERE n.project_id = $project_id
                    SET n.value = $value,
                        n.type = $type,
                        n.key = $key,
                        n += $properties
                """
                neo4j.execute_query(query, {
                    "id": node_id,
                    "project_id": project_id,
                    "value": node['value'],
                    "type": node['type'],
                    "key": node.get('key', ''),
                    "properties": props
                })
            finally:
                neo4j.close()

        return jsonify({
            'success': True,
            'message': '节点更新成功',
            'status': 200
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'更新节点失败: {str(e)}',
            'status': 500
        }), 500


@llmGenKG_bp.route('/update_edge', methods=['PATCH', 'POST'])
def update_edge():
    """更新边(关系)：支持修改 value, eventRel, properties，同步 MySQL 和 Neo4j"""
    try:
        data = request.get_json() or {}
        project_id = data.get('project_id')
        edge_id = data.get('edge_id')
        if not project_id or not edge_id:
            return jsonify({
                'success': False,
                'message': 'project_id 和 edge_id 不能为空',
                'status': 400
            }), 400

        updates = {}
        if 'value' in data:
            updates['value'] = data['value']
        if 'eventRel' in data:
            updates['eventRel'] = data['eventRel']
        if 'properties' in data:
            updates['properties'] = data['properties']

        if not updates:
            return jsonify({
                'success': False,
                'message': '没有要更新的字段',
                'status': 400
            }), 400

        engine = get_sqlalchemy_engine()
        with engine.connect() as connection:
            set_parts = []
            params = {"project_id": project_id, "edge_id": edge_id}
            if 'value' in updates:
                set_parts.append("value = :value")
                params['value'] = updates['value']
            if 'eventRel' in updates:
                set_parts.append("eventRel = :eventRel")
                params['eventRel'] = updates['eventRel']
            if 'properties' in updates:
                set_parts.append("properties = :properties")
                props = updates['properties']
                params['properties'] = json.dumps(props) if isinstance(props, dict) else props

            update_stmt = text(f"""
                UPDATE edge_table 
                SET {', '.join(set_parts)}
                WHERE project_id = :project_id AND id = :edge_id
            """)
            result = connection.execute(update_stmt, params)
            connection.commit()
            if result.rowcount == 0:
                return jsonify({
                    'success': False,
                    'message': f'未找到关系 {edge_id}',
                    'status': 404
                }), 404

        # 同步到 Neo4j：需要 from/to 定位关系，先查 edge
        with engine.connect() as conn:
            q = text("""
                SELECT `from`, `to`, value, eventRel, properties 
                FROM edge_table 
                WHERE project_id = :project_id AND id = :edge_id
            """)
            row = conn.execute(q, {"project_id": project_id, "edge_id": edge_id}).fetchone()
        engine.dispose()

        if row:
            neo4j = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
            try:
                props = json.loads(row.properties) if isinstance(row.properties, str) else row.properties
                # Neo4j 关系类型从 edge type 得来，这里用通用方式更新属性
                query = """
                    MATCH (a:KnowledgeNode {id: $from_id})-[r]->(b:KnowledgeNode {id: $to_id})
                    WHERE r.project_id = $project_id
                    SET r.value = $value,
                        r.eventRel = $eventRel,
                        r += $properties
                """
                neo4j.execute_query(query, {
                    "from_id": row.from_,
                    "to_id": row.to,
                    "project_id": project_id,
                    "value": row.value,
                    "eventRel": row.eventRel,
                    "properties": props
                })
            finally:
                neo4j.close()

        return jsonify({
            'success': True,
            'message': '关系更新成功',
            'status': 200
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'更新关系失败: {str(e)}',
            'status': 500
        }), 500


def _query_isolated_node_ids(connection, project_id: str, node_ids: list) -> list:
    """查询给定节点中哪些节点已成为孤立节点（无任何入边/出边）。"""
    cleaned_ids = [str(nid).strip() for nid in (node_ids or []) if str(nid).strip()]
    if not cleaned_ids:
        return []

    id_params = {f"id_{idx}": nid for idx, nid in enumerate(cleaned_ids)}
    in_clause = ", ".join([f":id_{idx}" for idx in range(len(cleaned_ids))])
    sql = text(f"""
        SELECT n.id
        FROM node_table n
        LEFT JOIN edge_table e
          ON e.project_id = n.project_id
         AND (e.`from` = n.id OR e.`to` = n.id)
        WHERE n.project_id = :project_id
          AND n.id IN ({in_clause})
        GROUP BY n.id
        HAVING COUNT(e.id) = 0
    """)
    rows = connection.execute(sql, {"project_id": project_id, **id_params}).fetchall()
    return [str(r.id) for r in rows if getattr(r, 'id', None)]


@llmGenKG_bp.route('/delete_node', methods=['POST'])
def delete_node():
    """删除单个节点：MySQL 级联删除关联边，并同步 Neo4j。"""
    engine = None
    try:
        data = request.get_json() or {}
        project_id = str(data.get('project_id') or '').strip()
        node_id = str(data.get('node_id') or '').strip()
        if not project_id or not node_id:
            return jsonify({
                'success': False,
                'message': 'project_id 和 node_id 不能为空',
                'status': 400
            }), 400

        engine = get_sqlalchemy_engine()
        with engine.connect() as connection:
            exists_row = connection.execute(
                text("""
                    SELECT id
                    FROM node_table
                    WHERE project_id = :project_id AND id = :node_id
                    LIMIT 1
                """),
                {"project_id": project_id, "node_id": node_id}
            ).fetchone()
            if not exists_row:
                return jsonify({
                    'success': False,
                    'message': f'未找到节点 {node_id}',
                    'status': 404
                }), 404

            affected_rows = connection.execute(
                text("""
                    SELECT DISTINCT
                        CASE
                            WHEN `from` = :node_id THEN `to`
                            ELSE `from`
                        END AS neighbor_id
                    FROM edge_table
                    WHERE project_id = :project_id
                      AND (`from` = :node_id OR `to` = :node_id)
                """),
                {"project_id": project_id, "node_id": node_id}
            ).fetchall()
            affected_node_ids = [
                str(r.neighbor_id).strip() for r in affected_rows if getattr(r, 'neighbor_id', None)
            ]

            deleted_edges_result = connection.execute(
                text("""
                    DELETE FROM edge_table
                    WHERE project_id = :project_id
                      AND (`from` = :node_id OR `to` = :node_id)
                """),
                {"project_id": project_id, "node_id": node_id}
            )
            connection.execute(
                text("""
                    DELETE FROM node_table
                    WHERE project_id = :project_id AND id = :node_id
                """),
                {"project_id": project_id, "node_id": node_id}
            )

            isolated_node_ids = _query_isolated_node_ids(connection, project_id, affected_node_ids)
            connection.commit()

        neo4j = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        try:
            neo4j.execute_query(
                """
                    MATCH (n:KnowledgeNode {id: $node_id})
                    WHERE n.project_id = $project_id
                    DETACH DELETE n
                """,
                {"project_id": project_id, "node_id": node_id}
            )
        finally:
            neo4j.close()

        return jsonify({
            'success': True,
            'message': '节点删除成功',
            'status': 200,
            'data': {
                'deleted_node_id': node_id,
                'deleted_related_edges_count': int(deleted_edges_result.rowcount or 0),
                'affected_node_ids': affected_node_ids,
                'isolated_node_ids': isolated_node_ids,
                'project_id': project_id,
            }
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'删除节点失败: {str(e)}',
            'status': 500
        }), 500
    finally:
        if engine is not None:
            engine.dispose()


@llmGenKG_bp.route('/delete_edge', methods=['POST'])
def delete_edge():
    """删除单条关系：保留节点，返回受影响节点及孤立节点信息。"""
    engine = None
    try:
        data = request.get_json() or {}
        project_id = str(data.get('project_id') or '').strip()
        edge_id = str(data.get('edge_id') or '').strip()
        if not project_id or not edge_id:
            return jsonify({
                'success': False,
                'message': 'project_id 和 edge_id 不能为空',
                'status': 400
            }), 400

        engine = get_sqlalchemy_engine()
        with engine.connect() as connection:
            edge_row = connection.execute(
                text("""
                    SELECT id, `from` AS from_id, `to` AS to_id, value, eventRel, properties
                    FROM edge_table
                    WHERE project_id = :project_id AND id = :edge_id
                    LIMIT 1
                """),
                {"project_id": project_id, "edge_id": edge_id}
            ).fetchone()
            if not edge_row:
                return jsonify({
                    'success': False,
                    'message': f'未找到关系 {edge_id}',
                    'status': 404
                }), 404

            connection.execute(
                text("""
                    DELETE FROM edge_table
                    WHERE project_id = :project_id AND id = :edge_id
                """),
                {"project_id": project_id, "edge_id": edge_id}
            )

            affected_node_ids = [
                str(edge_row.from_id).strip(),
                str(edge_row.to_id).strip(),
            ]
            affected_node_ids = [nid for nid in dict.fromkeys(affected_node_ids) if nid]
            isolated_node_ids = _query_isolated_node_ids(connection, project_id, affected_node_ids)
            connection.commit()

        props = {}
        if isinstance(edge_row.properties, str):
            try:
                props = json.loads(edge_row.properties)
            except Exception:
                props = {}
        elif isinstance(edge_row.properties, dict):
            props = edge_row.properties

        sample_id = str((props or {}).get('sample_id') or '').strip()
        cypher = """
            MATCH (a:KnowledgeNode {id: $from_id})-[r]->(b:KnowledgeNode {id: $to_id})
            WHERE r.project_id = $project_id
              AND coalesce(r.value, '') = $value
              AND coalesce(r.eventRel, '') = $eventRel
        """
        cypher_params = {
            "from_id": str(edge_row.from_id),
            "to_id": str(edge_row.to_id),
            "project_id": project_id,
            "value": str(edge_row.value or ''),
            "eventRel": str(edge_row.eventRel or ''),
        }
        if sample_id:
            cypher += "\n  AND coalesce(toString(r.sample_id), '') = $sample_id"
            cypher_params["sample_id"] = sample_id
        cypher += "\nDELETE r"

        neo4j = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        try:
            neo4j.execute_query(cypher, cypher_params)
        finally:
            neo4j.close()

        return jsonify({
            'success': True,
            'message': '关系删除成功',
            'status': 200,
            'data': {
                'deleted_edge_id': edge_id,
                'affected_node_ids': affected_node_ids,
                'isolated_node_ids': isolated_node_ids,
                'project_id': project_id,
            }
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'删除关系失败: {str(e)}',
            'status': 500
        }), 500
    finally:
        if engine is not None:
            engine.dispose()


def _normalize_node_for_snapshot(n):
    """将节点转为快照格式，type 统一为 实体/事件"""
    t = n.get('type')
    if t == 0 or t == '0':
        type_str = '实体'
    elif t == 1 or t == '1':
        type_str = '事件'
    else:
        type_str = t if isinstance(t, str) else '实体'
    return {
        "id": n.get("id"),
        "type": type_str,
        "value": n.get("value", ""),
        "key": n.get("key", ""),
        "properties": n.get("properties", {})
    }


def _normalize_edge_for_snapshot(e):
    """将边转为快照格式"""
    src = e.get("from") if isinstance(e, dict) else None
    if not src and isinstance(e, dict):
        src = e.get("source")
    dst = e.get("to") if isinstance(e, dict) else None
    if not dst and isinstance(e, dict):
        dst = e.get("target")
    return {
        "id": e.get("id"),
        "from": src,
        "to": dst,
        "type": e.get("type", ""),
        "value": e.get("value", ""),
        "eventRel": e.get("eventRel", ""),
        "properties": e.get("properties", {})
    }


def _default_extraction_title(run_type: str, nodes_count: int, edges_count: int) -> str:
    """侧栏展示用标题（风格接近会话列表：类型 + 规模 + 时间）。"""
    type_map = {
        "nodes": "节点抽取",
        "relations": "关系抽取",
        "master": "一键构建",
        "incremental": "增量构建",
    }
    label = type_map.get(run_type, run_type or "图谱构建")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"{label} · {nodes_count}节点/{edges_count}边 · {now}"


def _json_safe_default(value):
    """Serialize uncommon values in snapshot payloads to avoid hard failures."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (set, tuple)):
        return list(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return str(value)


def _json_dumps_safe(value) -> str:
    return json.dumps(value, ensure_ascii=False, default=_json_safe_default)


def save_extraction_history(
    project_id: str,
    run_type: str,
    sample_ids: list,
    nodes: list,
    edges: list,
    *,
    run_id: Optional[str] = None,
    title: Optional[str] = None,
    user_id: Optional[str] = None,
    workflow_meta: Optional[Dict[str, Any]] = None,
) -> str:
    """
    保存抽取历史快照，返回 run_id。
    若传入 run_id（如 Master Agent 的 workflow run_id），则与接口返回、侧栏 ?run= 一致。
    """
    rid = (run_id or "").strip() or str(uuid.uuid4())
    nodes_norm = [_normalize_node_for_snapshot(n) for n in nodes]
    edges_norm = [_normalize_edge_for_snapshot(e) for e in edges]
    ttl = (title or "").strip() or _default_extraction_title(
        run_type, len(nodes_norm), len(edges_norm)
    )
    uid = str(user_id).strip() if user_id is not None else None
    _ensure_extraction_history_schema()
    engine = get_sqlalchemy_engine()
    try:
        with engine.connect() as conn:
            insert_full = text("""
                INSERT INTO extraction_history
                (run_id, project_id, user_id, run_type, title, sample_ids, nodes_count, edges_count, nodes_snapshot, edges_snapshot, workflow_meta_snapshot)
                VALUES (:run_id, :project_id, :user_id, :run_type, :title, :sample_ids, :nodes_count, :edges_count, :nodes_snapshot, :edges_snapshot, :workflow_meta_snapshot)
            """)
            insert_legacy = text("""
                INSERT INTO extraction_history
                (run_id, project_id, run_type, sample_ids, nodes_count, edges_count, nodes_snapshot, edges_snapshot)
                VALUES (:run_id, :project_id, :run_type, :sample_ids, :nodes_count, :edges_count, :nodes_snapshot, :edges_snapshot)
            """)
            params_full = {
                "run_id": rid,
                "project_id": project_id,
                "user_id": uid,
                "run_type": run_type,
                "title": ttl,
                "sample_ids": _json_dumps_safe(sample_ids or []),
                "nodes_count": len(nodes_norm),
                "edges_count": len(edges_norm),
                "nodes_snapshot": _json_dumps_safe(nodes_norm),
                "edges_snapshot": _json_dumps_safe(edges_norm),
                "workflow_meta_snapshot": _json_dumps_safe(workflow_meta or {}),
            }
            params_legacy = {
                "run_id": rid,
                "project_id": project_id,
                "run_type": run_type,
                "sample_ids": _json_dumps_safe(sample_ids or []),
                "nodes_count": len(nodes_norm),
                "edges_count": len(edges_norm),
                "nodes_snapshot": _json_dumps_safe(nodes_norm),
                "edges_snapshot": _json_dumps_safe(edges_norm),
            }
            try:
                conn.execute(insert_full, params_full)
            except Exception as e1:
                err = str(e1).lower()
                if "unknown column" in err or "doesn't exist" in err:
                    conn.execute(insert_legacy, params_legacy)
                else:
                    raise
            conn.commit()
    except Exception as e:
        print(f"保存抽取历史失败: {e}")
        traceback.print_exc()
        raise
    finally:
        engine.dispose()
    return rid


def _ensure_extraction_history_schema():
    """为抽取历史补齐 title/user_id/workflow_meta_snapshot 列，便于任务级管理与报告回放。"""
    engine = get_sqlalchemy_engine()
    try:
        with engine.connect() as conn:
            q = text(
                """
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'extraction_history'
                                    AND COLUMN_NAME IN ('title', 'user_id', 'workflow_meta_snapshot')
                """
            )
            cols = {str(row[0]) for row in conn.execute(q).fetchall()}
            if 'user_id' not in cols:
                conn.execute(
                    text(
                        "ALTER TABLE extraction_history ADD COLUMN user_id VARCHAR(64) NULL COMMENT '操作人（与 graph_project.creator 对齐）' AFTER project_id"
                    )
                )
            if 'title' not in cols:
                conn.execute(
                    text(
                        "ALTER TABLE extraction_history ADD COLUMN title VARCHAR(255) NULL COMMENT '列表展示标题（与会话首条摘要类似）' AFTER run_type"
                    )
                )
            if 'workflow_meta_snapshot' not in cols:
                conn.execute(
                    text(
                        "ALTER TABLE extraction_history ADD COLUMN workflow_meta_snapshot LONGTEXT NULL COMMENT '构建流程元信息快照（quality_report等）' AFTER edges_snapshot"
                    )
                )
            conn.commit()
    except Exception as e:
        print(f"[extraction_history] schema ensure skipped: {e}")
    finally:
        engine.dispose()


def _get_project_sample_ids(project_id: str) -> list:
    client = None
    cur = None
    try:
        client = get_client()
        cur = client.cursor()
        cur.execute("SELECT data_list FROM finkg1.graph_project WHERE id = %s", (project_id,))
        row = cur.fetchone()
        raw = row.get('data_list') if row else []
        if isinstance(raw, str):
            return json.loads(raw) if raw else []
        return raw or []
    except Exception:
        return []
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if client:
                client.close()
        except Exception:
            pass


def _get_edges_from_database(project_id: str) -> list:
    nodes = get_nodes_from_database(project_id)
    nodes_map = {node['id']: node for node in nodes}
    engine = get_sqlalchemy_engine()
    try:
        with engine.connect() as connection:
            query = text(
                """
                SELECT id, type, `from` as from_, `to`, eventRel, value, properties
                FROM edge_table
                WHERE project_id = :project_id
                """
            )
            result = connection.execute(query, {"project_id": project_id})
            edges = []
            for row in result:
                from_node = nodes_map.get(row.from_)
                to_node = nodes_map.get(row.to)
                if not from_node or not to_node:
                    continue
                edges.append({
                    "id": row.id,
                    "type": row.type,
                    "from": row.from_,
                    "to": row.to,
                    "from_node": {
                        "id": from_node["id"],
                        "type": from_node["type"],
                        "value": from_node["value"],
                        "key": from_node["key"],
                    },
                    "to_node": {
                        "id": to_node["id"],
                        "type": to_node["type"],
                        "value": to_node["value"],
                        "key": to_node["key"],
                    },
                    "value": row.value,
                    "eventRel": row.eventRel,
                    "properties": json.loads(row.properties) if isinstance(row.properties, str) else row.properties,
                })
            return edges
    except Exception as e:
        print(f"获取关系数据异常: {str(e)}")
        return []
    finally:
        engine.dispose()


def _normalize_sample_id_set(raw: Union[Any, None]) -> set:
    """将各类样本 ID 列表规范为字符串集合，便于对比。"""
    if raw is None:
        return set()
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="ignore")
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return set()
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                raw = parsed
            else:
                return {raw} if raw != "None" else set()
        except json.JSONDecodeError:
            return {raw} if raw != "None" else set()
    out = set()
    for x in raw if isinstance(raw, (list, tuple, set)) else [raw]:
        s = str(x).strip()
        if s and s != "None":
            out.add(s)
    return out


def get_last_effective_build_record(project_id: str) -> Optional[Dict[str, Any]]:
    """
    最近一次可用于样本基线对比的抽取记录（不限于 master）。
    兼容用户在项目下新建抽取任务后，点击一键构建仍应基于最新抽取基线做 noop/incremental/prune 判定。
    """
    _ensure_extraction_history_schema()
    engine = get_sqlalchemy_engine()
    try:
        with engine.connect() as conn:
            q = text(
                """
                SELECT run_id, run_type, sample_ids
                FROM extraction_history
                WHERE project_id = :pid
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
            row = conn.execute(q, {"pid": project_id}).fetchone()
            if not row:
                return None
            m = row._mapping if hasattr(row, "_mapping") else dict(row)
            sid = m.get("sample_ids")
            if isinstance(sid, str):
                try:
                    sid = json.loads(sid)
                except json.JSONDecodeError:
                    sid = []
            return {
                "run_id": str(m.get("run_id") or "").strip(),
                "run_type": str(m.get("run_type") or "").strip(),
                "sample_ids": _normalize_sample_id_set(sid),
            }
    except Exception as e:
        print(f"[MasterDelta] 读取最近抽取基线失败: {e}")
        return None
    finally:
        engine.dispose()


def get_last_master_run_id(project_id: str) -> str:
    _ensure_extraction_history_schema()
    engine = get_sqlalchemy_engine()
    try:
        with engine.connect() as conn:
            q = text(
                """
                SELECT run_id FROM extraction_history
                WHERE project_id = :pid AND run_type = 'master'
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
            row = conn.execute(q, {"pid": project_id}).fetchone()
            return str(row[0]).strip() if row and row[0] else ""
    except Exception:
        return ""
    finally:
        engine.dispose()


def analyze_master_build_sample_delta(project_id: str, current_sample_ids: list) -> Dict[str, Any]:
    """
    对比当前请求样本集与上次一键构建(master)记录。
    - noop：集合完全一致（且下文应配合「图中仍有数据」判断）
    - incremental_only：仅新增样本
    - prune_only：仅移除样本（需在图中删掉对应子图）
    - incremental_and_prune：新增且移除
    - full：无上一次 master 记录 → 走完整构建
    """
    cur = _normalize_sample_id_set(current_sample_ids)
    baseline_record = get_last_effective_build_record(project_id)
    if baseline_record is None:
        return {"kind": "full", "reason": "no_prior_history"}
    baseline = baseline_record.get("sample_ids") or set()
    if cur == baseline:
        return {
            "kind": "noop",
            "reason": "samples_unchanged",
            "baseline_run_id": baseline_record.get("run_id"),
            "baseline_run_type": baseline_record.get("run_type"),
        }
    added = sorted(cur - baseline)
    removed = sorted(baseline - cur)
    if added and removed:
        return {
            "kind": "incremental_and_prune",
            "added_sample_ids": added,
            "removed_sample_ids": removed,
        }
    if added:
        return {"kind": "incremental_only", "added_sample_ids": added}
    return {"kind": "prune_only", "removed_sample_ids": removed}


@llmGenKG_bp.route('/preview_master_build_path', methods=['POST'])
def preview_master_build_path_api():
    """
    一键构建前置预判：返回本次将走的路径（noop / incremental / prune / full）。
    用于前端在点击后一键构建前给出轻提示，减少“已知无变化”场景下的等待焦虑。
    """
    try:
        data = request.get_json() or {}
        project_id = str(data.get("project_id") or "").strip()
        sample_ids = data.get("sample_ids") or data.get("announcement_ids") or []
        if not project_id:
            return jsonify({
                "success": False,
                "status": 400,
                "message": "project_id 不能为空",
            }), 400
        if not isinstance(sample_ids, list) or not sample_ids:
            return jsonify({
                "success": False,
                "status": 400,
                "message": "sample_ids 必须是非空数组",
            }), 400

        delta = analyze_master_build_sample_delta(project_id, sample_ids)
        if delta.get("kind") == "noop" and not _mysql_nodes_edges_nonempty(project_id):
            delta = {"kind": "full", "reason": "noop_but_graph_empty"}

        kind = str(delta.get("kind") or "")
        message_map = {
            "noop": "检测到样本无变化，将跳过重抽。可直接查看历史抽取。",
            "incremental_only": "检测到新增样本，将自动按新增样本执行增量构建。",
            "prune_only": "检测到样本有删除，将先清理对应子图并保留其余图谱。",
            "incremental_and_prune": "检测到样本有新增和删除，将执行增量抽取并同步裁剪历史子图。",
            "full": "未找到可复用的历史基线，将执行完整一键构建。",
        }
        return jsonify({
            "success": True,
            "status": 200,
            "message": "预判成功",
            "data": {
                "kind": kind,
                "delta": delta,
                "message": message_map.get(kind, "将执行一键构建。"),
            },
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "status": 500,
            "message": f"预判失败: {str(e)}",
        }), 500


def _mysql_nodes_edges_nonempty(project_id: str) -> bool:
    try:
        if get_nodes_from_database(project_id):
            return True
        return count_mysql_edges_for_project(project_id) > 0
    except Exception:
        return False


def remove_graph_data_for_sample_ids(project_id: str, removed_sample_ids: list) -> Dict[str, Any]:
    """
    从 MySQL / Neo4j 移除指定样本对应的节点及其关联边（边端点命中或边上 sample_id 命中）。
    """
    removed = _normalize_sample_id_set(removed_sample_ids)
    if not removed:
        return {"deleted_nodes": 0, "deleted_edges": 0, "removed_node_ids": []}

    nodes = get_nodes_from_database(project_id)
    delete_ids = []
    for n in nodes:
        props = n.get("properties") if isinstance(n.get("properties"), dict) else {}
        sid = str(props.get("sample_id") or "").strip()
        if sid in removed:
            delete_ids.append(n["id"])
    delete_set = set(delete_ids)
    if not delete_set and not removed:
        return {"deleted_nodes": 0, "deleted_edges": 0, "removed_node_ids": []}

    engine = get_sqlalchemy_engine()
    deleted_edges = 0
    deleted_nodes = 0
    edge_ids_del: List[Any] = []
    try:
        with engine.connect() as conn:
            q_edges = text(
                """
                SELECT id, `from` AS from_, `to`, properties
                FROM edge_table
                WHERE project_id = :pid
                """
            )
            rows = conn.execute(q_edges, {"pid": project_id}).fetchall()
            for row in rows:
                m = row._mapping if hasattr(row, "_mapping") else dict(row)
                eid = m.get("id")
                frm = m.get("from_")
                to = m.get("to")
                props = m.get("properties")
                if isinstance(props, str):
                    try:
                        props = json.loads(props)
                    except json.JSONDecodeError:
                        props = {}
                esid = str((props or {}).get("sample_id") or "").strip()
                if frm in delete_set or to in delete_set or esid in removed:
                    edge_ids_del.append(eid)

            for eid in edge_ids_del:
                conn.execute(
                    text("DELETE FROM edge_table WHERE id = :eid AND project_id = :pid"),
                    {"eid": eid, "pid": project_id},
                )
            deleted_edges = len(edge_ids_del)

            for nid in delete_ids:
                conn.execute(
                    text("DELETE FROM node_table WHERE id = :nid AND project_id = :pid"),
                    {"nid": nid, "pid": project_id},
                )
            deleted_nodes = len(delete_ids)
            conn.commit()
    except Exception as e:
        print(f"[PruneSample] MySQL 清理失败: {e}")
        traceback.print_exc()
    finally:
        engine.dispose()

    neo4j = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        if delete_ids:
            neo4j.execute_query(
                """
                UNWIND $ids AS nid
                MATCH (n:KnowledgeNode {project_id: $pid})
                WHERE n.id = nid
                DETACH DELETE n
                """,
                {"pid": project_id, "ids": list(delete_ids)},
            )
        neo4j.execute_query(
            """
            MATCH ()-[r]-()
            WHERE r.project_id = $pid AND coalesce(toString(r.sample_id), '') IN $removed
            DELETE r
            """,
            {"pid": project_id, "removed": list(removed)},
        )
    except Exception as e:
        print(f"[PruneSample] Neo4j 清理失败: {e}")
        traceback.print_exc()
    finally:
        neo4j.close()

    return {
        "deleted_nodes": deleted_nodes,
        "deleted_edges": deleted_edges,
        "removed_node_ids": delete_ids,
    }


def build_master_snapshot_payload_from_project_db(
    project_id: str,
    sample_ids_full: list,
    *,
    run_id_hint: str = "",
    sample_delta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """从当前库表组装与一键构建完成一致结构的 data 载荷（用于 noop / 仅裁剪样本）。"""
    nodes = get_nodes_from_database(project_id)
    edges = _get_edges_from_database(project_id)
    conflicts = run_conflict_agent(edges, deep_check=False)
    graph = run_graph_agent(nodes, edges, conflicts, project_id)
    rid = run_id_hint or get_last_master_run_id(project_id)
    if not rid:
        rec = get_last_effective_build_record(project_id) or {}
        rid = str(rec.get("run_id") or "").strip()

    samples = fetch_samples_from_mongo(sample_ids_full)
    quality_score = None
    quality_report = None
    try:
        from agents.quality_scorer_agent import score_graph_quality
        from agents.master_build_workflow import _build_quality_report

        quality_score = score_graph_quality(
            nodes=nodes,
            edges=edges,
            conflicts=conflicts,
            samples=samples or [],
        )
        quality_report = _build_quality_report(
            {"nodes": nodes, "edges": edges, "conflicts": conflicts, "samples": samples or []},
            quality_score,
        )
    except Exception as _e:
        print(f"[snapshot payload] 计算累计质量报告失败: {_e}")

    wm = {
        "run_id": rid,
        "quality_score": quality_score,
        "quality_report": quality_report,
        "conflicts": conflicts,
        "conflict_details": conflicts,
        "conflict_count": len(conflicts),
        "sample_delta": sample_delta or {},
    }
    samples = fetch_samples_from_mongo(sample_ids_full)
    return {
        "samples": samples or [],
        "nodes": nodes,
        "edges": edges,
        "conflicts": conflicts,
        "graph": graph,
        "workflow_meta": wm,
        "incremental_impact_before_build": None,
    }


def _master_build_should_snapshot_project_db(build_plan: Optional[Dict[str, Any]]) -> bool:
    plan = build_plan if isinstance(build_plan, dict) else {}
    mode = str(plan.get("mode") or "full").strip().lower()
    persistence_mode = str(plan.get("persistence_mode") or "replace").strip().lower()
    return mode == "incremental" or persistence_mode == "merge"


def _build_master_workflow_meta(
    run_id: str,
    build_plan: Optional[Dict[str, Any]],
    graph_enrichment: Optional[Dict[str, Any]],
    needs_stale_cleanup: bool,
    conflicts: Optional[list] = None,
    sample_delta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    enrichment = graph_enrichment if isinstance(graph_enrichment, dict) else {}
    conflict_rows = list(conflicts or [])
    meta = {
        "run_id": run_id,
        "build_plan": build_plan if isinstance(build_plan, dict) else {},
        "quality_score": enrichment.get("quality_score"),
        "quality_report": enrichment.get("quality_report"),
        "conflicts": conflict_rows,
        "conflict_details": conflict_rows,
        "conflict_count": len(conflict_rows),
        "needs_stale_cleanup": needs_stale_cleanup,
        "stale_cleanup_executed": bool(needs_stale_cleanup),
        "conflict_mitigation_applied": bool(enrichment),
    }
    if sample_delta is not None:
        meta["sample_delta"] = sample_delta
    return meta


def _finalize_master_build_payload(
    project_id: str,
    sample_ids_full: list,
    *,
    run_id_hint: str,
    build_plan: Optional[Dict[str, Any]],
    graph_enrichment: Optional[Dict[str, Any]],
    needs_stale_cleanup: bool,
    incremental_impact_before_build: Optional[Dict[str, Any]] = None,
    samples_override: Optional[list] = None,
    sample_delta: Optional[Dict[str, Any]] = None,
    nodes: Optional[list] = None,
    edges: Optional[list] = None,
    conflicts: Optional[list] = None,
    graph: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    workflow_meta = _build_master_workflow_meta(
        str(run_id_hint or ""),
        build_plan,
        graph_enrichment,
        bool(needs_stale_cleanup),
        conflicts=conflicts,
        sample_delta=sample_delta,
    )

    if _master_build_should_snapshot_project_db(build_plan):
        payload = build_master_snapshot_payload_from_project_db(
            project_id,
            sample_ids_full,
            run_id_hint=str(run_id_hint or ""),
            sample_delta=sample_delta,
        )
        payload_meta = payload.get("workflow_meta") if isinstance(payload.get("workflow_meta"), dict) else {}
        payload["workflow_meta"] = {
            **payload_meta,
            "run_id": workflow_meta["run_id"],
            "build_plan": workflow_meta["build_plan"],
            "quality_score": workflow_meta["quality_score"]
            if workflow_meta["quality_score"] is not None
            else payload_meta.get("quality_score"),
            "quality_report": workflow_meta["quality_report"]
            if workflow_meta["quality_report"] is not None
            else payload_meta.get("quality_report"),
            "needs_stale_cleanup": workflow_meta["needs_stale_cleanup"],
            "stale_cleanup_executed": workflow_meta["stale_cleanup_executed"],
            "conflict_mitigation_applied": workflow_meta["conflict_mitigation_applied"],
        }
        if sample_delta is not None:
            payload["workflow_meta"]["sample_delta"] = sample_delta
        payload["incremental_impact_before_build"] = incremental_impact_before_build
        return payload

    return {
        "samples": list(samples_override or []),
        "nodes": list(nodes or []),
        "edges": list(edges or []),
        "conflicts": list(conflicts or []),
        "graph": dict(graph or {}),
        "workflow_meta": workflow_meta,
        "incremental_impact_before_build": incremental_impact_before_build,
    }


def _load_extraction_snapshot(project_id: str, run_id: str) -> Dict[str, Any]:
    engine = get_sqlalchemy_engine()
    try:
        with engine.connect() as conn:
            q = text(
                """
                SELECT run_id, run_type, title, sample_ids, nodes_snapshot, edges_snapshot, workflow_meta_snapshot
                FROM extraction_history
                WHERE project_id = :project_id AND run_id = :run_id
                """
            )
            row = conn.execute(q, {"project_id": project_id, "run_id": run_id}).fetchone()
        if not row:
            return {}
        sample_ids = []
        if row.sample_ids:
            try:
                sample_ids = json.loads(row.sample_ids) if isinstance(row.sample_ids, str) else row.sample_ids
            except Exception:
                sample_ids = []
        return {
            "run_id": row.run_id,
            "run_type": row.run_type,
            "title": row.title,
            "sample_ids": sample_ids or [],
            "nodes": json.loads(row.nodes_snapshot) if row.nodes_snapshot else [],
            "edges": json.loads(row.edges_snapshot) if row.edges_snapshot else [],
            "workflow_meta": json.loads(row.workflow_meta_snapshot) if getattr(row, 'workflow_meta_snapshot', None) else {},
        }
    except Exception as e:
        print(f"读取抽取快照失败: {e}")
        return {}
    finally:
        engine.dispose()


def _login_name_for_numeric_user_id(uid_str: str) -> str:
    """
    graph_project.creator / 多数权限字段存的是登录名 user_name；
    前端若传 user_data.id（纯数字），需映射到 user_name 才能与 creator 对齐。
    """
    s = (uid_str or "").strip()
    if not s.isdigit():
        return ""
    client = None
    try:
        client = get_client()
        with client.cursor() as cur:
            cur.execute(
                "SELECT user_name FROM user_data WHERE id = %s LIMIT 1",
                (int(s),),
            )
            row = cur.fetchone()
            if row:
                return str(row.get("user_name") or "").strip()
    except Exception:
        pass
    finally:
        if client:
            try:
                client.close()
            except Exception:
                pass
    return ""


@llmGenKG_bp.route('/get_extraction_history_list', methods=['GET'])
def get_extraction_history_list():
    """
    获取项目的抽取历史列表。
    可选 query: user_id / creator — 若传入则仅返回「项目创建者」为该用户的记录（与历史对话列表权限一致）。
    """
    try:
        project_id = request.args.get('project_id')
        if not project_id:
            return jsonify({
                'success': False,
                'message': 'project_id 不能为空',
                'status': 400
            }), 400
        filter_user = (request.args.get('user_id') or request.args.get('creator') or '').strip()
        filter_alt = _login_name_for_numeric_user_id(filter_user)
        hist_params = {
            "project_id": project_id,
            "filter_user": filter_user,
            "filter_alt": filter_alt,
        }

        _ensure_extraction_history_schema()
        engine = get_sqlalchemy_engine()
        with engine.connect() as conn:
            # 优先：联表 graph_project，按项目创建者过滤（老数据 user_id 为空时仍可通过 creator 命中）
            # 注：使用 COLLATE utf8mb4_unicode_ci 解决字符集冲突
            q_join = text("""
                SELECT h.run_id, h.run_type, h.title, h.created_at, h.nodes_count, h.edges_count, h.user_id
                FROM extraction_history h
                INNER JOIN finkg1.graph_project g ON g.id COLLATE utf8mb4_unicode_ci = h.project_id COLLATE utf8mb4_unicode_ci
                WHERE h.project_id = :project_id
                  AND (
                    :filter_user = ''
                    OR TRIM(IFNULL(g.creator, '')) = :filter_user
                    OR TRIM(IFNULL(h.user_id, '')) = :filter_user
                    OR (:filter_alt <> '' AND TRIM(IFNULL(g.creator, '')) = :filter_alt)
                    OR (:filter_alt <> '' AND TRIM(IFNULL(h.user_id, '')) = :filter_alt)
                  )
                ORDER BY h.created_at DESC
                LIMIT 50
            """)
            try:
                rows = conn.execute(
                    q_join,
                    hist_params,
                ).fetchall()
            except Exception as e_join:
                err = str(e_join).lower()
                if "unknown column" in err or "doesn't exist" in err:
                    q_no_col = text("""
                        SELECT h.run_id, h.run_type, h.created_at, h.nodes_count, h.edges_count
                        FROM extraction_history h
                        INNER JOIN finkg1.graph_project g ON g.id = h.project_id
                        WHERE h.project_id = :project_id
                          AND (
                            :filter_user = ''
                            OR TRIM(IFNULL(g.creator, '')) = :filter_user
                            OR (:filter_alt <> '' AND TRIM(IFNULL(g.creator, '')) = :filter_alt)
                          )
                        ORDER BY h.created_at DESC
                        LIMIT 50
                    """)
                    try:
                        rows = conn.execute(
                            q_no_col,
                            hist_params,
                        ).fetchall()
                    except Exception:
                        q_legacy = text("""
                            SELECT run_id, run_type, created_at, nodes_count, edges_count
                            FROM extraction_history
                            WHERE project_id = :project_id
                            ORDER BY created_at DESC
                            LIMIT 50
                        """)
                        rows = conn.execute(q_legacy, {"project_id": project_id}).fetchall()
                else:
                    raise
        engine.dispose()

        items = []
        for r in rows:
            m = r._mapping if hasattr(r, "_mapping") else dict(r)
            ca = m.get("created_at")
            items.append({
                "run_id": m.get("run_id"),
                "run_type": m.get("run_type"),
                "title": m.get("title"),
                "created_at": ca.isoformat() if hasattr(ca, "isoformat") else str(ca or ""),
                "nodes_count": m.get("nodes_count"),
                "edges_count": m.get("edges_count"),
                "user_id": m.get("user_id"),
            })
        return jsonify({
            'success': True,
            'message': '获取成功',
            'status': 200,
            'data': {'items': items, 'project_id': project_id}
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'获取历史列表失败: {str(e)}',
            'status': 500
        }), 500


@llmGenKG_bp.route('/checkout_extraction_history', methods=['POST'])
def checkout_extraction_history_api():
    """将指定的图谱快照检出（覆盖）到当前工作区（node_table/edge_table），以便继续抽取"""
    try:
        data = request.get_json() or {}
        project_id = str(data.get('project_id') or '').strip()
        run_id = str(data.get('run_id') or '').strip()

        if not project_id:
            return jsonify({'success': False, 'message': 'project_id 不能为空', 'status': 400}), 400

        nodes = []
        edges = []
        if run_id:
            snap = _load_extraction_snapshot(project_id, run_id)
            if not snap:
                return jsonify({'success': False, 'message': '源历史任务不存在', 'status': 404}), 404
            nodes = snap.get('nodes') or []
            edges = snap.get('edges') or []

        # 覆写到当前主库(node_table/edge_table)
        save_nodes_to_database(nodes, project_id)
        
        # 覆写边并同步到 Neo4j
        save_edges_to_databases(edges, project_id, "general", replace_graph=True)

        return jsonify({
            'success': True,
            'message': '工作区已切换',
            'status': 200
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'切换失败: {str(e)}', 'status': 500}), 500


@llmGenKG_bp.route('/rename_extraction_history', methods=['POST'])
def rename_extraction_history_api():
    """重命名一条抽取历史记录。"""
    try:
        data = request.get_json() or {}
        project_id = str(data.get('project_id') or '').strip()
        run_id = str(data.get('run_id') or '').strip()
        title = str(data.get('title') or '').strip()
        uid = str(data.get('user_id') or data.get('creator') or data.get('username') or '').strip()
        uid_alt = _login_name_for_numeric_user_id(uid)
        if not project_id or not run_id or not title:
            return jsonify({
                'success': False,
                'message': 'project_id、run_id、title 不能为空',
                'status': 400,
            }), 400

        _ensure_extraction_history_schema()
        engine = get_sqlalchemy_engine()
        with engine.connect() as conn:
            q = text(
                """
                UPDATE extraction_history h
                INNER JOIN finkg1.graph_project g ON g.id COLLATE utf8mb4_unicode_ci = h.project_id COLLATE utf8mb4_unicode_ci
                SET h.title = :title, h.user_id = CASE WHEN :uid = '' THEN h.user_id ELSE :uid END
                WHERE h.project_id = :project_id AND h.run_id = :run_id
                  AND (
                    :uid = ''
                    OR TRIM(IFNULL(g.creator,'')) = :uid
                    OR TRIM(IFNULL(h.user_id,'')) = :uid
                    OR (:uid_alt <> '' AND TRIM(IFNULL(g.creator,'')) = :uid_alt)
                    OR (:uid_alt <> '' AND TRIM(IFNULL(h.user_id,'')) = :uid_alt)
                  )
                """
            )
            try:
                r = conn.execute(q, {
                    'title': title,
                    'uid': uid,
                    'uid_alt': uid_alt,
                    'project_id': project_id,
                    'run_id': run_id,
                })
                affected = r.rowcount or 0
            except Exception as e_upd:
                err_str = str(e_upd).lower()
                print("Rename via JOIN failed:", err_str)
                q2 = text(
                    """
                    UPDATE extraction_history SET title = :title
                    WHERE project_id = :project_id AND run_id = :run_id
                    """
                )
                r2 = conn.execute(q2, {
                    'title': title,
                    'project_id': project_id,
                    'run_id': run_id,
                })
                affected = r2.rowcount or 0
            conn.commit()
        engine.dispose()
        if affected <= 0:
            return jsonify({
                'success': False,
                'message': '未更新任何记录（无权限或记录不存在）',
                'status': 404,
            }), 404
        return jsonify({
            'success': True,
            'message': '重命名成功',
            'status': 200,
            'data': {'run_id': run_id, 'title': title},
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'重命名失败: {str(e)}',
            'status': 500,
        }), 500


@llmGenKG_bp.route('/create_extraction_history_snapshot', methods=['POST'])
def create_extraction_history_snapshot_api():
    """基于当前项目图谱或指定历史快照，新建一个命名的抽取任务快照。"""
    try:
        data = request.get_json() or {}
        project_id = str(data.get('project_id') or '').strip()
        title = str(data.get('title') or '').strip()
        source_run_id = str(data.get('source_run_id') or '').strip()
        is_empty = bool(data.get('is_empty'))
        uid = str(data.get('user_id') or data.get('creator') or data.get('username') or '').strip()

        if not project_id or not title:
            return jsonify({
                'success': False,
                'message': 'project_id 与 title 不能为空',
                'status': 400,
            }), 400

        if is_empty:
            sample_ids = _get_project_sample_ids(project_id)
            nodes = []
            edges = []
            workflow_meta = {}
        elif source_run_id:
            snap = _load_extraction_snapshot(project_id, source_run_id)
            if not snap:
                return jsonify({
                    'success': False,
                    'message': '源历史任务不存在',
                    'status': 404,
                }), 404
            sample_ids = snap.get('sample_ids') or []
            nodes = snap.get('nodes') or []
            edges = snap.get('edges') or []
            workflow_meta = snap.get('workflow_meta') or {}
        else:
            sample_ids = _get_project_sample_ids(project_id)
            nodes = get_nodes_from_database(project_id)
            edges = _get_edges_from_database(project_id)
            workflow_meta = {}

        if not is_empty and not nodes and not edges:
            return jsonify({
                'success': False,
                'message': '当前项目还没有可保存的抽取结果，请先完成一次抽取或构建',
                'status': 400,
            }), 400

        run_id = save_extraction_history(
            project_id,
            'snapshot',
            sample_ids,
            nodes,
            edges,
            title=title,
            user_id=uid or None,
            workflow_meta=workflow_meta,
        )
        return jsonify({
            'success': True,
            'message': '抽取任务已创建',
            'status': 200,
            'data': {
                'run_id': run_id,
                'project_id': project_id,
                'title': title,
                'nodes_count': len(nodes),
                'edges_count': len(edges),
            },
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'创建抽取任务失败: {str(e)}',
            'status': 500,
        }), 500


@llmGenKG_bp.route('/delete_extraction_history', methods=['POST'])
def delete_extraction_history_api():
    """删除一条抽取历史快照（需与项目创建者或记录 user_id 一致）。"""
    try:
        data = request.get_json() or {}
        project_id = data.get("project_id")
        run_id = data.get("run_id")
        uid = str(data.get("user_id") or data.get("creator") or data.get("username") or "").strip()
        uid_alt = _login_name_for_numeric_user_id(uid)
        if not project_id or not run_id:
            return jsonify({
                "success": False,
                "message": "project_id 与 run_id 不能为空",
                "status": 400,
            }), 400
        engine = get_sqlalchemy_engine()
        with engine.connect() as conn:
            q = text("""
                DELETE h FROM extraction_history h
                INNER JOIN finkg1.graph_project g ON g.id COLLATE utf8mb4_unicode_ci = h.project_id COLLATE utf8mb4_unicode_ci
                WHERE h.project_id = :project_id AND h.run_id = :run_id
                  AND (
                    :uid = ''
                    OR TRIM(IFNULL(g.creator,'')) = :uid
                    OR TRIM(IFNULL(h.user_id,'')) = :uid
                    OR (:uid_alt <> '' AND TRIM(IFNULL(g.creator,'')) = :uid_alt)
                    OR (:uid_alt <> '' AND TRIM(IFNULL(h.user_id,'')) = :uid_alt)
                  )
            """)
            try:
                r = conn.execute(q, {
                    "project_id": project_id,
                    "run_id": run_id,
                    "uid": uid,
                    "uid_alt": uid_alt,
                })
                affected = r.rowcount or 0
            except Exception as e_del:
                err_str = str(e_del).lower()
                print("Delete via JOIN failed:", err_str)
                # Fallback to simple DELETE if permissions/JOIN aren't working out due to strict mode or missing columns
                q2 = text("""
                    DELETE FROM extraction_history
                    WHERE project_id = :project_id AND run_id = :run_id
                """)
                r2 = conn.execute(q2, {"project_id": project_id, "run_id": run_id})
                affected = r2.rowcount or 0
            conn.commit()
        engine.dispose()
        if affected <= 0:
            return jsonify({
                "success": False,
                "message": "未删除任何记录（无权限或记录不存在）",
                "status": 404,
            }), 404
        return jsonify({"success": True, "message": "已删除", "status": 200})
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"删除失败: {str(e)}",
            "status": 500,
        }), 500


@llmGenKG_bp.route('/get_neo4j_graph_by_run', methods=['GET'])
def get_neo4j_graph_by_run():
    """按 run_id 获取历史快照的图谱数据"""
    try:
        project_id = request.args.get('project_id')
        run_id = request.args.get('run_id')
        print(f"[get_neo4j_graph_by_run] request project_id={project_id} run_id={run_id}")
        if not project_id or not run_id:
            return jsonify({
                'success': False,
                'message': 'project_id 和 run_id 不能为空',
                'status': 400
            }), 400
        engine = get_sqlalchemy_engine()
        with engine.connect() as conn:
            q = text("""
                SELECT nodes_snapshot, edges_snapshot
                FROM extraction_history
                WHERE project_id = :project_id AND run_id = :run_id
            """)
            row = conn.execute(q, {"project_id": project_id, "run_id": run_id}).fetchone()
        engine.dispose()
        if not row:
            print(f"[get_neo4j_graph_by_run] miss project_id={project_id} run_id={run_id}")
            return jsonify({
                'success': False,
                'message': '未找到该历史记录',
                'status': 404
            }), 404
        nodes = json.loads(row.nodes_snapshot) if row.nodes_snapshot else []
        edges_raw = json.loads(row.edges_snapshot) if row.edges_snapshot else []
        edges = [_normalize_edge_for_snapshot(e) for e in (edges_raw or []) if isinstance(e, dict)]
        print(
            f"[get_neo4j_graph_by_run] hit project_id={project_id} run_id={run_id} "
            f"nodes={len(nodes)} edges={len(edges)} raw_edges={len(edges_raw or [])}"
        )
        return jsonify({
            'success': True,
            'message': '获取成功',
            'status': 200,
            'data': {
                'nodes': nodes,
                'edges': edges,
                'project_id': project_id,
                'run_id': run_id
            }
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'获取历史图谱失败: {str(e)}',
            'status': 500
        }), 500


@llmGenKG_bp.route('/attribute_completion', methods=['POST'])
def attribute_completion():
    """
    图谱节点/关系属性补全 Agent。
    根据节点或关系的 value/type 等信息，结合 LLM 推理（可扩展为外部知识库查询）
    返回补全后的属性建议，或直接更新到数据库。
    """
    try:
        data = request.get_json() or {}
        project_id = data.get('project_id')
        target_type = data.get('target_type')  # 'node' | 'edge'
        target_id = data.get('target_id')  # node_id 或 edge_id
        apply_update = data.get('apply_update', False)  # 是否直接写入数据库

        if not project_id or not target_type or not target_id:
            return jsonify({
                'success': False,
                'message': 'project_id、target_type、target_id 不能为空',
                'status': 400
            }), 400

        if target_type not in ('node', 'edge'):
            return jsonify({
                'success': False,
                'message': 'target_type 必须是 node 或 edge',
                'status': 400
            }), 400

        # 获取当前节点/边数据
        if target_type == 'node':
            nodes = get_nodes_from_database(project_id)
            target = next((n for n in nodes if n['id'] == target_id), None)
            if not target:
                return jsonify({
                    'success': False,
                    'message': f'未找到节点 {target_id}',
                    'status': 404
                }), 404
            name = target.get('value', target.get('key', ''))
            type_label = target.get('type', '实体')
        else:
            engine = get_sqlalchemy_engine()
            with engine.connect() as conn:
                q = text("""
                    SELECT id, type, `from`, `to`, value, eventRel, properties 
                    FROM edge_table 
                    WHERE project_id = :project_id AND id = :edge_id
                """)
                row = conn.execute(q, {"project_id": project_id, "edge_id": target_id}).fetchone()
            engine.dispose()
            if not row:
                return jsonify({
                    'success': False,
                    'message': f'未找到关系 {target_id}',
                    'status': 404
                }), 404
            target = {
                "id": row.id,
                "from": row.from_,
                "to": row.to,
                "value": row.value,
                "eventRel": row.eventRel,
                "properties": json.loads(row.properties) if isinstance(row.properties, str) else row.properties
            }
            name = target.get('value', target.get('eventRel', ''))
            type_label = '关系'

        # 使用 LLM 生成属性补全建议（可替换为实际外部知识库查询）
        client = openai.OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
        prompt = f"""你是一个知识图谱属性补全助手。根据以下{type_label}信息，补充合理的扩展属性（JSON 格式）。
要求：
1. 仅返回一个 JSON 对象，不要其它文字
2. 可包含：description（简短描述）、alias（别名列表）、category（分类）、source（信息来源，可写"LLM补全"）
3. 若为金融/证券相关，可补充 industry、related_concepts 等
4. 属性名用英文，值为字符串或数组

{type_label}名称: {name}
当前已有属性: {json.dumps(target.get('properties', {}), ensure_ascii=False)}

请返回补全后的完整 properties JSON（合并已有属性与新增属性）："""

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1024
        )
        content = (response.choices[0].message.content or "{}").strip()
        # 尝试解析 JSON
        for prefix in ('```json', '```'):
            if prefix in content:
                try:
                    content = content.split(prefix)[1].split('```')[0].strip()
                    break
                except IndexError:
                    pass
        try:
            completed_props = json.loads(content)
        except json.JSONDecodeError:
            completed_props = {"description": content[:200] if content else "", "source": "LLM补全"}

        if apply_update:
            if target_type == 'node':
                engine = get_sqlalchemy_engine()
                with engine.connect() as conn:
                    upd = text("""
                        UPDATE node_table 
                        SET properties = :properties 
                        WHERE project_id = :project_id AND id = :node_id
                    """)
                    conn.execute(upd, {
                        "properties": json.dumps(completed_props),
                        "project_id": project_id,
                        "node_id": target_id
                    })
                    conn.commit()
                engine.dispose()
                # 同步 Neo4j
                neo4j = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
                try:
                    q = """
                        MATCH (n:KnowledgeNode {id: $id})
                        WHERE n.project_id = $project_id
                        SET n += $properties
                    """
                    neo4j.execute_query(q, {
                        "id": target_id,
                        "project_id": project_id,
                        "properties": completed_props
                    })
                finally:
                    neo4j.close()
            else:
                engine = get_sqlalchemy_engine()
                with engine.connect() as conn:
                    upd = text("""
                        UPDATE edge_table 
                        SET properties = :properties 
                        WHERE project_id = :project_id AND id = :edge_id
                    """)
                    conn.execute(upd, {
                        "properties": json.dumps(completed_props),
                        "project_id": project_id,
                        "edge_id": target_id
                    })
                    conn.commit()
                engine.dispose()
                # 同步 Neo4j
                r = target
                neo4j = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
                try:
                    q = """
                        MATCH (a:KnowledgeNode {id: $from_id})-[r]->(b:KnowledgeNode {id: $to_id})
                        WHERE r.project_id = $project_id
                        SET r += $properties
                    """
                    neo4j.execute_query(q, {
                        "from_id": r["from"],
                        "to_id": r["to"],
                        "project_id": project_id,
                        "properties": completed_props
                    })
                finally:
                    neo4j.close()

        return jsonify({
            'success': True,
            'message': '属性补全成功' if apply_update else '属性补全建议已生成',
            'status': 200,
            'data': {
                'target_type': target_type,
                'target_id': target_id,
                'completed_properties': completed_props,
                'applied': apply_update
            }
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'属性补全失败: {str(e)}',
            'status': 500
        }), 500


@llmGenKG_bp.route('/check_extraction_status', methods=['POST'])
def check_extraction_status():
    try:
        # 从请求体中获取project_id
        project_id = request.json.get('project_id')  # 修改点
        print("检查阶段的project_id：", project_id)
        if not project_id:
            return jsonify({'success': False, 'message': '项目ID不能为空'}), 400

        # 检查节点状态
        engine = get_sqlalchemy_engine()
        with engine.connect() as conn:
            # 检查节点
            node_query = text("SELECT COUNT(*) FROM node_table WHERE project_id = :project_id")
            node_count = conn.execute(node_query, {"project_id": project_id}).scalar()

            # 检查关系
            edge_query = text("SELECT COUNT(*) FROM edge_table WHERE project_id = :project_id")
            edge_count = conn.execute(edge_query, {"project_id": project_id}).scalar()

            print("node_count:", node_count)
            print("edge_count:", edge_count)

        return jsonify({
            'success': True,
            'has_nodes': node_count > 0,
            'has_edges': edge_count > 0,
            "status": 200,
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'检查状态失败: {str(e)}'
        }), 500