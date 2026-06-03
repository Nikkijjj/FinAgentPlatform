import os
import json
import logging
from pymongo import MongoClient
from database import get_client
from agents.master_build_workflow import invoke_master_build
from agents.incremental_kg_impact import clear_incremental_impact_for_project
from routes.evolution_api import ensure_log_table

logger = logging.getLogger(__name__)

def fetch_samples_from_mongo(sample_ids):
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    mongo_db_name = os.getenv("MONGO_DB", "finkg1")
    mongo_collection_name = os.getenv("MONGO_COLLECTION", "event_data")
    try:
        client = MongoClient(mongo_uri)
        col = client[mongo_db_name][mongo_collection_name]
        items = []
        for sid in sample_ids:
            item = col.find_one({"item_id": sid}, {"_id": 0})
            if item:
                items.append(item)
        return items
    except Exception as e:
        logger.error(f"[AutoEvolution Task] MongoDB Error: {e}")
        return []

def run_auto_evolution_job():
    """
    检查 MySQL 中的 kg_incremental_impact 表，
    如果发现有 pending=1 的项目，则拉取 affected_sample_ids 执行增量图谱构建。
    执行完成后，记录日志以便前端弹窗通知。
    """
    client = get_client()
    projects_to_evolve = []
    try:
        with client.cursor() as cur:
            cur.execute("""
                SELECT project_id, affected_sample_ids 
                FROM kg_incremental_impact 
                WHERE pending = 1
            """)
            projects_to_evolve = cur.fetchall()
    except Exception as e:
        logger.error(f"[AutoEvolution Task] DB Error: {e}")
        return
    finally:
        client.close()

    if not projects_to_evolve:
        return

    ensure_log_table()

    for row in projects_to_evolve:
        pid = row.get("project_id")
        aids_raw = row.get("affected_sample_ids")
        
        # 解析 affected_sample_ids
        aids = []
        if isinstance(aids_raw, str):
            try:
                aids = json.loads(aids_raw)
            except Exception:
                pass
        elif isinstance(aids_raw, list):
            aids = aids_raw
            
        if not aids:
            # 标记有误或者为空，直接清除标记
            clear_incremental_impact_for_project(pid)
            continue
            
        logger.info(f"[AutoEvolution] 检测到项目 {pid} 包含 {len(aids)} 个新事件，开始后台静默增量构建...")
        
        samples = fetch_samples_from_mongo(aids)
        if not samples:
            logger.warning(f"[AutoEvolution] MongoDB 未找到样本: {aids}")
            clear_incremental_impact_for_project(pid)
            continue
            
        try:
            # 调用原本的 Master Build 工作流进行增量合并
            final_state = invoke_master_build(
                project_id=str(pid),
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
                logger.error(f"[AutoEvolution] 项目 {pid} 增量构建失败: {final_state['error']}")
                continue
                
            logger.info(f"[AutoEvolution] 项目 {pid} 增量构建完成！正在生成通知日志...")
            
            # 清理 pending 标记
            clear_incremental_impact_for_project(pid)
            
            # 记录完成日志，前端轮询会抓取到
            client = get_client()
            with client.cursor() as cur:
                cur.execute("""
                    INSERT INTO kg_auto_evolution_log (project_id, sample_count)
                    VALUES (%s, %s)
                """, (str(pid), len(aids)))
            client.commit()
            client.close()
            
        except Exception as e:
            logger.error(f"[AutoEvolution] 处理项目 {pid} 时发生异常: {e}")
