import json
import logging
import uuid
import os
from datetime import datetime
from typing import Dict, Set
from flask import Blueprint, request, jsonify
from pymongo import MongoClient
from agents.incremental_kg_impact import run_incremental_kg_impact_scan

logger = logging.getLogger(__name__)
evolution_bp = Blueprint('evolution', __name__)

def _get_mysql():
    from database import get_client
    return get_client()

def _parse_json_list(raw):
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []

def _graph_ids_for_project(project_id: str) -> Dict[str, Set[str]]:
    """读取当前项目已持久化的节点和关系 ID，用于计算增量构建差异。"""
    client = _get_mysql()
    try:
        with client.cursor() as cur:
            cur.execute("SELECT id FROM node_table WHERE project_id = %s", (project_id,))
            node_ids = {str(row.get("id") or "").strip() for row in (cur.fetchall() or [])}
            cur.execute("SELECT id FROM edge_table WHERE project_id = %s", (project_id,))
            edge_ids = {str(row.get("id") or "").strip() for row in (cur.fetchall() or [])}
        return {
            "node_ids": {x for x in node_ids if x},
            "edge_ids": {x for x in edge_ids if x},
        }
    except Exception as e:
        logger.warning("[Evolution API] 读取图谱差异基线失败: %s", e, exc_info=True)
        return {"node_ids": set(), "edge_ids": set()}
    finally:
        client.close()

def ensure_log_table():
    client = _get_mysql()
    try:
        with client.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS kg_auto_evolution_log (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    project_id VARCHAR(32) NOT NULL,
                    sample_count INT DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    notified TINYINT(1) DEFAULT 0
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识图谱动态演进通知日志';
            """)
        client.commit()
    except Exception as e:
        logger.error(f"[Evolution API] Ensure log table error: {e}")
    finally:
        client.close()

@evolution_bp.route('/inject_mock', methods=['POST'])
def inject_mock_event():
    """
    注入一条新资讯/网页摘要，并立即按新增样本触发增量图谱构建。
    前端可提供项目ID、标题、内容、URL和来源。
    """
    data = request.json or {}
    project_id = data.get('project_id')
    title = data.get('title')
    content = data.get('content')
    url = data.get('url') or "http://mock.event/local"
    source = data.get('source') or ("联网网页摘要" if url != "http://mock.event/local" else "实时演示终端")
    
    if not project_id or not title or not content:
        return jsonify({"success": False, "message": "缺少必填参数 (project_id, title, content)"}), 400

    item_id = f"web_{uuid.uuid4().hex[:10]}"
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    before_ids = _graph_ids_for_project(str(project_id))
    
    # 1. 插入 MongoDB event_data
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    mongo_db_name = os.getenv("MONGO_DB", "finkg1")
    mongo_collection_name = os.getenv("MONGO_COLLECTION", "event_data")
    mongo_client = None
    try:
        mongo_client = MongoClient(mongo_uri)
        col = mongo_client[mongo_db_name][mongo_collection_name]
        col.insert_one({
            "item_id": item_id,
            "title": title,
            "content": content,
            "summary": content,
            "pub_time": now_str,
            "url": url,
            "source": source,
            "insert_time": now_str,
            # fetch_samples_from_mongo 按 data._id 读取样本。这里必须写入同构 data 结构，
            # 否则后续增量构建会读不到网页摘要样本。
            "data": {
                "_id": item_id,
                "title": title,
                "content": content,
                "summary": content,
                "event_description": content,
                "event_time": now_str,
                "source": source,
                "url": url,
                "raw_data": {
                    "标题": title,
                    "网页摘要": content,
                    "来源链接": url,
                },
            }
        })
    except Exception as e:
        logger.error(f"MongoDB Insert Error: {e}")
        return jsonify({"success": False, "message": f"MongoDB写入失败: {e}"}), 500
    finally:
        try:
            mongo_client.close()
        except Exception:
            pass

    # 2. 更新 MySQL graph_project 的 data_list
    client = _get_mysql()
    try:
        with client.cursor() as cur:
            cur.execute("SELECT data_list FROM graph_project WHERE id = %s", (project_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({"success": False, "message": "找不到该项目"}), 404
            
            data_list = _parse_json_list(row.get("data_list"))
            if item_id not in {str(x) for x in data_list}:
                data_list.append(item_id)
            cur.execute(
                "UPDATE graph_project SET data_list = %s WHERE id = %s",
                (json.dumps(data_list, ensure_ascii=False), project_id)
            )
        client.commit()
    except Exception as e:
        logger.error(f"MySQL Update Error: {e}")
        return jsonify({"success": False, "message": f"MySQL项目更新失败: {e}"}), 500
    finally:
        client.close()

    # 3. 标记增量影响，并立即触发当前项目的增量图谱构建。
    # 之前只标记 pending，导致网页摘要未作为新样本真正参与构建。
    affected_projects = run_incremental_kg_impact_scan([item_id])
    incremental_result = {}
    if str(project_id) in {str(x) for x in affected_projects}:
        try:
            from routes.llmGenKG_api import run_incremental_graph_for_project
            incremental_result = run_incremental_graph_for_project(str(project_id)) or {}
        except Exception as e:
            logger.error("[Evolution API] 网页摘要增量构建失败: %s", e, exc_info=True)
            return jsonify({
                "success": False,
                "message": f"网页摘要已写入样本库，但增量图谱构建失败: {e}",
                "item_id": item_id,
            }), 500
    else:
        incremental_result = {"skipped": True, "reason": "project_not_marked"}

    if incremental_result.get("skipped"):
        return jsonify({
            "success": False,
            "message": f"网页摘要已写入样本库，但增量构建未执行: {incremental_result.get('reason')}",
            "item_id": item_id,
            "incremental_result": incremental_result,
        }), 500

    if incremental_result.get("success") is False:
        return jsonify({
            "success": False,
            "message": f"网页摘要已写入样本库，但增量图谱构建失败: {incremental_result.get('error') or '未知错误'}",
            "item_id": item_id,
            "incremental_result": incremental_result,
        }), 500

    after_ids = _graph_ids_for_project(str(project_id))
    new_node_ids = sorted(after_ids["node_ids"] - before_ids["node_ids"])
    new_edge_ids = sorted(after_ids["edge_ids"] - before_ids["edge_ids"])
    
    return jsonify({
        "success": True, 
        "message": f"网页摘要已作为新样本注入，并完成增量图谱构建。新事件ID: {item_id}",
        "item_id": item_id,
        "incremental_result": incremental_result,
        "new_node_ids": new_node_ids,
        "new_edge_ids": new_edge_ids,
    })

@evolution_bp.route('/status', methods=['GET'])
def check_evolution_status():
    """
    前端轮询此接口，获取某项目是否刚刚完成了动态演进。
    """
    project_id = request.args.get('project_id')
    if not project_id:
        return jsonify({"success": False, "message": "缺少 project_id"}), 400
        
    ensure_log_table()
    client = _get_mysql()
    try:
        with client.cursor() as cur:
            cur.execute("""
                SELECT id, sample_count, created_at 
                FROM kg_auto_evolution_log 
                WHERE project_id = %s AND notified = 0
                ORDER BY created_at DESC LIMIT 1
            """, (project_id,))
            row = cur.fetchone()
            if row:
                return jsonify({
                    "success": True,
                    "has_new_update": True,
                    "log_id": row['id'],
                    "sample_count": row['sample_count'],
                    "time": str(row['created_at'])
                })
            else:
                return jsonify({"success": True, "has_new_update": False})
    except Exception as e:
        logger.error(f"Check status error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        client.close()

@evolution_bp.route('/ack', methods=['POST'])
def ack_evolution_notification():
    """
    前端弹出通知后，调用此接口确认已读，避免重复弹窗。
    """
    log_id = request.json.get('log_id')
    if not log_id:
        return jsonify({"success": False, "message": "缺少 log_id"}), 400
        
    client = _get_mysql()
    try:
        with client.cursor() as cur:
            cur.execute("UPDATE kg_auto_evolution_log SET notified = 1 WHERE id = %s", (log_id,))
        client.commit()
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Ack notification error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        client.close()
