from __future__ import annotations

from typing import Any, Dict, List, Optional


def _to_int(v, default):
    try:
        if v is None:
            return default
        return int(v)
    except Exception:
        return default


def make_build_plan(
    project_id: str,
    sample_ids: List[Any],
    has_incremental_impact: bool = False,
    user_plan_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    BuildPlannerAgent:
    - 决定全量/增量策略
    - 决定样本分批大小
    - 决定是否启用冲突精检
    - 决定是否启用严格 stale 清理
    """
    overrides = user_plan_overrides or {}
    sample_count = len(sample_ids or [])

    # 默认全量重建；仅在请求显式传入 mode=incremental（或专用增量接口）时合并写入
    default_mode = str(overrides.get("mode") or "full").strip().lower()
    if default_mode not in ("full", "incremental"):
        default_mode = "full"
    mode = default_mode

    if sample_count <= 50:
        default_batch_size = 20
    elif sample_count <= 200:
        default_batch_size = 30
    else:
        default_batch_size = 40

    sample_batch_size = max(5, _to_int(overrides.get("sample_batch_size"), default_batch_size))
    # 增量构建通常样本更碎片，默认关闭 deep_check，减少误报；可通过 overrides 强制开启。
    deep_check_default = (sample_count <= 200) and (mode == "full")
    enable_conflict_deep_check = bool(overrides.get("enable_conflict_deep_check", deep_check_default))
    strict_stale_cleanup = bool(overrides.get("strict_stale_cleanup", mode == "full"))
    enable_graph_optimization = bool(overrides.get("enable_graph_optimization", True))
    enable_isolated_repair = bool(overrides.get("enable_isolated_repair", True))

    persistence_mode = overrides.get("persistence_mode")
    if persistence_mode not in ("replace", "merge"):
        persistence_mode = "merge" if mode == "incremental" else "replace"

    return {
        "project_id": project_id,
        "mode": mode,  # full / incremental
        "persistence_mode": persistence_mode,  # replace=覆盖写入；merge=合并 upsert
        "sample_batch_size": sample_batch_size,
        "enable_conflict_deep_check": enable_conflict_deep_check,
        "strict_stale_cleanup": strict_stale_cleanup,
        "enable_graph_optimization": enable_graph_optimization,
        "enable_isolated_repair": enable_isolated_repair,
        "sample_count": sample_count,
        "has_incremental_impact_hint": bool(has_incremental_impact),
    }
