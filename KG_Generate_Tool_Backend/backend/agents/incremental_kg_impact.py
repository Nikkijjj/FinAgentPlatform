# -*- coding: utf-8 -*-
"""
增量同步后的知识图谱影响检测 Agent。

在 MongoDB event_data 批量 upsert 后，根据本次触及的 item_id 集合，
扫描 graph_project.data_list，对「已选样本与增量数据有交集」的项目打标，
提示一键构建/图谱内容可能已受影响，供动态 Stale/人工跟进。
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS kg_incremental_impact (
    project_id VARCHAR(32) NOT NULL PRIMARY KEY,
    pending TINYINT(1) NOT NULL DEFAULT 1,
    reason VARCHAR(512) NULL,
    affected_sample_ids JSON NULL,
    last_batch_touched_count INT NOT NULL DEFAULT 0,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='操作库增量对图谱构建的待处理影响标记';
"""


def _get_mysql():
    from database import get_client

    return get_client()


def ensure_kg_incremental_impact_table() -> None:
    client = _get_mysql()
    try:
        with client.cursor() as cur:
            cur.execute(_TABLE_SQL)
        client.commit()
    finally:
        client.close()


def run_incremental_kg_impact_scan(touched_item_ids: List[Any]) -> List[str]:
    """
    对「本次写入/更新」的样本 ID，扫描所有图谱项目的数据清单；
    若有交集，则将项目标记为 pending，表示知识图谱所依赖的操作库内容可能已变化。
    """
    if not touched_item_ids:
        return []

    ensure_kg_incremental_impact_table()
    touched = {str(x).strip() for x in touched_item_ids if x is not None and str(x).strip()}
    if not touched:
        return []

    reason = (
        "操作库（MongoDB event_data）增量同步触及本项目已选样本，"
        "原文/字段可能已更新，建议重新执行一键构建或核对图谱。"
    )
    affected_projects: List[str] = []
    client = _get_mysql()
    try:
        with client.cursor() as cur:
            cur.execute(
                "SELECT id, data_list FROM finkg1.graph_project"
            )
            rows = cur.fetchall() or []
            batch_n = len(touched)

            for row in rows:
                pid = str(row.get("id") or "")
                if not pid:
                    continue
                raw = row.get("data_list")
                if not raw:
                    continue
                try:
                    id_list = json.loads(raw) if isinstance(raw, str) else raw
                except (json.JSONDecodeError, TypeError):
                    continue
                if not isinstance(id_list, list):
                    continue
                proj_ids = {str(x).strip() for x in id_list if x is not None and str(x).strip()}
                inter = sorted(proj_ids & touched)
                if not inter:
                    continue

                affected_projects.append(pid)
                cur.execute(
                    """
                    INSERT INTO kg_incremental_impact
                        (project_id, pending, reason, affected_sample_ids, last_batch_touched_count)
                    VALUES (%s, 1, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        pending = 1,
                        reason = VALUES(reason),
                        affected_sample_ids = VALUES(affected_sample_ids),
                        last_batch_touched_count = VALUES(last_batch_touched_count),
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        pid,
                        reason,
                        json.dumps(inter, ensure_ascii=False),
                        batch_n,
                    ),
                )
            client.commit()
    except Exception as e:
        logger.error("[IncrementalKG] 扫描标记失败: %s", e, exc_info=True)
        try:
            client.rollback()
        except Exception:
            pass
        raise
    finally:
        client.close()

    if affected_projects:
        logger.info(
            "[IncrementalKG] 已标记 %s 个项目待关注（与本轮增量样本有交集）",
            len(affected_projects),
        )
    return affected_projects


def project_has_pending_incremental_impact(project_id: str) -> bool:
    ensure_kg_incremental_impact_table()
    client = _get_mysql()
    try:
        with client.cursor() as cur:
            cur.execute(
                "SELECT pending FROM kg_incremental_impact WHERE project_id = %s",
                (str(project_id),),
            )
            row = cur.fetchone()
            if not row:
                return False
            return int(row.get("pending") or 0) == 1
    finally:
        client.close()


def get_incremental_impact_record(project_id: str) -> Optional[Dict[str, Any]]:
    ensure_kg_incremental_impact_table()
    client = _get_mysql()
    try:
        with client.cursor() as cur:
            cur.execute(
                """
                SELECT project_id, pending, reason, affected_sample_ids,
                       last_batch_touched_count, updated_at
                FROM kg_incremental_impact
                WHERE project_id = %s
                """,
                (str(project_id),),
            )
            row = cur.fetchone()
            if not row:
                return None
            out = dict(row)
            aid = out.get("affected_sample_ids")
            if isinstance(aid, str):
                try:
                    out["affected_sample_ids"] = json.loads(aid)
                except json.JSONDecodeError:
                    out["affected_sample_ids"] = []
            if out.get("updated_at") is not None:
                out["updated_at"] = str(out["updated_at"])
            return out
    finally:
        client.close()


def clear_incremental_impact_for_project(project_id: str) -> None:
    """一键构建等业务完成后清除待处理标记。"""
    ensure_kg_incremental_impact_table()
    client = _get_mysql()
    try:
        with client.cursor() as cur:
            cur.execute(
                """
                UPDATE kg_incremental_impact
                SET pending = 0, reason = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE project_id = %s
                """,
                (str(project_id),),
            )
        client.commit()
    except Exception as e:
        logger.warning("[IncrementalKG] 清除标记失败 project_id=%s: %s", project_id, e)
        try:
            client.rollback()
        except Exception:
            pass
    finally:
        client.close()
