from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterator, List, Tuple

from openai import OpenAI


def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


def _to_int(v: Any, default: int = 0) -> int:
    try:
        if v is None:
            return default
        return int(float(v))
    except Exception:
        return default


def _extract_core_metrics(workflow_meta: Dict[str, Any], conflict_details: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    wm = workflow_meta or {}
    quality_report = wm.get("quality_report") if isinstance(wm.get("quality_report"), dict) else {}
    quality_score = wm.get("quality_score") if isinstance(wm.get("quality_score"), dict) else {}
    qs_metrics = quality_score.get("metrics") if isinstance(quality_score.get("metrics"), dict) else {}
    qr_stats = quality_report.get("stats") if isinstance(quality_report.get("stats"), dict) else {}

    conflict_count = _to_int(
        quality_report.get("conflict_count")
        or qr_stats.get("conflict_count")
        or qs_metrics.get("conflict_count")
        or wm.get("conflict_count"),
        0,
    )

    metrics = {
        "grade": str(quality_report.get("grade") or "-").strip() or "-",
        "overall_score": _to_float(quality_report.get("overall_score") or quality_score.get("overall_score"), 0.0),
        "node_property_fill_rate": _to_float(quality_report.get("node_property_fill_rate"), 0.0),
        "edge_property_fill_rate": _to_float(quality_report.get("edge_property_fill_rate"), 0.0),
        "semantic_relation_ratio": _to_float(quality_report.get("semantic_relation_ratio"), 0.0),
        "node_count": _to_int(qr_stats.get("node_count") or qs_metrics.get("node_count"), 0),
        "edge_count": _to_int(qr_stats.get("edge_count") or qs_metrics.get("edge_count"), 0),
        "sample_count": _to_int(qr_stats.get("sample_count") or qs_metrics.get("sample_count"), 0),
        "conflict_count": conflict_count,
        "conflict_rate": _to_float(qs_metrics.get("conflict_rate"), 0.0),
        "sample_anchor_coverage": _to_float(qs_metrics.get("sample_anchor_coverage"), 0.0),
        "isolated_node_ratio": _to_float(qs_metrics.get("isolated_node_ratio"), 0.0),
        "has_conflict_details": bool(conflict_details),
    }
    return metrics


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _build_fallback_report(metrics: Dict[str, Any]) -> str:
    conflict_count = _to_int(metrics.get("conflict_count"), 0)
    conflict_line = (
        f"冲突共 {conflict_count} 条，冲突率约 {_fmt_pct(_to_float(metrics.get('conflict_rate'), 0.0))}。"
        if conflict_count > 0
        else "当前未检测到显著冲突。"
    )

    return (
        "📌 图谱构建AI简报\n"
        f"整体等级 {metrics.get('grade', '-')}, 综合得分 {metrics.get('overall_score', 0):.4f}。\n"
        f"✅ 覆盖与结构：节点 {metrics.get('node_count', 0)}、关系 {metrics.get('edge_count', 0)}，"
        f"节点属性填充率 {_fmt_pct(_to_float(metrics.get('node_property_fill_rate'), 0.0))}，"
        f"关系属性填充率 {_fmt_pct(_to_float(metrics.get('edge_property_fill_rate'), 0.0))}，"
        f"语义关系占比 {_fmt_pct(_to_float(metrics.get('semantic_relation_ratio'), 0.0))}。\n"
        f"⚠️ 冲突与一致性：{conflict_line}"
        + (
            "当前返回仅包含冲突数量统计，未包含逐条冲突明细（无法直接定位到具体节点/关系）。\n"
            if conflict_count > 0 and not metrics.get("has_conflict_details")
            else "\n"
        )
        + "🛠 优化建议：\n"
        "1) 优先补充冲突明细输出（from/to/relation/reason/evidence），支持逐条复核与回溯。\n"
        "2) 对高冲突关系设定规则门槛（时间一致性、因果方向、样本证据长度）后再入图。\n"
        "3) 对低覆盖实体补充关键属性映射（主体、时间、金额、事件类型），提升查询可解释性。\n"
        "4) 建议对高频节点做去重与别名归一，降低伪冲突与孤立节点。"
    )


def _build_llm_prompt(metrics: Dict[str, Any], workflow_meta: Dict[str, Any], user_hint: str = "") -> str:
    meta_preview = {
        "run_id": workflow_meta.get("run_id"),
        "build_plan": workflow_meta.get("build_plan"),
        "quality_report": workflow_meta.get("quality_report"),
        "quality_score": workflow_meta.get("quality_score"),
    }
    return (
        "你是金融知识图谱构建质量评估顾问。请基于给定的指标与 workflow_meta 摘要，写一份“内容丰富、自然叙述、可执行”的中文分析报告。\n"
        "写作要求：\n"
        "- 目标读者是项目答辩/评审：语气专业、克制，不要口号式，不要堆模板。\n"
        "- 不要使用过度格式化的固定小标题/编号清单；可以分段，但段落要像人写的分析。\n"
        "- 不要使用 emoji。\n"
        "- 允许在关键数字处做解释（例如：填充率低意味着查询可解释性下降；冲突率高意味着一致性风险）。\n"
        "- 如果缺少冲突明细，只能做统计层诊断，必须明确说明“暂无法定位到具体冲突对/关系”。\n"
        "- 不要编造不存在的字段或结论。\n"
        "内容建议（务必覆盖但不必按条列）：\n"
        "1) 一句话总体结论（等级/得分 + 这份图谱当前适合做什么、不适合做什么）；\n"
        "2) 结构与覆盖：节点/关系规模、样本覆盖、孤立节点与锚定覆盖可能带来的影响；\n"
        "3) 质量风险：冲突（数量/比例）、语义关系占比、属性填充率的风险解读；\n"
        "4) 可执行改进：给出 4~8 条建议，优先级从“最先做/收益最大”到“可选优化”，每条建议尽量贴近系统现状（如补齐关键属性、归一别名、增加冲突明细输出、提高样本锚定覆盖等）。\n"
        "篇幅：建议 700~1200 字。\n"
        f"用户附加偏好：{user_hint or '无'}\n\n"
        f"指标摘要：{json.dumps(metrics, ensure_ascii=False)}\n"
        f"workflow_meta摘要：{json.dumps(meta_preview, ensure_ascii=False)}"
    )


def generate_kg_quality_analysis_report(
    workflow_meta: Dict[str, Any],
    conflict_details: List[Dict[str, Any]] | None = None,
    user_hint: str = "",
) -> Tuple[str, Dict[str, Any]]:
    metrics = _extract_core_metrics(workflow_meta or {}, conflict_details or [])

    api_key = os.getenv("DEEPSEEK_API_KEY") or ""
    base_url = os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
    model = os.getenv("KG_QUALITY_ANALYSIS_MODEL") or "deepseek-chat"

    if not api_key.strip():
        # 无密钥时回退模板，保证功能可用
        return _build_fallback_report(metrics), metrics

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        prompt = _build_llm_prompt(metrics, workflow_meta or {}, user_hint)
        resp = client.chat.completions.create(
            model=model,
            temperature=0.25,
            max_tokens=900,
            messages=[
                {
                    "role": "system",
                    "content": "你是审慎、专业的图谱质量分析助手。只输出报告正文，不要加多余前后缀。",
                },
                {"role": "user", "content": prompt},
            ],
        )
        text = str(((resp.choices or [{}])[0].message.content) or "").strip()
        if not text:
            return _build_fallback_report(metrics), metrics
        return text, metrics
    except Exception:
        return _build_fallback_report(metrics), metrics


def _chunk_text(text: str, chunk_size: int = 18) -> Iterator[str]:
    t = str(text or "")
    if not t:
        return
    for i in range(0, len(t), max(1, chunk_size)):
        yield t[i : i + max(1, chunk_size)]


def generate_kg_quality_analysis_report_stream(
    workflow_meta: Dict[str, Any],
    conflict_details: List[Dict[str, Any]] | None = None,
    user_hint: str = "",
) -> Tuple[Iterator[str], Dict[str, Any]]:
    """流式生成图谱质量分析报告，返回 (chunk迭代器, 指标摘要)。"""
    metrics = _extract_core_metrics(workflow_meta or {}, conflict_details or [])

    api_key = os.getenv("DEEPSEEK_API_KEY") or ""
    base_url = os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
    model = os.getenv("KG_QUALITY_ANALYSIS_MODEL") or "deepseek-chat"

    if not api_key.strip():
        fallback = _build_fallback_report(metrics)
        return _chunk_text(fallback), metrics

    def _iter_chunks() -> Iterator[str]:
        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            prompt = _build_llm_prompt(metrics, workflow_meta or {}, user_hint)
            stream = client.chat.completions.create(
                model=model,
                temperature=0.25,
                max_tokens=900,
                stream=True,
                messages=[
                    {
                        "role": "system",
                        "content": "你是审慎、专业的图谱质量分析助手。只输出报告正文，不要加多余前后缀。",
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            emitted = False
            for event in stream:
                try:
                    delta = ((event.choices or [{}])[0].delta.content) or ""
                except Exception:
                    delta = ""
                if delta:
                    emitted = True
                    # 进一步细分，避免“只吐一次大段”导致前端看起来像非流式
                    for c in _chunk_text(str(delta), chunk_size=12):
                        yield c

            if not emitted:
                # 流式无输出时回退模板
                for c in _chunk_text(_build_fallback_report(metrics)):
                    yield c
        except Exception:
            for c in _chunk_text(_build_fallback_report(metrics)):
                yield c

    return _iter_chunks(), metrics


def is_quality_analysis_intent(query: str) -> bool:
    q = str(query or "").lower()
    if not q:
        return False
    markers = [
        "质量报告",
        "质量分析",
        "构建效果",
        "图谱质量",
        "冲突分析",
        "kg构建",
        "kg 质量",
        "quality report",
        "quality analysis",
    ]
    return any(m in q for m in markers)
