# -*- coding: utf-8 -*-
"""
Phase-3 自动评估脚本：构建前后对比
- 节点/关系 precision & recall（需 gold 标注）
- QA 命中率（evidence 命中；可选 answer 命中）

用法示例：
python tests/evaluate_phase3_pipeline.py --dataset tests/eval_dataset.json --output runtime/eval/phase3_report.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


THIS_FILE = Path(__file__).resolve()
BACKEND_ROOT = THIS_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agents.master_build_workflow import invoke_master_build  # noqa: E402
from routes.askAI_api import generate_answer_from_evidence, retrieve_project_kg  # noqa: E402
from routes.llmGenKG_api import fetch_samples_from_mongo  # noqa: E402


def _norm_text(v: Any) -> str:
    return " ".join(str(v or "").strip().lower().split())


def _norm_type(v: Any) -> str:
    s = _norm_text(v)
    if s in ("1", "event", "事件"):
        return "event"
    return "entity"


@contextmanager
def _temporary_env(overrides: Dict[str, str]):
    backup = {k: os.environ.get(k) for k in overrides.keys()}
    try:
        for k, v in overrides.items():
            os.environ[k] = str(v)
        yield
    finally:
        for k, old in backup.items():
            if old is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = old


@dataclass
class Metrics:
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    fn: int


@dataclass
class BuildEvalResult:
    profile_name: str
    elapsed_seconds: float
    node_count: int
    edge_count: int
    conflict_count: int
    quality_report: Dict[str, Any]
    node_metrics: Optional[Metrics]
    edge_metrics: Optional[Metrics]
    qa_metrics: Dict[str, Any]


def _prf(pred: Set[Any], gold: Set[Any]) -> Metrics:
    tp = len(pred & gold)
    fp = len(pred - gold)
    fn = len(gold - pred)
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return Metrics(
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        tp=tp,
        fp=fp,
        fn=fn,
    )


def _node_set(rows: Sequence[Dict[str, Any]]) -> Set[Tuple[str, str]]:
    out: Set[Tuple[str, str]] = set()
    for r in rows or []:
        t = _norm_type(r.get("type"))
        v = _norm_text(r.get("value"))
        if v:
            out.add((t, v))
    return out


def _edge_set(rows: Sequence[Dict[str, Any]]) -> Set[Tuple[str, str, str]]:
    out: Set[Tuple[str, str, str]] = set()
    for r in rows or []:
        ft = _norm_text((r.get("from_node") or {}).get("value"))
        tt = _norm_text((r.get("to_node") or {}).get("value"))
        rt = _norm_text(r.get("type"))
        if ft and tt and rt:
            out.add((ft, tt, rt))
    return out


def _gold_edge_set(rows: Sequence[Dict[str, Any]]) -> Set[Tuple[str, str, str]]:
    out: Set[Tuple[str, str, str]] = set()
    for r in rows or []:
        fv = _norm_text(r.get("from_value") or r.get("from"))
        tv = _norm_text(r.get("to_value") or r.get("to"))
        rt = _norm_text(r.get("type"))
        if fv and tv and rt:
            out.add((fv, tv, rt))
    return out


def _to_dict_metrics(m: Optional[Metrics]) -> Optional[Dict[str, Any]]:
    if m is None:
        return None
    return {
        "precision": m.precision,
        "recall": m.recall,
        "f1": m.f1,
        "tp": m.tp,
        "fp": m.fp,
        "fn": m.fn,
    }


def _compute_qa_metrics(
    project_id: str,
    qa_cases: Sequence[Dict[str, Any]],
    top_k_per_project: int,
    qa_use_llm: bool,
) -> Dict[str, Any]:
    if not qa_cases:
        return {
            "case_count": 0,
            "evidence_hit_rate": 0.0,
            "answer_hit_rate": None,
            "details": [],
        }

    evidence_hits = 0
    answer_hits = 0
    details = []

    for case in qa_cases:
        query = str(case.get("query") or "").strip()
        expected_terms = [str(x).strip() for x in (case.get("expected_terms") or []) if str(x).strip()]
        if not query:
            continue

        evidence = retrieve_project_kg(project_id, query, top_k=top_k_per_project)
        blob = "\n".join(str(e.get("snippet") or "") for e in (evidence or []))
        ev_hit = any(term in blob for term in expected_terms) if expected_terms else bool(evidence)
        if ev_hit:
            evidence_hits += 1

        ans_hit = None
        answer_preview = ""
        if qa_use_llm:
            answer = generate_answer_from_evidence(
                query=query,
                evidence=evidence,
                deep_think=False,
                detail_level="brief",
            )
            answer_preview = str(answer or "")[:220]
            ans_hit = any(term in answer for term in expected_terms) if expected_terms else bool(answer)
            if ans_hit:
                answer_hits += 1

        details.append(
            {
                "query": query,
                "expected_terms": expected_terms,
                "evidence_count": len(evidence or []),
                "evidence_hit": ev_hit,
                "answer_hit": ans_hit,
                "answer_preview": answer_preview,
            }
        )

    total = len(details)
    return {
        "case_count": total,
        "evidence_hit_rate": round(evidence_hits / max(1, total), 4),
        "answer_hit_rate": round(answer_hits / max(1, total), 4) if qa_use_llm else None,
        "details": details,
    }


def _default_profiles() -> Dict[str, Dict[str, str]]:
    baseline = {
        "KG_NODE_SANITIZE_ENABLED": "false",
        "KG_REL_SECOND_PASS_ENABLED": "false",
        "KG_REL_SENTENCE_CANDIDATE_ENABLED": "false",
        "REL_EXTRACT_SAMPLE_SCOPED": "false",
        "KG_QA_EXCLUDE_OPTIMIZATION_REL": "false",
        "KG_QA_REL_MIN_CONF": "0.0",
    }
    optimized = {
        "KG_NODE_SANITIZE_ENABLED": "true",
        "KG_REL_SECOND_PASS_ENABLED": "true",
        "KG_REL_SENTENCE_CANDIDATE_ENABLED": "true",
        "REL_EXTRACT_SAMPLE_SCOPED": "true",
        "KG_QA_EXCLUDE_OPTIMIZATION_REL": "true",
        "KG_QA_REL_MIN_CONF": "0.55",
    }
    return {"baseline": baseline, "optimized": optimized}


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_profile(
    profile_name: str,
    env_overrides: Dict[str, str],
    project_id: str,
    sample_ids: Sequence[Any],
    gold_nodes: Sequence[Dict[str, Any]],
    gold_edges: Sequence[Dict[str, Any]],
    qa_cases: Sequence[Dict[str, Any]],
    top_k_per_project: int,
    qa_use_llm: bool,
) -> BuildEvalResult:
    with _temporary_env(env_overrides):
        samples = fetch_samples_from_mongo(list(sample_ids))
        if not samples:
            raise RuntimeError("未获取到样本，请检查 sample_ids 或 Mongo 连接")

        t0 = time.perf_counter()
        final_state = invoke_master_build(
            project_id=project_id,
            sample_ids=list(sample_ids),
            samples=samples,
            run_id=None,
            resume_from=None,
            plan_overrides={"mode": "full", "persistence_mode": "replace"},
            has_incremental_impact=False,
        )
        elapsed = time.perf_counter() - t0

        if final_state.get("error"):
            raise RuntimeError(f"{profile_name} 构建失败: {final_state.get('error')}")

        pred_nodes = final_state.get("nodes") or []
        pred_edges = final_state.get("edges") or []
        conflicts = final_state.get("conflicts") or []
        quality_report = ((final_state.get("graph_enrichment") or {}).get("quality_report") or {})

        node_metrics = None
        if gold_nodes:
            node_metrics = _prf(_node_set(pred_nodes), _node_set(gold_nodes))

        edge_metrics = None
        if gold_edges:
            edge_metrics = _prf(_edge_set(pred_edges), _gold_edge_set(gold_edges))

        qa_metrics = _compute_qa_metrics(
            project_id=project_id,
            qa_cases=qa_cases,
            top_k_per_project=top_k_per_project,
            qa_use_llm=qa_use_llm,
        )

        return BuildEvalResult(
            profile_name=profile_name,
            elapsed_seconds=round(elapsed, 3),
            node_count=len(pred_nodes),
            edge_count=len(pred_edges),
            conflict_count=len(conflicts),
            quality_report=quality_report,
            node_metrics=node_metrics,
            edge_metrics=edge_metrics,
            qa_metrics=qa_metrics,
        )


def _delta(before: Optional[Metrics], after: Optional[Metrics]) -> Optional[Dict[str, float]]:
    if before is None or after is None:
        return None
    return {
        "precision": round(after.precision - before.precision, 4),
        "recall": round(after.recall - before.recall, 4),
        "f1": round(after.f1 - before.f1, 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase-3 KG pipeline 自动评估")
    parser.add_argument("--dataset", required=True, help="评估数据 JSON 路径")
    parser.add_argument("--output", default="runtime/eval/phase3_report.json", help="输出报告 JSON 路径")
    parser.add_argument("--top-k-per-project", type=int, default=8, help="QA 检索 top_k")
    parser.add_argument("--qa-use-llm", action="store_true", help="是否评估 answer 命中（会调用大模型）")
    args = parser.parse_args()

    dataset_path = Path(args.dataset).resolve()
    output_path = Path(args.output).resolve()

    data = _load_json(dataset_path)
    project_id = str(data.get("project_id") or "").strip()
    sample_ids = data.get("sample_ids") or []
    gold = data.get("gold") or {}
    gold_nodes = gold.get("nodes") or []
    gold_edges = gold.get("edges") or []
    qa_cases = data.get("qa_cases") or []

    if not project_id:
        raise ValueError("dataset 缺少 project_id")
    if not sample_ids:
        raise ValueError("dataset 缺少 sample_ids")

    profiles_cfg = _default_profiles()

    baseline = _run_profile(
        profile_name="baseline",
        env_overrides=profiles_cfg["baseline"],
        project_id=project_id,
        sample_ids=sample_ids,
        gold_nodes=gold_nodes,
        gold_edges=gold_edges,
        qa_cases=qa_cases,
        top_k_per_project=args.top_k_per_project,
        qa_use_llm=args.qa_use_llm,
    )

    optimized = _run_profile(
        profile_name="optimized",
        env_overrides=profiles_cfg["optimized"],
        project_id=project_id,
        sample_ids=sample_ids,
        gold_nodes=gold_nodes,
        gold_edges=gold_edges,
        qa_cases=qa_cases,
        top_k_per_project=args.top_k_per_project,
        qa_use_llm=args.qa_use_llm,
    )

    report = {
        "project_id": project_id,
        "sample_count": len(sample_ids),
        "profiles": {
            "baseline": {
                "elapsed_seconds": baseline.elapsed_seconds,
                "node_count": baseline.node_count,
                "edge_count": baseline.edge_count,
                "conflict_count": baseline.conflict_count,
                "quality_report": baseline.quality_report,
                "node_metrics": _to_dict_metrics(baseline.node_metrics),
                "edge_metrics": _to_dict_metrics(baseline.edge_metrics),
                "qa_metrics": baseline.qa_metrics,
            },
            "optimized": {
                "elapsed_seconds": optimized.elapsed_seconds,
                "node_count": optimized.node_count,
                "edge_count": optimized.edge_count,
                "conflict_count": optimized.conflict_count,
                "quality_report": optimized.quality_report,
                "node_metrics": _to_dict_metrics(optimized.node_metrics),
                "edge_metrics": _to_dict_metrics(optimized.edge_metrics),
                "qa_metrics": optimized.qa_metrics,
            },
        },
        "delta": {
            "node_metrics": _delta(baseline.node_metrics, optimized.node_metrics),
            "edge_metrics": _delta(baseline.edge_metrics, optimized.edge_metrics),
            "qa_evidence_hit_rate": round(
                float(optimized.qa_metrics.get("evidence_hit_rate") or 0.0)
                - float(baseline.qa_metrics.get("evidence_hit_rate") or 0.0),
                4,
            ),
            "qa_answer_hit_rate": (
                round(
                    float(optimized.qa_metrics.get("answer_hit_rate") or 0.0)
                    - float(baseline.qa_metrics.get("answer_hit_rate") or 0.0),
                    4,
                )
                if args.qa_use_llm
                else None
            ),
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("[phase3-eval] 评估完成")
    print(f"[phase3-eval] 报告路径: {output_path}")
    print(json.dumps(report.get("delta") or {}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
