# -*- coding: utf-8 -*-
"""
单次 KG-QA 请求的 Agent 上下文：贯穿 Planner / Tool / Skill，避免在长函数间散落无关参数。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentContext:
    """一次问答编排的共享状态（进程内、请求级）。"""

    user_id: Any
    query: str
    detail_level: str
    deep_think: bool
    top_k_per_project: int
    intent_mode: str
    session_id: Optional[str]
    username: Optional[str]
    uid: Optional[str]
    use_session_history: bool
    prior_messages: List[Dict[str, Any]]
    history_text: Optional[str]
    retrieval_query: str

    allow_general_fallback: bool = True
    enable_web_search: bool = False
    web_project_id: str = ""
    web_search_mode: str = "when_weak_evidence"

    detected_intent: Optional[str] = None
    strategy: Optional[str] = None
    legacy_bucket: Optional[str] = None

    scratch: Dict[str, Any] = field(default_factory=dict)

    def set_plan(self, intent: str, strategy: str, legacy_bucket: str) -> None:
        self.detected_intent = intent
        self.strategy = strategy
        self.legacy_bucket = legacy_bucket
