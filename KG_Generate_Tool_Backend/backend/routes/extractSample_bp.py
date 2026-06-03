import json
import re
import traceback
from datetime import datetime
from flask import Blueprint, jsonify, request
from database import get_client  # 确保这是MySQL连接
from pymongo import MongoClient
import logging

extractSample_bp = Blueprint('extractSample', __name__)


def get_data_from_db(project_id=None):
    """从数据库获取项目数据"""
    try:
        client = get_client()
        cursor = client.cursor()

        query = """
        SELECT 
            title,
            text AS content,
            summary,
            publish_time,
            user AS operator,
            event_type,
            project_id,
            create_time AS insert_time
        FROM finkg1.project_data
        WHERE project_id = %s
        ORDER BY create_time DESC
        """
        cursor.execute(query, (project_id,))
        data_list = cursor.fetchall()

        return {
            "status": 200,
            "project_id": project_id,
            "data": data_list,
            "count": len(data_list)
        }

    except Exception as e:
        print(f'Database error: {str(e)}')
        traceback.print_exc()
        return {
            "status": 500,
            "error": str(e),
            "message": "获取数据失败"
        }
    finally:
        cursor.close()


@extractSample_bp.route('/extractSample/getAllTextData', methods=['POST'])
def fetch_data():
    try:
        params = request.get_json()
        project_id = params.get('project_id')
        page = params.get('page', 1)
        page_size = params.get('page_size', 10)

        if not project_id:
            return jsonify({"status": 400, "message": "project_id是必填字段"})

        client = get_client()
        cursor = client.cursor()
        offset = (page - 1) * page_size

        # 查询总条数
        count_query = "SELECT count(*) as total FROM finkg1.project_data WHERE project_id = %s"
        cursor.execute(count_query, (project_id,))
        total = cursor.fetchone()['total']

        # 查询分页数据
        data_query = """
        SELECT 
            title,
            text AS content,
            summary,
            publish_time,
            create_time
        FROM finkg1.project_data
        WHERE project_id = %s
        ORDER BY create_time DESC
        LIMIT %s OFFSET %s
        """
        cursor.execute(data_query, (project_id, page_size, offset))
        result = cursor.fetchall()

        formatted_data = []
        for idx, row in enumerate(result, start=1):
            formatted_data.append({
                "index": idx + offset,
                "title": row["title"] or "",
                "content": row["content"] or "",
                "publishTime": str(row["publish_time"]) if row["publish_time"] else "",
                "summary": row["summary"] or ""
            })

        return jsonify({
            "status": 200,
            "data": formatted_data,
            "count": total,
            "project_id": project_id,
            "page": page,
            "page_size": page_size
        })

    except Exception as e:
        print(f"Error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "status": 500,
            "message": "服务器内部错误",
            "error": str(e)
        })
    finally:
        cursor.close()


@extractSample_bp.route('/extractSample/saveSelectData', methods=['POST'])
def save_selected_data():
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        announcement_ids = data.get('announcement_ids', [])

        if not project_id:
            return jsonify({"msg": "project_id 不能为空", "status": 400})
        if not announcement_ids or not isinstance(announcement_ids, list):
            return jsonify({"msg": "announcement_ids 必须是非空数组", "status": 400})

        client = get_client()
        cursor = client.cursor()

        # 获取现有data_list
        project_query = "SELECT data_list FROM finkg1.graph_project WHERE id = %s"
        cursor.execute(project_query, (project_id,))
        project_result = cursor.fetchone()

        if not project_result:
            return jsonify({"msg": "项目不存在", "status": 404})

        current_id_list = []
        if project_result['data_list']:
            try:
                current_id_list = json.loads(project_result['data_list'])
                if not isinstance(current_id_list, list):
                    current_id_list = []
            except json.JSONDecodeError:
                current_id_list = []

        new_ids = [str(id) for id in announcement_ids if str(id) not in current_id_list]
        if not new_ids:
            return jsonify({
                "status": 200,
                "msg": "所有数据已存在，未添加新数据",
                "added_count": 0
            })

        updated_id_list = current_id_list + new_ids

        update_query = "UPDATE finkg1.graph_project SET data_list = %s WHERE id = %s"
        cursor.execute(update_query, (json.dumps(updated_id_list, ensure_ascii=False), project_id))
        client.commit()

        return jsonify({
            "status": 200,
            "msg": f"成功添加 {len(new_ids)} 条数据",
            "added_count": len(new_ids),
            "total_count": len(updated_id_list)
        })

    except Exception as e:
        client.rollback()
        print(f"保存数据异常: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "msg": f"保存失败: {str(e)}",
            "status": 500
        })
    finally:
        cursor.close()


# @extractSample_bp.route('/extractSample/getProjectAnnouncements', methods=['POST'])
# def get_project_announcements():
#     try:
#         data = request.get_json()
#         project_id = data.get('project_id')
#
#         if not project_id:
#             return jsonify({"msg": "project_id 不能为空", "status": 400})
#
#         client = get_client()
#         cursor = client.cursor()
#
#         # 获取项目中的公告ID列表
#         project_query = "SELECT data_list FROM finkg1.graph_project WHERE id = %s"
#         cursor.execute(project_query, (project_id,))
#         project_result = cursor.fetchone()
#
#         if not project_result:
#             return jsonify({"msg": "项目不存在", "status": 404})
#
#         id_list = []
#         if project_result['data_list']:
#             try:
#                 id_list = json.loads(project_result['data_list'])
#                 if not isinstance(id_list, list):
#                     id_list = []
#             except json.JSONDecodeError:
#                 id_list = []
#
#         if not id_list:
#             return jsonify({
#                 "status": 200,
#                 "data": [],
#                 "count": 0
#             })
#
#         # 构建IN查询参数
#         placeholders = ','.join(['%s'] * len(id_list))
#         announcement_query = f"""
#         SELECT id, title, content, date, stock_num
#         FROM finkg1.announce_data
#         WHERE id IN ({placeholders})
#         ORDER BY date DESC
#         """
#         cursor.execute(announcement_query, tuple(id_list))
#         result = cursor.fetchall()
#
#         formatted_data = []
#         for row in result:
#             formatted_data.append({
#                 "id": str(row['id']),
#                 "title": row['title'],
#                 "content": row['content'],
#                 "date": str(row['date']) if row['date'] else '',
#                 "stock_num": row['stock_num']
#             })
#
#         return jsonify({
#             "status": 200,
#             "data": formatted_data,
#             "count": len(formatted_data)
#         })
#
#     except Exception as e:
#         print(f"获取项目公告异常: {str(e)}")
#         traceback.print_exc()
#         return jsonify({
#             "msg": f"获取数据失败: {str(e)}",
#             "status": 500
#         })
#     finally:
#         cursor.close()


# 在文件开头添加 MongoDB 连接

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mongo_client = MongoClient('mongodb://localhost:27017/')
mongo_db = mongo_client['finkg1']
mongo_collection = mongo_db['event_data']


@extractSample_bp.route('/extractSample/getProjectAnnouncements', methods=['POST'])
def get_project_announcements():
    try:
        data = request.get_json()
        project_id = data.get('project_id')

        if not project_id:
            return jsonify({"msg": "project_id 不能为空", "status": 400})

        # 获取项目中的公告ID列表（从 MySQL 的 graph_project 表）
        mysql_client = get_client()
        cursor = mysql_client.cursor()
        project_query = "SELECT data_list FROM finkg1.graph_project WHERE id = %s"
        cursor.execute(project_query, (project_id,))
        project_result = cursor.fetchone()
        cursor.close()

        if not project_result:
            return jsonify({"msg": "项目不存在", "status": 404})

        id_list = []
        if project_result['data_list']:
            try:
                id_list = json.loads(project_result['data_list'])
                if not isinstance(id_list, list):
                    id_list = []
            except json.JSONDecodeError:
                id_list = []

        if not id_list:
            return jsonify({"status": 200, "data": [], "count": 0})

        # 优化：使用 $in 一次性查询所有匹配的文档
        logger.info(f"从 MongoDB 查询 {len(id_list)} 个 ID")

        # 方案1：如果数据存储在 data._id 字段中
        cursor = mongo_collection.find({'data._id': {'$in': id_list}})

        # 方案2：如果数据存储在 data.id 字段中（根据实际数据结构选择）
        # cursor = mongo_collection.find({'data.id': {'$in': id_list}})

        matched_items = []
        for doc in cursor:
            if doc and 'data' in doc:
                matched_items.append(doc['data'])

        logger.info(f"MongoDB 查询完成，找到 {len(matched_items)} 条匹配数据")

        return jsonify({
            "status": 200,
            "data": matched_items,
            "count": len(matched_items)
        })

    except Exception as e:
        logger.error(f"获取项目公告异常: {str(e)}")
        traceback.print_exc()
        return jsonify({"msg": f"获取数据失败: {str(e)}", "status": 500})

@extractSample_bp.route('/extractSample/deleteSelectedData', methods=['POST'])
def delete_selected_data():
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        ids = data.get('ids', [])  # 前端传来的要删除的公告ID列表

        if not project_id:
            return jsonify({"msg": "project_id 不能为空", "status": 400})
        if not ids or not isinstance(ids, list):
            return jsonify({"msg": "ids 必须是非空数组", "status": 400})

        client = get_client()
        cursor = client.cursor()

        # 1. 获取项目当前的data_list
        project_query = "SELECT data_list FROM finkg1.graph_project WHERE id = %s"
        cursor.execute(project_query, (project_id,))
        project_result = cursor.fetchone()

        if not project_result:
            return jsonify({"msg": "项目不存在", "status": 404})

        # 2. 解析现有的data_list
        current_id_list = []
        if project_result['data_list']:
            try:
                current_id_list = json.loads(project_result['data_list'])
                if not isinstance(current_id_list, list):
                    current_id_list = []
            except json.JSONDecodeError:
                current_id_list = []

        # 3. 从current_id_list中移除要删除的ID
        original_count = len(current_id_list)
        # 使用列表推导式过滤掉要删除的ID
        updated_id_list = [id for id in current_id_list if id not in ids]
        deleted_count = original_count - len(updated_id_list)

        # 4. 如果没有实际删除任何ID，直接返回
        if deleted_count == 0:
            return jsonify({
                "status": 200,
                "msg": "未找到匹配的公告ID",
                "deleted_count": 0
            })

        # 5. 更新data_list字段
        update_query = "UPDATE finkg1.graph_project SET data_list = %s WHERE id = %s"
        cursor.execute(update_query, (json.dumps(updated_id_list, ensure_ascii=False), project_id))
        client.commit()

        return jsonify({
            "status": 200,
            "msg": f"成功删除 {deleted_count} 条数据",
            "deleted_count": deleted_count,
            "remaining_count": len(updated_id_list)
        })

    except Exception as e:
        client.rollback()
        print(f"删除数据异常: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "msg": f"删除失败: {str(e)}",
            "status": 500
        })
    finally:
        cursor.close()


@extractSample_bp.route('/extractSample/searchMongoEvents', methods=['POST'])
def search_mongo_events():
    """
    直连 MongoDB event_data 检索样本，条件与事件看板类似，便于抽取步骤快速圈选。
    返回结构与 list_all 兼容：{ code, data: { messages, total } }。
    """
    try:
        raw_payload = request.get_json(silent=True)
        data = raw_payload if isinstance(raw_payload, dict) else {}

        def _as_text(value, default=""):
            if value is None:
                return default
            if isinstance(value, list):
                if not value:
                    return default
                value = value[0]
            return str(value).strip()

        page = max(1, int(data.get("page") or 1))
        page_size = min(max(1, int(data.get("page_size") or data.get("size") or 20)), 100)
        skip = (page - 1) * page_size

        keyword = _as_text(data.get("keyword"))
        stock_code = _as_text(data.get("stock_code"))
        raw_event_type = data.get("event_type")
        event_types = []
        if isinstance(raw_event_type, list):
            event_types = [str(x).strip() for x in raw_event_type if str(x).strip()]
        else:
            single_event_type = str(raw_event_type or "").strip()
            if single_event_type:
                event_types = [single_event_type]
        start_time = _as_text(data.get("start_time"))
        end_time = _as_text(data.get("end_time"))
        sort_field = _as_text(data.get("sort_field"), "event_time") or "event_time"
        sort_order = int(data.get("sort_order") if data.get("sort_order") is not None else -1)

        from bson.regex import Regex
        from routes.llmGenKG_api import get_mongo_event_collection

        conditions = []
        if stock_code:
            reg = Regex(stock_code, "i")
            conditions.append({
                "$or": [
                    {"data.symbol": reg},
                    {"data.company_of_interest": reg},
                ]
            })
        if keyword:
            kw = Regex(keyword, "i")
            conditions.append({
                "$or": [
                    {"data.title": kw},
                    {"data.event_description": kw},
                    {"data.summary": kw},
                    {"data.event_name": kw},
                ]
            })
        if event_types:
            if len(event_types) == 1:
                conditions.append({"data.event_type": event_types[0]})
            else:
                conditions.append({"data.event_type": {"$in": event_types}})

        time_filter = {}
        if start_time:
            time_filter["$gte"] = start_time
        if end_time:
            time_filter["$lte"] = end_time
        if time_filter:
            conditions.append({"data.event_time": time_filter})

        query_filter = {"$and": conditions} if conditions else {}

        sort_map = {
            "event_time": ("data.event_time", sort_order),
            "trade_date": ("data.trade_date", sort_order),
            "_id": ("_id", sort_order),
        }
        sort_key, direction = sort_map.get(sort_field, ("data.event_time", sort_order))

        client = None
        try:
            client, coll = get_mongo_event_collection()
            total = coll.count_documents(query_filter)
            cursor = (
                coll.find(query_filter)
                .sort(sort_key, direction)
                .skip(skip)
                .limit(page_size)
            )

            messages = []
            for doc in cursor:
                item = doc.get("data") or {}
                raw_data = item.get("raw_data") or {}
                oid = item.get("_id") or doc.get("_id")
                messages.append({
                    "_id": oid,
                    "id": str(oid) if oid is not None else "",
                    "title": item.get("title") or item.get("event_name") or "",
                    "event_description": item.get("event_description") or item.get("content") or "",
                    "event_time": item.get("event_time") or "",
                    "symbol": item.get("symbol") or "",
                    "board_name": item.get("board_name") or raw_data.get("board_name") or "",
                    "company_of_interest": item.get("company_of_interest") or "",
                    "event_type": item.get("event_type") or "",
                    "event_subtype": item.get("event_subtype") or raw_data.get("event_subtype") or "",
                    "impact_level": item.get("impact_level") or raw_data.get("impact_level") or "",
                    "sentiment": item.get("sentiment") or raw_data.get("sentiment") or "",
                    "trigger_rule": item.get("trigger_rule") or {},
                    "raw_data": raw_data or item,
                })

            return jsonify({
                "code": 0,
                "msg": "ok",
                "data": {
                    "messages": messages,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                },
            })
        finally:
            if client:
                client.close()

    except Exception as e:
        logger.error("searchMongoEvents 失败: %s", e, exc_info=True)
        return jsonify({"code": 1, "msg": str(e), "data": {"messages": [], "total": 0}}), 500