# # -*- coding: utf-8 -*-
# """
# 从外部 API 拉取 message 列表并同步到本地 event_data 表，支持每日定时更新。
# """
#
# import hashlib
# import json
# import requests
# from database import get_client
#
# EVENT_API_URL = "http://192.168.3.168:8000/api/message/list_all"
#
# # list_all 接口要求的请求体（空条件表示拉取全部）
# LIST_ALL_PAYLOAD = {
#     "stock_code": "",
#     "keyword": "",
#     "start_time": "",
#     "end_time": "",
#     "event_type": "",
#     "sort_field": "event_time",
#     "sort_order": -1,
# }
#
#
# def create_event_data_table(conn):
#     """创建 event_data 表（若不存在）。"""
#     sql = """
#     CREATE TABLE IF NOT EXISTS event_data (
#         id BIGINT AUTO_INCREMENT PRIMARY KEY,
#         item_id VARCHAR(255) NOT NULL COMMENT '来自接口的 id 或数据哈希，用于去重',
#         data JSON NOT NULL COMMENT '单条数据的完整 JSON',
#         created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
#         updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
#         UNIQUE KEY uk_item_id (item_id)
#     ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='从 list_all 接口同步的消息/事件数据';
#     """
#     with conn.cursor() as cursor:
#         cursor.execute(sql)
#     conn.commit()
#
#
# def _get_item_id(item):
#     """从单条数据中取唯一标识，若无则用内容哈希。"""
#     for key in ("id", "_id", "message_id", "event_id"):
#         if key in item and item[key] is not None:
#             return str(item[key])
#     raw = json.dumps(item, sort_keys=True, ensure_ascii=False)
#     return hashlib.md5(raw.encode("utf-8")).hexdigest()
#
#
# def get_items_from_response(response_data):
#     """
#     将接口返回的 JSON 规范化为「条目列表」。
#     支持：{"data": [...]}、{"list": [...]}、{"results": [...]} 或直接 [...]。
#     """
#     if response_data is None:
#         return []
#     if isinstance(response_data, list):
#         return response_data
#     if not isinstance(response_data, dict):
#         return [response_data]
#     for key in ("data", "list", "results", "items", "messages"):
#         if key in response_data and isinstance(response_data[key], list):
#             return response_data[key]
#     # 整个响应当作一条记录
#     return [response_data]
#
#
# def fetch_event_data():
#     """从配置的 URL 拉取 JSON（POST，带 list_all 要求的 body）。"""
#     try:
#         r = requests.post(
#             EVENT_API_URL,
#             json=LIST_ALL_PAYLOAD,
#             headers={"Content-Type": "application/json"},
#             timeout=30,
#         )
#         r.raise_for_status()
#         data = r.json()
#         # 若接口返回业务错误，不把错误内容当数据写入
#         if isinstance(data, dict) and (data.get("code") != 0 or data.get("msg") == "fail"):
#             raise RuntimeError(f"list_all 返回错误: {data.get('data', data)}")
#         return data
#     except Exception as e:
#         raise RuntimeError(f"请求 {EVENT_API_URL} 失败: {e}") from e
#
#
# def sync_event_data():
#     """
#     拉取接口数据并写入/更新 event_data 表。
#     有 item_id 则 upsert，否则按 item_id 插入。
#     """
#     raw = fetch_event_data()
#     items = get_items_from_response(raw)
#     if not items:
#         return 0
#
#     conn = get_client()
#     try:
#         create_event_data_table(conn)
#         # 使用 INSERT ... ON DUPLICATE KEY UPDATE 做全量覆盖更新
#         sql = """
#         INSERT INTO event_data (item_id, data, created_at, updated_at)
#         VALUES (%s, %s, NOW(), NOW())
#         ON DUPLICATE KEY UPDATE
#             data = VALUES(data),
#             updated_at = NOW()
#         """
#         with conn.cursor() as cursor:
#             for item in items:
#                 if not isinstance(item, dict):
#                     item = {"value": item}
#                 item_id = _get_item_id(item)
#                 data_str = json.dumps(item, ensure_ascii=False)
#                 cursor.execute(sql, (item_id, data_str))
#         conn.commit()
#         return len(items)
#     finally:
#         conn.close()
#
#
# def run_sync():
#     """创建表并执行一次同步，供定时任务或手动调用。"""
#     sync_event_data()


# backend/event_data_sync_mongo.py
# backend/event_data_sync.py
# -*- coding: utf-8 -*-
"""
从外部 API 拉取 message 列表并同步到本地 event_data 表，支持每日定时更新。
同时支持 MongoDB 同步。
"""

import hashlib
import json
import requests
import asyncio
import aiohttp
import time
import logging
from database import get_client
from pymongo import MongoClient, UpdateOne
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

EVENT_API_URL = "http://8.130.110.113:5003/api/message/list_all"

# list_all 接口要求的请求体（空条件表示拉取全部）
LIST_ALL_PAYLOAD = {
    "stock_code": "",
    "keyword": "",
    "start_time": "",
    "end_time": "",
    "event_type": "",
    "sort_field": "event_time",
    "sort_order": -1,
}

# ========== MongoDB 同步参数 ==========
PAGE_SIZE = 500  # 每页大小
MAX_CONCURRENT = 30  # 最大并发数
BATCH_SIZE = 1000  # 每批写入 MongoDB 的数据量
REQUEST_TIMEOUT = 60  # 请求超时
# =====================================

# MongoDB 连接
MONGO_URI = 'mongodb://localhost:27017/'
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client['finkg1']
mongo_collection = mongo_db['event_data']
mongo_meta_collection = mongo_db['event_data_meta']

# 创建 MongoDB 索引
mongo_collection.create_index('item_id', unique=True)
mongo_collection.create_index('data._id')
mongo_collection.create_index('data.event_time')
logger.info("MongoDB 索引创建完成")


# ========== MySQL 同步函数（原有的） ==========
def create_event_data_table(conn):
    """创建 event_data 表（若不存在）。"""
    sql = """
    CREATE TABLE IF NOT EXISTS event_data (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        item_id VARCHAR(255) NOT NULL COMMENT '来自接口的 id 或数据哈希，用于去重',
        data JSON NOT NULL COMMENT '单条数据的完整 JSON',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uk_item_id (item_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='从 list_all 接口同步的消息/事件数据';
    """
    with conn.cursor() as cursor:
        cursor.execute(sql)
    conn.commit()


def _get_item_id(item):
    """从单条数据中取唯一标识，若无则用内容哈希。"""
    for key in ("id", "_id", "message_id", "event_id"):
        if key in item and item[key] is not None:
            return str(item[key])
    raw = json.dumps(item, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def get_items_from_response(response_data):
    """
    将接口返回的 JSON 规范化为「条目列表」。
    支持：{"data": [...]}、{"list": [...]}、{"results": [...]} 或直接 [...]。
    """
    if response_data is None:
        return []
    if isinstance(response_data, list):
        return response_data
    if not isinstance(response_data, dict):
        return [response_data]
    for key in ("data", "list", "results", "items", "messages"):
        if key in response_data and isinstance(response_data[key], list):
            return response_data[key]
    # 整个响应当作一条记录
    return [response_data]


def fetch_event_data():
    """从配置的 URL 拉取 JSON（POST，带 list_all 要求的 body）。"""
    try:
        r = requests.post(
            EVENT_API_URL,
            json=LIST_ALL_PAYLOAD,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        # 若接口返回业务错误，不把错误内容当数据写入
        if isinstance(data, dict) and (data.get("code") != 0 or data.get("msg") == "fail"):
            raise RuntimeError(f"list_all 返回错误: {data.get('data', data)}")
        return data
    except Exception as e:
        raise RuntimeError(f"请求 {EVENT_API_URL} 失败: {e}") from e


def sync_event_data():
    """
    拉取接口数据并写入/更新 MySQL event_data 表。
    """
    raw = fetch_event_data()
    items = get_items_from_response(raw)
    if not items:
        return 0

    conn = get_client()
    try:
        create_event_data_table(conn)
        # 使用 INSERT ... ON DUPLICATE KEY UPDATE 做全量覆盖更新
        sql = """
        INSERT INTO event_data (item_id, data, created_at, updated_at)
        VALUES (%s, %s, NOW(), NOW())
        ON DUPLICATE KEY UPDATE
            data = VALUES(data),
            updated_at = NOW()
        """
        with conn.cursor() as cursor:
            for item in items:
                if not isinstance(item, dict):
                    item = {"value": item}
                item_id = _get_item_id(item)
                data_str = json.dumps(item, ensure_ascii=False)
                cursor.execute(sql, (item_id, data_str))
        conn.commit()
        return len(items)
    finally:
        conn.close()


def run_sync():
    """MySQL 同步入口，供定时任务调用"""
    return sync_event_data()


# ========== MongoDB 同步函数（修正版，支持按时间增量） ==========
def _parse_event_time(value):
    """
    尝试把 event_time 字符串解析为 datetime，用于比较大小。
    解析失败则返回 None。
    """
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    s = str(value).strip()
    if not s:
        return None
    # 常见时间格式
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
        try:
            # 避免带毫秒时解析失败，先截断到秒
            return datetime.strptime(s[:19], fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _get_last_synced_event_time():
    """
    从 MongoDB 中读取上次同步到的最大 event_time。
    优先读 meta 表，没有则从 event_data 中扫描一条最大值。
    """
    doc = mongo_meta_collection.find_one({"_id": "event_data_meta"})
    if doc and doc.get("last_event_time"):
        return doc["last_event_time"]

    # 兜底：从已有数据里按 event_time 排序取最大一条
    latest = mongo_collection.find(
        {"data.event_time": {"$exists": True}}
    ).sort("data.event_time", -1).limit(1)
    latest_list = list(latest)
    if latest_list:
        return latest_list[0]["data"].get("event_time")
    return None


def _set_last_synced_event_time(event_time):
    """
    把本次同步到的最大 event_time 记录到 meta 表。
    """
    if not event_time:
        return
    mongo_meta_collection.update_one(
        {"_id": "event_data_meta"},
        {"$set": {"last_event_time": event_time, "updated_at": time.time()}},
        upsert=True,
    )


async def fetch_page_async(session, page, semaphore, start_time=None):
    """异步获取单页数据 - 支持按 start_time 进行增量拉取"""
    payload = LIST_ALL_PAYLOAD.copy()
    payload["page"] = page
    payload["size"] = PAGE_SIZE
    # 若提供了 start_time，则只拉取该时间之后的增量
    if start_time:
        payload["start_time"] = start_time

    async with semaphore:
        try:
            async with session.post(
                    EVENT_API_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=REQUEST_TIMEOUT
            ) as response:
                if response.status != 200:
                    logger.warning(f"第 {page} 页 HTTP {response.status}")
                    return [], None, None

                data = await response.json()

                # 检查接口返回的业务状态
                if data.get("code") != 0:
                    logger.error(f"第 {page} 页 接口返回错误: {data.get('msg')}")
                    return [], None, None

                # 从 data.data.messages 中提取消息列表
                messages = []
                total_pages = None
                total_count = None

                if "data" in data and isinstance(data["data"], dict):
                    messages = data["data"].get("messages", [])
                    pagination = data["data"].get("pagination", {})
                    total_pages = pagination.get("pages")
                    total_count = pagination.get("total")

                    logger.info(f"第 {page} 页: 获取到 {len(messages)} 条消息")
                    if total_pages:
                        logger.info(f"第 {page} 页 分页信息: 总页数={total_pages}, 总条数={total_count}")
                else:
                    logger.warning(f"第 {page} 页 返回数据格式异常: {data}")

                return messages, total_pages, total_count

        except Exception as e:
            logger.warning(f"第 {page} 页请求失败: {e}")
            return [], None, None


async def fetch_all_pages_async(start_time=None):
    """并发获取所有页面 - 修正版，支持从给定 start_time 开始增量拉取"""
    async with aiohttp.ClientSession() as session:
        # 获取第一页，确定总页数
        logger.info("正在获取第一页...")
        semaphore = asyncio.Semaphore(1)
        first_page_items, total_pages, total_count = await fetch_page_async(
            session, 1, semaphore, start_time
        )

        if not first_page_items:
            logger.warning("第一页无数据")
            return []

        all_items = first_page_items
        logger.info(f"第一页获取完成: {len(all_items)} 条消息")

        if total_pages:
            logger.info(f"总页数: {total_pages}")
        if total_count:
            logger.info(f"总数据量: {total_count}")

        # 如果没有总页数信息，需要估算
        if not total_pages:
            # 如果第一页数据少于每页大小，说明只有一页
            if len(first_page_items) < PAGE_SIZE:
                logger.info("只有一页数据")
                return all_items
            else:
                # 估算总页数（保守估计）
                estimated_pages = 200
                logger.info(f"无法获取总页数，按估算值 {estimated_pages} 页处理")
                total_pages = estimated_pages

        # 如果只有一页，直接返回
        if total_pages <= 1:
            return all_items

        # 并发获取剩余页面
        logger.info(f"开始并发获取剩余 {total_pages - 1} 页数据...")

        semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        tasks = []
        for page in range(2, total_pages + 1):
            tasks.append(fetch_page_async(session, page, semaphore, start_time))

        # 分批处理结果，避免内存过大
        batch_size = 50
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch)

            for items, _, _ in batch_results:
                if items:
                    all_items.extend(items)

            logger.info(f"进度: {min(i + batch_size, len(tasks))}/{total_pages - 1} 页, 累计 {len(all_items)} 条消息")

        return all_items


def batch_write_to_mongo(items):
    """批量写入 MongoDB。返回 (写入条数, 本次触及的 item_id 列表)。"""
    if not items:
        logger.info("没有数据需要写入")
        return 0, []

    total = len(items)
    logger.info(f"开始写入 MongoDB，共 {total} 条")

    operations = []
    written = 0
    start_time = time.time()
    touched_ids: list = []

    for idx, item in enumerate(items):
        # 使用 _id 作为唯一标识
        item_id = item.get('_id') if item.get('_id') else _get_item_id(item)
        touched_ids.append(str(item_id))

        operations.append(
            UpdateOne(
                {'item_id': item_id},
                {'$set': {
                    'item_id': item_id,
                    'data': item,
                    'synced_at': time.time()
                }},
                upsert=True
            )
        )

        # 批量执行
        if len(operations) >= BATCH_SIZE:
            try:
                result = mongo_collection.bulk_write(operations, ordered=False)
                written += len(operations)
                elapsed = time.time() - start_time
                rate = written / elapsed if elapsed > 0 else 0
                logger.info(f"写入进度: {written}/{total} ({written / total * 100:.1f}%) - {rate:.0f} 条/秒")
                operations = []
            except Exception as e:
                logger.error(f"批量写入失败: {e}")
                operations = []

    # 写入剩余数据
    if operations:
        try:
            result = mongo_collection.bulk_write(operations, ordered=False)
            written += len(operations)
            logger.info(f"最后一批写入完成: {len(operations)} 条")
        except Exception as e:
            logger.error(f"最后一批写入失败: {e}")

    total_time = time.time() - start_time
    avg_rate = written / total_time if total_time > 0 else 0
    logger.info(f"MongoDB 写入完成: {written} 条, 耗时 {total_time:.1f}秒, 平均 {avg_rate:.0f} 条/秒")
    return written, touched_ids


def sync_to_mongo():
    """
    MongoDB 增量同步函数。

    逻辑：
    - 第一次运行：因为没有 last_event_time，会全量同步一次；
    - 后续运行：从上次记录的最大 event_time 开始增量拉取；
    - 如果外部接口按时间是“>=”语义，则可能返回一小部分已存在数据，
      但由于我们使用 item_id 唯一索引 + upsert，不会产生重复，只是更新。
    """
    start_ts = time.time()
    logger.info("=" * 60)
    logger.info("开始增量数据同步到 MongoDB")
    logger.info(f"MongoDB URI: {MONGO_URI}")
    logger.info(f"目标数据库: finkg1.event_data")

    # 读取上次同步到的最大 event_time
    last_event_time = _get_last_synced_event_time()
    if last_event_time:
        logger.info(f"上次同步的最大 event_time: {last_event_time}")
    else:
        logger.info("未找到历史同步记录，本次将执行全量同步")

    try:
        # 异步获取所有数据
        logger.info("正在获取 list_all 接口数据...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            all_items = loop.run_until_complete(fetch_all_pages_async(start_time=last_event_time))
        finally:
            loop.close()

        if not all_items:
            logger.warning("未获取到任何数据（可能没有新增记录）")
            return 0

        fetch_time = time.time() - start_ts
        logger.info(f"数据获取完成: {len(all_items)} 条，耗时 {fetch_time:.1f}秒")

        # 计算本批次的最大 event_time，并记录到 meta
        max_event_dt = None
        max_event_str = None
        for item in all_items:
            et = item.get("event_time")
            dt = _parse_event_time(et)
            if not dt:
                continue
            if (max_event_dt is None) or (dt > max_event_dt):
                max_event_dt = dt
                max_event_str = et

        if max_event_str:
            logger.info(f"本次同步批次最大 event_time: {max_event_str}")
        else:
            logger.info("本次批次中未找到有效的 event_time 字段，将不会更新增量游标")

        # 写入 MongoDB
        written, touched_ids = batch_write_to_mongo(all_items)

        # 仅在写入成功且存在新的最大 event_time 时更新增量游标
        if written > 0 and max_event_str:
            _set_last_synced_event_time(max_event_str)

        # 图谱影响 Agent：标记「已选样本被本轮增量触及」的项目
        if written > 0 and touched_ids:
            try:
                from agents.incremental_kg_impact import run_incremental_kg_impact_scan

                aff = run_incremental_kg_impact_scan(touched_ids)
                if aff:
                    logger.info(
                        "[IncrementalKG] 以下项目的图谱可能受操作库增量影响，已标记 pending: %s",
                        aff,
                    )
                    try:
                        import os as _os

                        if _os.environ.get("KG_AUTO_INCREMENTAL_SYNC", "").strip().lower() in (
                            "1",
                            "true",
                            "yes",
                        ):
                            from routes.llmGenKG_api import run_incremental_graph_for_projects

                            kg_ret = run_incremental_graph_for_projects(aff)
                            logger.info("[IncrementalKG] 自动增量合并构建结果: %s", kg_ret)
                    except Exception as auto_e:
                        logger.warning(
                            "[IncrementalKG] 自动增量构建未执行或失败: %s",
                            auto_e,
                            exc_info=True,
                        )
            except Exception as kg_e:
                logger.warning("[IncrementalKG] 影响扫描未执行: %s", kg_e, exc_info=True)

        total_time = time.time() - start_ts
        logger.info(f"同步完成！本次写入 {written} 条到 MongoDB")
        logger.info(f"总耗时: {total_time:.1f}秒")
        logger.info("=" * 60)

        return written

    except Exception as e:
        logger.error(f"同步失败: {e}")
        import traceback
        traceback.print_exc()
        raise