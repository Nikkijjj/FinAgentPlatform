# -*- coding: utf-8 -*-
"""
一键构建：LangGraph 多功能 Agent 协作（动态分支 + 规划 + 质量 + checkpoint）。
"""
from __future__ import annotations

import json
import traceback
from typing import Any, Dict, Iterator, List, Literal, Optional, TypedDict

from agents.build_planner_agent import make_build_plan
from agents.checkpoint_manager_agent import load_checkpoint, make_run_id, save_checkpoint
from agents.quality_scorer_agent import score_graph_quality

try:
    from langgraph.graph import END, StateGraph
except ImportError as _e:  # pragma: no cover
    StateGraph = None  # type: ignore
    END = None  # type: ignore
    _LANGGRAPH_IMPORT_ERROR = _e
else:
    _LANGGRAPH_IMPORT_ERROR = None


_STAGE_ORDER = [
    "planning",
    "node_extraction",
    "assess_stale_need",
    "stale_graph_cleanup",
    "stale_skip",
    "relation_extraction",
    "graph_optimization",
    "conflict_handling",
    "conflict_mitigation",
    "quality_scoring",
    "graph_assembly",
]


class MasterBuildState(TypedDict, total=False):
    project_id: str
    sample_ids: List[Any]
    samples: list
    nodes: list
    edges: list
    conflicts: list
    graph: dict
    error: Optional[str]
    needs_stale_cleanup: bool
    graph_enrichment: Dict[str, Any]
    build_plan: Dict[str, Any]
    run_id: str
    resume_from: Optional[str]


def _should_skip(stage: str, state: MasterBuildState) -> bool:
    resume_from = str(state.get("resume_from") or "").strip()
    if not resume_from or resume_from not in _STAGE_ORDER:
        return False
    if stage not in _STAGE_ORDER:
        return False
    return _STAGE_ORDER.index(stage) < _STAGE_ORDER.index(resume_from)


def _checkpoint(stage: str, state: MasterBuildState, updates: Dict[str, Any]) -> None:
    run_id = str(state.get("run_id") or "").strip()
    if not run_id:
        return
    merged = dict(state)
    merged.update(updates or {})
    try:
        save_checkpoint(run_id, stage, merged)
    except Exception:
        traceback.print_exc()


def _planning(state: MasterBuildState) -> Dict[str, Any]:
    if state.get("error"):
        return {}
    if _should_skip("planning", state):
        return {}
    try:
        bp_in = state.get("build_plan") if isinstance(state.get("build_plan"), dict) else {}
        has_incremental_impact = bool(bp_in.get("has_incremental_impact", False))
        nested = bp_in.get("overrides") if isinstance(bp_in.get("overrides"), dict) else {}
        user_over = {k: v for k, v in bp_in.items() if k not in ("overrides",)}
        user_over.update(nested)
        plan = make_build_plan(
            project_id=state["project_id"],
            sample_ids=state.get("sample_ids") or [],
            has_incremental_impact=has_incremental_impact,
            user_plan_overrides=user_over,
        )
        updates = {"build_plan": plan}
        _checkpoint("planning", state, updates)
        return updates
    except Exception as e:
        traceback.print_exc()
        return {"error": f"规划 Agent 失败: {e}"}


def _graph_assembly(state: MasterBuildState) -> Dict[str, Any]:
    if state.get("error"):
        g: Dict[str, Any] = {}
        if state.get("graph_enrichment"):
            g["quality"] = state["graph_enrichment"]
        return {"graph": g}
    try:
        from routes.llmGenKG_api import run_graph_agent

        graph = run_graph_agent(
            state.get("nodes") or [],
            state.get("edges") or [],
            state.get("conflicts") or [],
            state["project_id"],
        )
        enr = state.get("graph_enrichment")
        if enr:
            graph = {**graph, "quality": enr}
        updates = {"graph": graph}
        _checkpoint("graph_assembly", state, updates)
        return updates
    except Exception as e:
        traceback.print_exc()
        return {"error": f"图组装 Agent 失败: {e}", "graph": {}}


def _node_extraction(state: MasterBuildState) -> Dict[str, Any]:
    if state.get("error"):
        return {}
    if _should_skip("node_extraction", state):
        return {}
    try:
        from routes.llmGenKG_api import run_node_agent

        plan = state.get("build_plan") or {}
        persistence = str(plan.get("persistence_mode") or "replace").strip().lower()
        nodes = run_node_agent(
            state["samples"],
            state["project_id"],
            batch_size=int(plan.get("sample_batch_size", 20)),
            mode=str(plan.get("mode", "full")),
            persistence_mode=persistence if persistence in ("replace", "merge") else "replace",
        )
        updates = {"nodes": nodes}
        _checkpoint("node_extraction", state, updates)
        return updates
    except Exception as e:
        traceback.print_exc()
        return {"error": f"节点抽取 Agent 失败: {e}"}


def _assess_stale_need(state: MasterBuildState) -> Dict[str, Any]:
    if state.get("error"):
        return {}
    if _should_skip("assess_stale_need", state):
        return {}
    try:
        from routes.llmGenKG_api import should_run_stale_graph_cleanup

        need = should_run_stale_graph_cleanup(state["project_id"])
        plan = state.get("build_plan") or {}
        mode = str(plan.get("mode", "full")).strip().lower()
        # 增量模式下必须保留既有图结构，不执行 stale 清理。
        if mode == "incremental":
            need = False
        strict = bool(plan.get("strict_stale_cleanup", False))
        if strict and mode != "incremental":
            need = True
        updates = {"needs_stale_cleanup": need}
        _checkpoint("assess_stale_need", state, updates)
        return updates
    except Exception as e:
        traceback.print_exc()
        return {"error": f"过时清理评估失败: {e}"}


def _stale_graph_cleanup(state: MasterBuildState) -> Dict[str, Any]:
    if state.get("error"):
        return {}
    if _should_skip("stale_graph_cleanup", state):
        return {}
    try:
        from routes.llmGenKG_api import run_stale_graph_cleanup

        if not run_stale_graph_cleanup(state["project_id"]):
            return {"error": "过时关系/图数据清理失败（MySQL 或 Neo4j）"}
        updates = {}
        _checkpoint("stale_graph_cleanup", state, updates)
        return updates
    except Exception as e:
        traceback.print_exc()
        return {"error": f"过时图数据清理 Agent 失败: {e}"}


def _stale_skip(state: MasterBuildState) -> Dict[str, Any]:
    """图中无旧数据，跳过清理。"""
    _checkpoint("stale_skip", state, {})
    return {}


def _route_after_planning(state: MasterBuildState) -> Literal["early_finish", "node"]:
    if state.get("error"):
        return "early_finish"
    return "node"


def _route_after_node_extraction(
    state: MasterBuildState,
) -> Literal["early_finish", "assess"]:
    if state.get("error"):
        return "early_finish"
    return "assess"


def _route_after_stale_assessment(
    state: MasterBuildState,
) -> Literal["early_finish", "stale", "skip_stale"]:
    if state.get("error"):
        return "early_finish"
    if state.get("needs_stale_cleanup"):
        return "stale"
    return "skip_stale"


def _relation_extraction(state: MasterBuildState) -> Dict[str, Any]:
    if state.get("error"):
        return {}
    if _should_skip("relation_extraction", state):
        return {}
    try:
        from routes.llmGenKG_api import extract_relations_only, get_nodes_from_database
        from routes.llmGenKG_api import save_edges_to_databases

        plan = state.get("build_plan") or {}
        nodes_for_rel = state.get("nodes") or []
        if str(plan.get("mode", "full")).strip().lower() == "incremental":
            nodes_for_rel = get_nodes_from_database(state["project_id"])
        edges = extract_relations_only(
            nodes_for_rel,
            state["samples"],
            state["project_id"],
            mode=str(plan.get("mode", "full")),
        )
        replace_graph = str(plan.get("persistence_mode") or "replace").strip().lower() != "merge"
        if edges:
            ok = save_edges_to_databases(
                edges,
                state["project_id"],
                relation_type="general",
                replace_graph=replace_graph,
            )
            if not ok:
                return {"error": "关系抽取结果持久化失败（MySQL 或 Neo4j）"}
        updates = {"edges": edges or []}
        _checkpoint("relation_extraction", state, updates)
        return updates
    except Exception as e:
        traceback.print_exc()
        return {"error": f"关系抽取 Agent 失败: {e}"}


def _route_after_relation(
    state: MasterBuildState,
) -> Literal["early_finish", "optimize"]:
    if state.get("error"):
        return "early_finish"
    return "optimize"


def _graph_optimization(state: MasterBuildState) -> Dict[str, Any]:
    if state.get("error"):
        return {}
    if _should_skip("graph_optimization", state):
        return {}
    try:
        from agents.graph_optimization_agent import optimize_graph_structure
        from routes.llmGenKG_api import save_edges_to_databases

        plan = state.get("build_plan") or {}
        enable_opt = bool(plan.get("enable_graph_optimization", True))
        if not enable_opt:
            updates = {
                "graph_enrichment": {
                    **(state.get("graph_enrichment") or {}),
                    "graph_optimization": {
                        "enabled": False,
                        "message": "已按构建计划跳过图优化阶段",
                    },
                }
            }
            _checkpoint("graph_optimization", state, updates)
            return updates

        result = optimize_graph_structure(
            project_id=state["project_id"],
            nodes=state.get("nodes") or [],
            edges=state.get("edges") or [],
            enable_isolated_repair=bool(plan.get("enable_isolated_repair", True)),
        )
        optimized_edges = result.get("edges") or []
        changed = bool(result.get("changed", False))
        report = result.get("report") or {}

        if changed and optimized_edges:
            replace_graph = str(plan.get("persistence_mode") or "replace").strip().lower() != "merge"
            ok = save_edges_to_databases(
                optimized_edges,
                state["project_id"],
                relation_type="general",
                replace_graph=replace_graph,
            )
            if not ok:
                return {"error": "图优化结果持久化失败（MySQL 或 Neo4j）"}

        enrich = state.get("graph_enrichment") or {}
        enrich = {
            **enrich,
            "graph_optimization": {
                "enabled": True,
                "changed": changed,
                **report,
            },
        }
        updates = {
            "edges": optimized_edges,
            "graph_enrichment": enrich,
        }
        _checkpoint("graph_optimization", state, updates)
        return updates
    except Exception as e:
        traceback.print_exc()
        return {"error": f"图优化 Agent 失败: {e}"}


def _conflict_handling(state: MasterBuildState) -> Dict[str, Any]:
    if state.get("error"):
        return {}
    if _should_skip("conflict_handling", state):
        return {}
    try:
        from routes.llmGenKG_api import run_conflict_agent

        deep_check = bool((state.get("build_plan") or {}).get("enable_conflict_deep_check", False))
        conflicts = run_conflict_agent(state.get("edges") or [], deep_check=deep_check)
        updates = {"conflicts": conflicts}
        _checkpoint("conflict_handling", state, updates)
        return updates
    except Exception as e:
        traceback.print_exc()
        return {"error": f"冲突处理 Agent 失败: {e}"}


def _route_after_conflict(
    state: MasterBuildState,
) -> Literal["early_finish", "mitigate", "quality"]:
    if state.get("error"):
        return "early_finish"
    conflicts = state.get("conflicts") or []
    if conflicts:
        return "mitigate"
    return "quality"


def _conflict_mitigation(state: MasterBuildState) -> Dict[str, Any]:
    """动态冲突分支：为图谱补充质量元数据，便于前端展示复核提示。"""
    if state.get("error"):
        return {}
    if _should_skip("conflict_mitigation", state):
        return {}
    conflicts = state.get("conflicts") or []
    if not conflicts:
        return {}
    types_found = list({c.get("type", "") for c in conflicts if isinstance(c, dict)})
    base = state.get("graph_enrichment") or {}
    updates = {
        "graph_enrichment": {
            **base,
            "requires_manual_review": True,
            "conflict_count": len(conflicts),
            "conflict_types": sorted({t for t in types_found if t}),
            "message": "检测到潜在关系冲突，建议结合冲突列表人工复核后再用于分析。",
        }
    }
    _checkpoint("conflict_mitigation", state, updates)
    return updates


def _build_quality_report(state: MasterBuildState, quality_score: Dict[str, Any]) -> Dict[str, Any]:
    nodes = [n for n in (state.get("nodes") or []) if isinstance(n, dict)]
    edges = [e for e in (state.get("edges") or []) if isinstance(e, dict)]

    def _fill_rate(rows: list, keys: list) -> float:
        if not rows:
            return 0.0
        total = len(rows) * max(1, len(keys))
        hit = 0
        for r in rows:
            props = r.get("properties") if isinstance(r.get("properties"), dict) else {}
            for k in keys:
                v = props.get(k)
                if v not in (None, "", [], {}):
                    hit += 1
        return round(hit / total, 4)

    node_fill = _fill_rate(
        nodes,
        ["canonical_name", "certainty", "polarity", "evidence_sentence", "event_time_norm"],
    )
    edge_fill = _fill_rate(
        edges,
        ["trigger_phrase", "direction", "strength", "temporal_order", "evidence_sentence"],
    )

    generic_values = {"相关", "关联", "影响", "涉及", "同样本关联", "同段共现"}
    semantic_ok = 0
    for e in edges:
        v = str(e.get("value") or "").strip()
        if len(v) >= 2 and v not in generic_values:
            semantic_ok += 1
    semantic_ratio = round(semantic_ok / max(1, len(edges)), 4)

    q = quality_score or {}
    overall = float((q.get("overall_score") if isinstance(q, dict) else 0.0) or 0.0)
    grade = "A" if overall >= 0.82 else "B" if overall >= 0.68 else "C" if overall >= 0.52 else "D"

    return {
        "grade": grade,
        "overall_score": round(overall, 4),
        "node_property_fill_rate": node_fill,
        "edge_property_fill_rate": edge_fill,
        "semantic_relation_ratio": semantic_ratio,
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "conflict_count": len(state.get("conflicts") or []),
            "sample_count": len(state.get("samples") or []),
        },
    }


def _quality_scoring(state: MasterBuildState) -> Dict[str, Any]:
    if state.get("error"):
        return {}
    if _should_skip("quality_scoring", state):
        return {}
    try:
        report = score_graph_quality(
            nodes=state.get("nodes") or [],
            edges=state.get("edges") or [],
            conflicts=state.get("conflicts") or [],
            samples=state.get("samples") or [],
        )
        quality_report = _build_quality_report(state, report)
        enrich = state.get("graph_enrichment") or {}
        enrich = {**enrich, "quality_score": report, "quality_report": quality_report}
        updates = {"graph_enrichment": enrich}
        _checkpoint("quality_scoring", state, updates)
        return updates
    except Exception as e:
        traceback.print_exc()
        return {"error": f"质量评分 Agent 失败: {e}"}


def _build_graph():
    if StateGraph is None:
        raise RuntimeError(
            "未安装 langgraph，请执行: pip install langgraph"
        ) from _LANGGRAPH_IMPORT_ERROR

    g = StateGraph(MasterBuildState)
    g.add_node("planning", _planning)
    g.add_node("node_extraction", _node_extraction)
    g.add_node("assess_stale_need", _assess_stale_need)
    g.add_node("stale_graph_cleanup", _stale_graph_cleanup)
    g.add_node("stale_skip", _stale_skip)
    g.add_node("relation_extraction", _relation_extraction)
    g.add_node("graph_optimization", _graph_optimization)
    g.add_node("conflict_handling", _conflict_handling)
    g.add_node("conflict_mitigation", _conflict_mitigation)
    g.add_node("quality_scoring", _quality_scoring)
    g.add_node("graph_assembly", _graph_assembly)

    g.set_entry_point("planning")

    g.add_conditional_edges(
        "planning",
        _route_after_planning,
        {"early_finish": "graph_assembly", "node": "node_extraction"},
    )
    g.add_conditional_edges(
        "node_extraction",
        _route_after_node_extraction,
        {"early_finish": "graph_assembly", "assess": "assess_stale_need"},
    )
    g.add_conditional_edges(
        "assess_stale_need",
        _route_after_stale_assessment,
        {
            "early_finish": "graph_assembly",
            "stale": "stale_graph_cleanup",
            "skip_stale": "stale_skip",
        },
    )
    g.add_edge("stale_graph_cleanup", "relation_extraction")
    g.add_edge("stale_skip", "relation_extraction")

    g.add_conditional_edges(
        "relation_extraction",
        _route_after_relation,
        {"early_finish": "graph_assembly", "optimize": "graph_optimization"},
    )
    g.add_edge("graph_optimization", "conflict_handling")
    g.add_conditional_edges(
        "conflict_handling",
        _route_after_conflict,
        {
            "early_finish": "graph_assembly",
            "mitigate": "conflict_mitigation",
            "quality": "quality_scoring",
        },
    )
    g.add_edge("conflict_mitigation", "quality_scoring")
    g.add_edge("quality_scoring", "graph_assembly")
    g.add_edge("graph_assembly", END)
    return g.compile()


_compiled = None


def get_master_build_graph():
    global _compiled
    if _compiled is None:
        _compiled = _build_graph()
    return _compiled


def _progress_event_for_stage(stage: str) -> Dict[str, Any]:
    """阶段进度：phase=nodes|relations；progress 为全流程 0～100；subtitle 用于弹窗文案。"""
    mapping: Dict[str, tuple] = {
        "planning": ("nodes", 6, "规划构建任务"),
        "node_extraction": ("nodes", 38, "抽取图谱节点"),
        "assess_stale_need": ("nodes", 46, "评估过时图数据"),
        "stale_graph_cleanup": ("nodes", 50, "清理过时 MySQL / Neo4j"),
        "stale_skip": ("nodes", 52, "跳过清理（无需删除旧数据）"),
        "relation_extraction": ("relations", 74, "抽取实体关系"),
        "graph_optimization": ("relations", 80, "图结构优化（孤立节点修复）"),
        "conflict_handling": ("relations", 86, "冲突检测"),
        "conflict_mitigation": ("relations", 90, "标记待人工复核"),
        "quality_scoring": ("relations", 95, "图谱质量评分"),
        "graph_assembly": ("relations", 100, "组装可视化图数据"),
    }
    phase, pct, subtitle = mapping.get(stage, ("nodes", 0, stage))
    return {"phase": phase, "progress": pct, "subtitle": subtitle}


def iter_master_build_ndjson(
    project_id: str,
    sample_ids: list,
    samples: list,
    run_id: Optional[str] = None,
    resume_from: Optional[str] = None,
    plan_overrides: Optional[Dict[str, Any]] = None,
    has_incremental_impact: bool = False,
    incremental_snapshot: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    history_sample_ids: Optional[list] = None,
) -> Iterator[str]:
    """
    一键构建 NDJSON 流：每执行完 LangGraph 一个节点输出一行 progress，
    最后输出一行 complete（结构与 master_agent_run 的 data 对齐）或 error。
    """
    final_run_id = run_id or make_run_id(prefix=f"master_{project_id}")
    _hist_ids = history_sample_ids if history_sample_ids is not None else sample_ids
    initial: MasterBuildState = {
        "project_id": project_id,
        "sample_ids": sample_ids,
        "samples": samples,
        "nodes": [],
        "edges": [],
        "conflicts": [],
        "graph": {},
        "error": None,
        "needs_stale_cleanup": False,
        "graph_enrichment": {},
        "run_id": final_run_id,
        "resume_from": resume_from,
        "build_plan": {
            "has_incremental_impact": has_incremental_impact,
            "overrides": plan_overrides or {},
        },
    }
    if final_run_id:
        ckpt = load_checkpoint(final_run_id)
        if ckpt and isinstance(ckpt.get("state"), dict):
            loaded = ckpt["state"]
            merged = dict(initial)
            merged.update(loaded)
            merged["run_id"] = final_run_id
            merged["resume_from"] = resume_from or ckpt.get("stage")
            initial = merged  # type ignore

    running: Dict[str, Any] = dict(initial)

    try:
        graph = get_master_build_graph()

        for chunk in graph.stream(initial, stream_mode="updates"):
            if not isinstance(chunk, dict):
                continue
            for stage_name, upd in chunk.items():
                if isinstance(upd, dict):
                    running.update(upd)
                meta = _progress_event_for_stage(str(stage_name))
                line = {
                    "status": "progress",
                    "stage": stage_name,
                    "phase": meta["phase"],
                    "progress": meta["progress"],
                    "label": meta["subtitle"],
                }
                yield json.dumps(line, ensure_ascii=False) + "\n"

        err = running.get("error")
        if err:
            yield json.dumps(
                {"status": "error", "success": False, "message": str(err)},
                ensure_ascii=False,
            ) + "\n"
            return

        nodes = running.get("nodes") or []
        edges = running.get("edges") or []
        conflicts = running.get("conflicts") or []
        graph_payload = running.get("graph") or {}

        try:
            from routes.llmGenKG_api import _finalize_master_build_payload, save_extraction_history
            from agents.incremental_kg_impact import clear_incremental_impact_for_project

            _uid = str(user_id).strip() if user_id else None
            payload = _finalize_master_build_payload(
                project_id,
                list(_hist_ids or sample_ids),
                run_id_hint=final_run_id,
                build_plan=running.get("build_plan"),
                graph_enrichment=running.get("graph_enrichment"),
                needs_stale_cleanup=bool(running.get("needs_stale_cleanup")),
                incremental_impact_before_build=incremental_snapshot,
                samples_override=samples,
                nodes=nodes,
                edges=edges,
                conflicts=conflicts,
                graph=graph_payload,
            )
            save_extraction_history(
                project_id,
                "master",
                list(_hist_ids or sample_ids),
                payload.get("nodes") or [],
                payload.get("edges") or [],
                run_id=final_run_id,
                user_id=_uid,
                workflow_meta=dict(payload.get("workflow_meta") or {}),
            )
            clear_incremental_impact_for_project(project_id)
        except Exception as persist_err:
            traceback.print_exc()
            raise RuntimeError(f"Master构建结果保存失败: {persist_err}") from persist_err
        yield json.dumps({"status": "complete", "success": True, "data": payload}, ensure_ascii=False) + "\n"
    except Exception as e:
        traceback.print_exc()
        yield json.dumps(
            {"status": "error", "success": False, "message": str(e)},
            ensure_ascii=False,
        ) + "\n"


def invoke_master_build(
    project_id: str,
    sample_ids: list,
    samples: list,
    run_id: Optional[str] = None,
    resume_from: Optional[str] = None,
    plan_overrides: Optional[Dict[str, Any]] = None,
    has_incremental_impact: bool = False,
) -> MasterBuildState:
    """执行一键构建状态图，支持 run_id checkpoint 与 resume_from。"""
    final_run_id = run_id or make_run_id(prefix=f"master_{project_id}")
    initial: MasterBuildState = {
        "project_id": project_id,
        "sample_ids": sample_ids,
        "samples": samples,
        "nodes": [],
        "edges": [],
        "conflicts": [],
        "graph": {},
        "error": None,
        "needs_stale_cleanup": False,
        "graph_enrichment": {},
        "run_id": final_run_id,
        "resume_from": resume_from,
        "build_plan": {
            "has_incremental_impact": has_incremental_impact,
            "overrides": plan_overrides or {},
        },
    }
    # 可重入：若 run_id 已有 checkpoint，优先加载历史状态继续。
    if final_run_id:
        ckpt = load_checkpoint(final_run_id)
        if ckpt and isinstance(ckpt.get("state"), dict):
            loaded = ckpt["state"]
            merged = dict(initial)
            merged.update(loaded)
            merged["run_id"] = final_run_id
            merged["resume_from"] = resume_from or ckpt.get("stage")
            initial = merged  # type: ignore

    try:
        graph = get_master_build_graph()
        result = graph.invoke(initial)
        if isinstance(result, dict):
            result["run_id"] = final_run_id
            result["resume_from"] = None
        return result
    except Exception as e:
        traceback.print_exc()
        initial["error"] = str(e)
        initial["run_id"] = final_run_id
        return initial
