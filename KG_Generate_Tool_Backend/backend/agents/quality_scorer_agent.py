from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Set


def _clip01(v: float) -> float:
    if v < 0:
        return 0.0
    if v > 1:
        return 1.0
    return v


def _parse_date(text: str):
    t = (text or "").strip()
    if not t:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(t[:19], fmt)
        except Exception:
            continue
    return None


def score_graph_quality(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    conflicts: List[Dict[str, Any]],
    samples: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    QualityScorerAgent:
    - 覆盖率（节点/关系相对样本规模）
    - 一致性（冲突率）
    - 新鲜度（基于事件时间衰减）
    - 结构性（孤立节点比例、连通性近似）
    """
    node_count = len(nodes or [])
    edge_count = len(edges or [])
    conflict_count = len(conflicts or [])
    sample_count = max(1, len(samples or []))

    # 1) 覆盖率：针对稀疏样本做自适应归一，避免固定分母对碎片化数据过度惩罚
    text_lengths = []
    sample_ids = set()
    for s in samples or []:
        sid = str((s or {}).get("id") or "").strip()
        if sid:
            sample_ids.add(sid)
        text_val = str((s or {}).get("event_description") or (s or {}).get("content") or "")
        if text_val:
            text_lengths.append(len(text_val))
    avg_text_len = (sum(text_lengths) / max(1, len(text_lengths))) if text_lengths else 0.0

    # 文本越短越稀疏，期望边/点数量应适度下调（范围 0.65~1.0）
    sparse_factor = max(0.65, min(1.0, avg_text_len / 240.0))
    expected_nodes_per_sample = 6.0 * sparse_factor
    expected_edges_per_sample = 8.0 * sparse_factor

    node_cov = _clip01(node_count / max(1.0, sample_count * expected_nodes_per_sample))
    edge_cov = _clip01(edge_count / max(1.0, sample_count * expected_edges_per_sample))

    # 样本锚定覆盖：至少有边/点挂到样本 ID，说明证据触达更广
    touched_sample_ids: Set[str] = set()
    for n in nodes or []:
        if not isinstance(n, dict):
            continue
        props = n.get("properties") if isinstance(n.get("properties"), dict) else {}
        sid = str(props.get("sample_id") or "").strip()
        if sid:
            touched_sample_ids.add(sid)
    for e in edges or []:
        if not isinstance(e, dict):
            continue
        props = e.get("properties") if isinstance(e.get("properties"), dict) else {}
        sid = str(props.get("sample_id") or "").strip()
        if sid:
            touched_sample_ids.add(sid)
    anchor_cov = _clip01(len(touched_sample_ids) / max(1, len(sample_ids))) if sample_ids else 0.5

    coverage = round(node_cov * 0.4 + edge_cov * 0.4 + anchor_cov * 0.2, 4)

    # 2) 一致性：冲突越多得分越低
    denom = max(1, edge_count)
    conflict_rate = conflict_count / denom
    consistency = round(_clip01(1.0 - min(1.0, conflict_rate * 2.0)), 4)

    # 3) 新鲜度：按样本日期与当前时间差做衰减
    now = datetime.now()
    parsed_dates = []
    for s in samples or []:
        d = _parse_date(str(s.get("event_time") or s.get("date") or ""))
        if d is not None:
            parsed_dates.append(d)
    if parsed_dates:
        avg_days = sum([(now - d).days for d in parsed_dates]) / max(1, len(parsed_dates))
        freshness = round(_clip01(1.0 - min(1.0, avg_days / 365.0)), 4)
    else:
        freshness = 0.6

    # 4) 结构性：孤立节点比例 + 连通分量近似
    node_ids: Set[str] = {str((n or {}).get("id")) for n in (nodes or []) if (n or {}).get("id") is not None}
    degree = {nid: 0 for nid in node_ids}
    for e in edges or []:
        s = str(e.get("from") or e.get("source") or "")
        t = str(e.get("to") or e.get("target") or "")
        if s in degree:
            degree[s] += 1
        if t in degree:
            degree[t] += 1
    isolated = sum(1 for _, d in degree.items() if d == 0)
    isolated_ratio = isolated / max(1, len(node_ids))
    structural = round(_clip01(1.0 - isolated_ratio), 4)

    overall = round(
        _clip01(coverage * 0.3 + consistency * 0.3 + freshness * 0.2 + structural * 0.2),
        4,
    )

    return {
        "overall_score": overall,
        "dimensions": {
            "coverage": coverage,
            "consistency": consistency,
            "freshness": freshness,
            "structural": structural,
        },
        "metrics": {
            "node_count": node_count,
            "edge_count": edge_count,
            "conflict_count": conflict_count,
            "sample_count": sample_count,
            "isolated_node_ratio": round(isolated_ratio, 4),
            "conflict_rate": round(conflict_rate, 4),
            "sample_anchor_coverage": round(anchor_cov, 4),
            "avg_sample_text_len": round(avg_text_len, 1),
            "coverage_sparse_factor": round(sparse_factor, 4),
        },
    }
