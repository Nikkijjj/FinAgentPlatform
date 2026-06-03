from __future__ import annotations

from agents.intent_taxonomy import (
    INTENT_GENERAL,
    INTENT_KG_QUERY,
    FINE_INTENTS,
    fine_intent_to_legacy_tuple,
)


def list_user_projects(user_id, get_user_project_ids_fn):
    return get_user_project_ids_fn(user_id)


def aggregate_rank(chunks, aggregate_evidence_fn, max_items=12):
    return aggregate_evidence_fn(chunks, max_items=max_items)


def generate_answer(
    context,
    query,
    generate_answer_from_evidence_fn,
    deep_think=False,
    detail_level="brief",
    prior_messages=None,
):
    return generate_answer_from_evidence_fn(
        query=query,
        evidence=context,
        deep_think=deep_think,
        detail_level=detail_level,
        prior_messages=prior_messages,
    )


def cross_project_retrieval_skill(
    project_ids,
    query,
    retrieve_project_kg_fn,
    aggregate_rank_fn,
    top_k_per_project=3,
):
    project_evidence_map = {}
    no_limit = int(top_k_per_project or 0) <= 0
    for pid in project_ids:
        project_evidence_map[pid] = retrieve_project_kg_fn(pid, query, top_k=top_k_per_project)
    if no_limit:
        return aggregate_rank_fn(project_evidence_map, max_items=0)
    return aggregate_rank_fn(project_evidence_map, max_items=max(6, top_k_per_project * 4))


def evidence_citation_skill(evidence):
    citations = []
    for i, e in enumerate(evidence or [], start=1):
        row = {
            "id": i,
            "project_id": e.get("project_id", ""),
            "node_id": e.get("node_id", ""),
            "score": float(e.get("score") or 0.0),
            "snippet": str(e.get("snippet") or ""),
        }
        if e.get("project_name"):
            row["project_name"] = e.get("project_name")
        if e.get("source"):
            row["source"] = e.get("source")
        u = str(e.get("url") or "").strip()
        if u:
            row["url"] = u
        pt = str(e.get("page_title") or "").strip()
        if pt:
            row["page_title"] = pt
        if e.get("rel_types"):
            row["rel_types"] = e.get("rel_types")
        if e.get("run_id"):
            row["run_id"] = e.get("run_id")
        citations.append(row)
    return citations


def conflict_awareness_skill(evidence, detect_conflict_hints_fn, estimate_confidence_fn):
    hints = detect_conflict_hints_fn(evidence)
    confidence = estimate_confidence_fn(evidence)
    if confidence < 0.35:
        hints.append("当前证据置信度偏低，建议人工复核后再用于决策。")
    return hints


class QueryPlannerAgent:
    def __init__(self, classify_query_intent_fn):
        self._classify_query_intent = classify_query_intent_fn

    def plan(self, query, intent_mode, conversation_history=None):
        mode = str(intent_mode or "auto").strip().lower()
        if mode == "auto":
            detected_intent = self._classify_query_intent(
                query, conversation_history=conversation_history
            )
        elif mode == "kg":
            detected_intent = INTENT_KG_QUERY
        elif mode == "general":
            detected_intent = INTENT_GENERAL
        else:
            detected_intent = mode if mode in FINE_INTENTS else INTENT_GENERAL

        if detected_intent not in FINE_INTENTS:
            detected_intent = INTENT_GENERAL

        legacy_bucket, strategy = fine_intent_to_legacy_tuple(detected_intent)
        return {
            "intent": detected_intent,
            "strategy": strategy,
            "legacy_bucket": legacy_bucket,
        }


class SynthesisAgent:
    def __init__(
        self,
        generate_answer_fn,
        generate_general_answer_fn,
        evidence_citation_skill_fn,
        conflict_awareness_skill_fn,
    ):
        self._generate_answer = generate_answer_fn
        self._generate_general_answer = generate_general_answer_fn
        self._evidence_citation_skill = evidence_citation_skill_fn
        self._conflict_awareness_skill = conflict_awareness_skill_fn

    def synthesize_from_kg(
        self,
        query,
        evidence,
        deep_think=False,
        detail_level="brief",
        prior_messages=None,
    ):
        answer = self._generate_answer(
            context=evidence,
            query=query,
            deep_think=deep_think,
            detail_level=detail_level,
            prior_messages=prior_messages,
        )
        citations = self._evidence_citation_skill(evidence)
        quality_hints = self._conflict_awareness_skill(evidence)
        return answer, citations, quality_hints

    def synthesize_general(self, query, deep_think=False, detail_level="brief", prior_messages=None):
        return self._generate_general_answer(
            query,
            deep_think=deep_think,
            detail_level=detail_level,
            prior_messages=prior_messages,
        )
