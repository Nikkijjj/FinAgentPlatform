from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Set, Tuple


def _safe_conf(edge: Dict[str, Any]) -> float:
    props = edge.get("properties") if isinstance(edge.get("properties"), dict) else {}
    try:
        return float(props.get("confidence", 0.0))
    except Exception:
        return 0.0


def _edge_key_for_dedupe(edge: Dict[str, Any]) -> Tuple[str, str, str, str]:
    return (
        str(edge.get("from") or edge.get("source") or ""),
        str(edge.get("to") or edge.get("target") or ""),
        str(edge.get("type") or ""),
        str(edge.get("value") or ""),
    )


def _text_semantic_score(text: str) -> float:
    t = str(text or "").strip()
    if not t:
        return 0.0
    low_signal = {"相关", "关联", "影响", "涉及", "同样本关联", "同段共现", "语义关系"}
    if t in low_signal:
        return 0.15
    score = 0.45
    if len(t) >= 3:
        score += 0.15
    if any(k in t for k in ("投资", "收购", "披露", "监管", "担保", "诉讼", "合作", "签署", "回购", "处罚")):
        score += 0.2
    return min(1.0, score)


def _edge_rank(edge: Dict[str, Any]) -> Tuple[float, float, float]:
    props = edge.get("properties") if isinstance(edge.get("properties"), dict) else {}
    conf = _safe_conf(edge)
    semantic = _text_semantic_score(edge.get("value") or edge.get("eventRel") or "")
    has_ctx = 1.0 if str(props.get("context") or "").strip() else 0.0
    return (semantic, conf, has_ctx)


def _prune_conflicting_edges(edges: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    """
    冲突边治理：
    - 同向多类型关系：保留质量最高的一条，减少 run_conflict_agent 的同向冲突。
    - 双向因果关系：仅保留质量更高方向，避免双向因果冲突。
    """
    if not edges:
        return [], 0

    removed = 0
    by_dir: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for e in edges:
        src = str(e.get("from") or e.get("source") or "")
        dst = str(e.get("to") or e.get("target") or "")
        if not src or not dst or src == dst:
            continue
        by_dir.setdefault((src, dst), []).append(e)

    kept_dir: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for k, rows in by_dir.items():
        best = max(rows, key=_edge_rank)
        kept_dir[k] = best
        removed += max(0, len(rows) - 1)

    # 双向因果冲突再裁剪一次（仅当两侧都是因果关系）
    pruned = dict(kept_dir)
    done = set()
    for (src, dst), e in list(kept_dir.items()):
        rk = (dst, src)
        if rk not in kept_dir:
            continue
        pair = tuple(sorted([src, dst]))
        if pair in done:
            continue
        done.add(pair)

        e2 = kept_dir[rk]
        t1 = str(e.get("type") or "")
        t2 = str(e2.get("type") or "")
        if t1 != "因果关系" or t2 != "因果关系":
            continue

        if _edge_rank(e) >= _edge_rank(e2):
            pruned.pop(rk, None)
            removed += 1
        else:
            pruned.pop((src, dst), None)
            removed += 1

    return list(pruned.values()), removed


def _enrich_edge_properties_defaults(edges: List[Dict[str, Any]], node_map: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """为边补齐可推断的结构化属性，提升 edge_property_fill_rate。"""
    out: List[Dict[str, Any]] = []
    for raw in edges or []:
        e = dict(raw)
        props = dict(e.get("properties") or {})

        val = str(e.get("eventRel") or e.get("value") or "").strip()
        if val and not str(props.get("trigger_phrase") or "").strip():
            props["trigger_phrase"] = val[:32]

        if not str(props.get("direction") or "").strip():
            src = str(e.get("from") or "")
            dst = str(e.get("to") or "")
            src_node = node_map.get(src) or {}
            dst_node = node_map.get(dst) or {}
            src_t = str(src_node.get("type") or "").strip().lower()
            dst_t = str(dst_node.get("type") or "").strip().lower()
            if src_t in ("1", "event", "事件") and dst_t not in ("1", "event", "事件"):
                props["direction"] = "event_to_entity"
            elif src_t not in ("1", "event", "事件") and dst_t in ("1", "event", "事件"):
                props["direction"] = "entity_to_event"

        if not str(props.get("strength") or "").strip():
            conf = _safe_conf(e)
            if conf >= 0.85:
                props["strength"] = "high"
            elif conf >= 0.65:
                props["strength"] = "medium"
            elif conf > 0:
                props["strength"] = "low"

        if not str(props.get("evidence_sentence") or "").strip():
            ctx = str(props.get("context") or "").strip()
            if ctx:
                props["evidence_sentence"] = ctx[:160]

        # temporal_order 仅在可判定时补，避免无意义默认值污染
        if not str(props.get("temporal_order") or "").strip() and val:
            if any(k in val for k in ("之前", "先", "早于")):
                props["temporal_order"] = "before"
            elif any(k in val for k in ("之后", "后", "晚于")):
                props["temporal_order"] = "after"

        e["properties"] = props
        out.append(e)
    return out


def _sanitize_and_dedupe_edges(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    node_ids: Set[str] = {
        str((n or {}).get("id"))
        for n in (nodes or [])
        if (n or {}).get("id") is not None
    }
    best: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
    for e in edges or []:
        if not isinstance(e, dict):
            continue
        src = str(e.get("from") or e.get("source") or "")
        dst = str(e.get("to") or e.get("target") or "")
        if not src or not dst or src == dst:
            continue
        if src not in node_ids or dst not in node_ids:
            continue
        k = _edge_key_for_dedupe(e)
        prev = best.get(k)
        if prev is None or _safe_conf(e) > _safe_conf(prev):
            best[k] = dict(e)
    return list(best.values())


def _repair_isolated_nodes(
    project_id: str,
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    max_add_edges: int = 80,
    max_per_sample: int = 3,
) -> Tuple[List[Dict[str, Any]], int, int]:
    node_map: Dict[str, Dict[str, Any]] = {
        str(n.get("id")): n
        for n in (nodes or [])
        if isinstance(n, dict) and n.get("id")
    }
    if not node_map:
        return list(edges or []), 0, 0

    degree: Dict[str, int] = {nid: 0 for nid in node_map.keys()}
    undirected_pairs: Set[Tuple[str, str]] = set()
    for e in edges or []:
        src = str(e.get("from") or e.get("source") or "")
        dst = str(e.get("to") or e.get("target") or "")
        if src in degree:
            degree[src] += 1
        if dst in degree:
            degree[dst] += 1
        if src and dst and src != dst:
            undirected_pairs.add(tuple(sorted([src, dst])))

    isolated_ids = [nid for nid, d in degree.items() if d == 0]
    before = len(isolated_ids)
    if before < 2:
        return list(edges or []), before, before

    groups: Dict[str, List[Dict[str, Any]]] = {}
    for nid in isolated_ids:
        n = node_map[nid]
        props = n.get("properties") if isinstance(n.get("properties"), dict) else {}
        sid = str(props.get("sample_id") or "").strip()
        if not sid:
            continue
        groups.setdefault(sid, []).append(n)

    out_edges = list(edges or [])
    added = 0
    for sample_id, ns in groups.items():
        if added >= max_add_edges:
            break
        if len(ns) < 2:
            continue

        events = []
        entities = []
        for n in ns:
            t = str(n.get("type", "")).strip().lower()
            if t in ("1", "event", "事件"):
                events.append(n)
            else:
                entities.append(n)

        candidates: List[Tuple[str, str]] = []
        if events and entities:
            anchor = events[0]
            for ent in entities:
                candidates.append((str(ent.get("id")), str(anchor.get("id"))))
        else:
            ordered = sorted(ns, key=lambda x: str(x.get("id")))
            for i in range(len(ordered) - 1):
                candidates.append((str(ordered[i].get("id")), str(ordered[i + 1].get("id"))))

        local_add = 0
        for src, dst in candidates:
            if added >= max_add_edges or local_add >= max_per_sample:
                break
            if not src or not dst or src == dst:
                continue
            pair = tuple(sorted([src, dst]))
            if pair in undirected_pairs:
                continue
            if src not in node_map or dst not in node_map:
                continue

            val = "同样本关联"
            edge_id = hashlib.md5(f"opt_{project_id}_{sample_id}_{src}_{dst}".encode("utf-8")).hexdigest()
            out_edges.append({
                "id": edge_id,
                "type": "语义关系",
                "from": src,
                "to": dst,
                "from_node": node_map[src],
                "to_node": node_map[dst],
                "value": val,
                "eventRel": val,
                "project_id": project_id,
                "properties": {
                    "source": "GraphOptimizationAgent",
                    "channel": "opt",
                    "confidence": 0.42,
                    "sample_id": sample_id,
                    "repair": True,
                },
            })
            undirected_pairs.add(pair)
            degree[src] = degree.get(src, 0) + 1
            degree[dst] = degree.get(dst, 0) + 1
            added += 1
            local_add += 1

    after = sum(1 for _, d in degree.items() if d == 0)
    return out_edges, before, after


def optimize_graph_structure(
    project_id: str,
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    *,
    enable_isolated_repair: bool = True,
) -> Dict[str, Any]:
    """
    GraphOptimizationAgent:
    - 清洗无效边/自环边
    - 去重同义重复边
    - 检测孤立节点并做保守补边
    """
    sanitized = _sanitize_and_dedupe_edges(nodes or [], edges or [])
    removed_count = max(0, len(edges or []) - len(sanitized))

    pruned, pruned_count = _prune_conflicting_edges(sanitized)
    removed_count += pruned_count

    node_map = {
        str(n.get("id")): n
        for n in (nodes or [])
        if isinstance(n, dict) and n.get("id") is not None
    }
    enriched = _enrich_edge_properties_defaults(pruned, node_map)

    before_iso = 0
    after_iso = 0
    repaired = list(enriched)
    if enable_isolated_repair:
        repaired, before_iso, after_iso = _repair_isolated_nodes(project_id, nodes or [], enriched)
    else:
        node_ids = {
            str((n or {}).get("id"))
            for n in (nodes or [])
            if (n or {}).get("id") is not None
        }
        degree = {nid: 0 for nid in node_ids}
        for e in enriched:
            s = str(e.get("from") or e.get("source") or "")
            t = str(e.get("to") or e.get("target") or "")
            if s in degree:
                degree[s] += 1
            if t in degree:
                degree[t] += 1
        before_iso = sum(1 for _, d in degree.items() if d == 0)
        after_iso = before_iso

    added_count = max(0, len(repaired) - len(sanitized))
    changed = removed_count > 0 or added_count > 0

    return {
        "edges": repaired,
        "changed": changed,
        "report": {
            "removed_invalid_or_duplicate_edges": removed_count,
            "removed_conflict_pruned_edges": pruned_count,
            "added_isolated_repair_edges": added_count,
            "isolated_nodes_before": before_iso,
            "isolated_nodes_after": after_iso,
            "edge_count_before": len(edges or []),
            "edge_count_after": len(repaired),
        },
    }
