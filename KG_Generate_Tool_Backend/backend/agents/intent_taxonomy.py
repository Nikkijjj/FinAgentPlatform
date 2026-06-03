# -*- coding: utf-8 -*-
"""
细粒度问答意图标签与路由策略（与 classify_query_intent / QueryPlanner 对齐）。
"""
from __future__ import annotations

from typing import Final, Literal, Tuple

# 细粒度意图（API 响应 data.intent 可为下列之一）
INTENT_KG_QUERY: Final = "kg_query"
INTENT_GENERAL: Final = "general"
INTENT_OPEN_DOMAIN: Final = "open_domain"  # 开放域事实查询：历史、科学、时事等
INTENT_PLATFORM_HELP: Final = "platform_help"
INTENT_KG_BUILD: Final = "kg_build"
INTENT_DATA_IMPORT: Final = "data_import"
INTENT_PROJECT_MGMT: Final = "project_mgmt"
INTENT_TOOL_CALL: Final = "tool_call"

FINE_INTENTS: Final[frozenset[str]] = frozenset(
    {
        INTENT_KG_QUERY,
        INTENT_GENERAL,
        INTENT_OPEN_DOMAIN,
        INTENT_PLATFORM_HELP,
        INTENT_KG_BUILD,
        INTENT_DATA_IMPORT,
        INTENT_PROJECT_MGMT,
        INTENT_TOOL_CALL,
    }
)

# 兼容旧版「粗粒度」标签（日志与个别分支）
LEGACY_KG: Final = "kg"
LEGACY_GENERAL: Final = "general"

Strategy = Literal["use_kg_tools", "use_general", "use_platform_guidance"]


def normalize_legacy_intent_label(intent: str) -> str:
    """将旧响应中的 kg 映射为 kg_query（若未知则原样返回）。"""
    if intent == LEGACY_KG:
        return INTENT_KG_QUERY
    return intent


def intent_to_strategy(intent: str) -> Strategy:
    """细粒度意图 → Planner 策略。"""
    if intent in (INTENT_GENERAL, INTENT_OPEN_DOMAIN):
        return "use_general"
    if intent == INTENT_KG_QUERY:
        return "use_kg_tools"
    return "use_platform_guidance"


def coerce_manual_intent_mode(intent_mode: str) -> str:
    """HTTP 请求 intent_mode（auto/kg/general）→ 细粒度锚点意图。"""
    m = str(intent_mode or "auto").strip().lower()
    if m == LEGACY_KG:
        return INTENT_KG_QUERY
    if m == LEGACY_GENERAL:
        return INTENT_GENERAL
    return m


def fine_intent_to_legacy_tuple(intent: str) -> Tuple[str, Strategy]:
    """
    返回 (对外 legacy 桶, strategy)。
    legacy 桶仅两档：general / kg / platform（platform 表示非检索类平台引导）。
    """
    strategy = intent_to_strategy(intent)
    if strategy == "use_general":
        return LEGACY_GENERAL, strategy
    if strategy == "use_kg_tools":
        return LEGACY_KG, strategy
    return "platform", strategy
