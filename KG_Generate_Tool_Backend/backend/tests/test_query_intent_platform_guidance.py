# -*- coding: utf-8 -*-
import unittest

try:
    from agents.intent_taxonomy import (
        INTENT_DATA_IMPORT,
        INTENT_KG_BUILD,
        INTENT_PLATFORM_HELP,
        INTENT_PROJECT_MGMT,
        INTENT_TOOL_CALL,
        intent_to_strategy,
    )
    from agents.query_capability_agent import classify_query_intent
except ImportError:
    classify_query_intent = None
    intent_to_strategy = None
    INTENT_PLATFORM_HELP = None
    INTENT_KG_BUILD = None
    INTENT_DATA_IMPORT = None
    INTENT_PROJECT_MGMT = None
    INTENT_TOOL_CALL = None


def _fake_llm(**kwargs):
    return "意图: general | 置信度: 0.5 | 理由: fallback"


class TestPlatformGuidanceIntentRouting(unittest.TestCase):
    @unittest.skipIf(classify_query_intent is None, "缺少 query_capability_agent 依赖")
    def test_admin_graph_management_routes_to_platform_help(self):
        self.assertEqual(
            classify_query_intent("作为管理员我如何管理图谱", call_chat_completion_fn=_fake_llm, use_cache=False),
            INTENT_PLATFORM_HELP,
        )

    @unittest.skipIf(classify_query_intent is None, "缺少 query_capability_agent 依赖")
    def test_build_import_project_and_tool_queries_keep_platform_intents(self):
        cases = {
            "怎么构建知识图谱": INTENT_KG_BUILD,
            "如何查看图谱质量报告": INTENT_KG_BUILD,
            "图谱质量报告有什么内容": INTENT_KG_BUILD,
            "如何查看图谱质量构建报告，这个报告里面有什么内容": INTENT_KG_BUILD,
            "怎么导入样本": INTENT_DATA_IMPORT,
            "怎么新建项目": INTENT_PROJECT_MGMT,
            "调用接口同步数据": INTENT_TOOL_CALL,
        }
        for query, expected in cases.items():
            with self.subTest(query=query):
                self.assertEqual(
                    classify_query_intent(query, call_chat_completion_fn=_fake_llm, use_cache=False),
                    expected,
                )

    @unittest.skipIf(intent_to_strategy is None, "缺少 intent_taxonomy 依赖")
    def test_platform_guidance_intents_share_platform_strategy(self):
        intents = [
            INTENT_PLATFORM_HELP,
            INTENT_KG_BUILD,
            INTENT_DATA_IMPORT,
            INTENT_PROJECT_MGMT,
            INTENT_TOOL_CALL,
        ]
        for intent in intents:
            with self.subTest(intent=intent):
                self.assertEqual(intent_to_strategy(intent), "use_platform_guidance")