# -*- coding: utf-8 -*-
"""轻量自动化测试：共现占位边过滤、检索属性黑名单。"""
import os
import unittest
from unittest import mock

try:
    from routes.llmGenKG_api import (
        _finalize_master_build_payload,
        _master_build_should_snapshot_project_db,
        _should_drop_placeholder_cooccurrence_edge,
    )
except ImportError:
    _finalize_master_build_payload = None
    _master_build_should_snapshot_project_db = None
    _should_drop_placeholder_cooccurrence_edge = None

try:
    from routes.askAI_api import (
        _appendix_evidence_preprocess,
        _build_retrieval_query,
        _merge_retrieval_tokens,
        _qa_skip_prop_keys,
    )
except ImportError:
    _appendix_evidence_preprocess = None
    _build_retrieval_query = None
    _merge_retrieval_tokens = None
    _qa_skip_prop_keys = None

try:
    from agents.constrained_web_search import (
        _salvage_web_rows_when_overfiltered,
        _dynamic_web_topk,
        _relevance_tokens_expanded,
        filter_ddgs_rows_by_user_query,
        merge_kg_and_web_evidence,
    )
except ImportError:
    _salvage_web_rows_when_overfiltered = None
    _dynamic_web_topk = None
    _relevance_tokens_expanded = None
    filter_ddgs_rows_by_user_query = None
    merge_kg_and_web_evidence = None

try:
    from agents.web_search_review_agent import review_web_search_rows
except ImportError:
    review_web_search_rows = None

try:
    from agents.graph_optimization_agent import optimize_graph_structure
except ImportError:
    optimize_graph_structure = None


class TestKgEdgePlaceholder(unittest.TestCase):
    @unittest.skipIf(_should_drop_placeholder_cooccurrence_edge is None, "缺少依赖，跳过 llmGenKG_api 导入")
    def test_drop_cooccurrence(self):
        os.environ.pop("KG_KEEP_COOC_EDGES", None)
        self.assertTrue(
            _should_drop_placeholder_cooccurrence_edge(
                {"type": "文本共现", "value": "同段共现"}
            )
        )
        self.assertFalse(
            _should_drop_placeholder_cooccurrence_edge(
                {"type": "股权关系", "value": "持股"}
            )
        )

    @unittest.skipIf(_should_drop_placeholder_cooccurrence_edge is None, "缺少依赖")
    def test_keep_cooc_when_env(self):
        os.environ["KG_KEEP_COOC_EDGES"] = "true"
        try:
            self.assertFalse(
                _should_drop_placeholder_cooccurrence_edge(
                    {"type": "文本共现", "value": "同段共现"}
                )
            )
        finally:
            os.environ.pop("KG_KEEP_COOC_EDGES", None)


class TestWebEvidenceMerge(unittest.TestCase):
    @unittest.skipIf(merge_kg_and_web_evidence is None, "缺少 constrained_web_search 导入")
    def test_merge_preserves_reserved_web_slots(self):
        kg_list = [{"source": "kg", "id": f"kg{i}"} for i in range(10)]
        web_list = [{"source": "constrained_web", "id": f"web{i}"} for i in range(4)]
        merged = merge_kg_and_web_evidence(kg_list, web_list, max_total=14)
        self.assertEqual(len(merged), 14)
        self.assertEqual(sum(1 for item in merged if item.get("source") == "constrained_web"), 4)
        self.assertTrue(any(item.get("id") == "web0" for item in merged[:6]))
        self.assertTrue(any(item.get("id") == "web3" for item in merged[:14]))

    @unittest.skipIf(merge_kg_and_web_evidence is None, "缺少 constrained_web_search 导入")
    def test_merge_only_web_or_only_kg(self):
        kg_list = [{"source": "kg", "id": "kg0"}]
        web_list = [{"source": "constrained_web", "id": "web0"}]
        self.assertEqual(merge_kg_and_web_evidence(kg_list, [], max_total=1), kg_list)
        self.assertEqual(merge_kg_and_web_evidence([], web_list, max_total=1), web_list)


class TestMasterBuildFinalization(unittest.TestCase):
    @unittest.skipIf(_master_build_should_snapshot_project_db is None, "缺少 llmGenKG_api 依赖")
    def test_incremental_or_merge_uses_project_snapshot(self):
        self.assertTrue(_master_build_should_snapshot_project_db({"mode": "incremental"}))
        self.assertTrue(_master_build_should_snapshot_project_db({"persistence_mode": "merge"}))
        self.assertFalse(
            _master_build_should_snapshot_project_db({"mode": "full", "persistence_mode": "replace"})
        )

    @unittest.skipIf(_finalize_master_build_payload is None, "缺少 llmGenKG_api 依赖")
    def test_incremental_final_payload_prefers_project_snapshot(self):
        snapshot_payload = {
            "samples": [{"_id": "all-1"}],
            "nodes": [{"id": "full-node"}],
            "edges": [{"id": "full-edge"}],
            "conflicts": [{"id": "full-conflict"}],
            "graph": {"nodes": [{"id": "full-node"}], "links": [{"id": "full-edge"}]},
            "workflow_meta": {"conflict_count": 1},
            "incremental_impact_before_build": None,
        }
        with mock.patch("routes.llmGenKG_api.build_master_snapshot_payload_from_project_db", return_value=snapshot_payload) as mocked:
            payload = _finalize_master_build_payload(
                "p1",
                ["s1", "s2"],
                run_id_hint="run-1",
                build_plan={"mode": "incremental", "persistence_mode": "merge"},
                graph_enrichment={"quality_score": 0.91, "quality_report": "ok"},
                needs_stale_cleanup=False,
                incremental_impact_before_build={"changed": True},
                samples_override=[{"_id": "partial"}],
                nodes=[{"id": "partial-node"}],
                edges=[{"id": "partial-edge"}],
                conflicts=[],
                graph={"nodes": [], "links": []},
            )

        mocked.assert_called_once()
        self.assertEqual(payload["nodes"], snapshot_payload["nodes"])
        self.assertEqual(payload["edges"], snapshot_payload["edges"])
        self.assertEqual(payload["samples"], snapshot_payload["samples"])
        self.assertEqual(payload["workflow_meta"]["run_id"], "run-1")
        self.assertEqual(payload["workflow_meta"]["build_plan"]["mode"], "incremental")
        self.assertEqual(payload["workflow_meta"]["quality_score"], 0.91)
        self.assertEqual(payload["incremental_impact_before_build"], {"changed": True})

    @unittest.skipIf(_finalize_master_build_payload is None, "缺少 llmGenKG_api 依赖")
    def test_full_replace_final_payload_keeps_direct_graph(self):
        payload = _finalize_master_build_payload(
            "p1",
            ["s1"],
            run_id_hint="run-2",
            build_plan={"mode": "full", "persistence_mode": "replace"},
            graph_enrichment=None,
            needs_stale_cleanup=True,
            samples_override=[{"_id": "s1"}],
            nodes=[{"id": "direct-node"}],
            edges=[{"id": "direct-edge"}],
            conflicts=[{"id": "direct-conflict"}],
            graph={"nodes": [{"id": "direct-node"}], "links": [{"id": "direct-edge"}]},
        )

        self.assertEqual(payload["nodes"], [{"id": "direct-node"}])
        self.assertEqual(payload["edges"], [{"id": "direct-edge"}])
        self.assertEqual(payload["workflow_meta"]["conflict_count"], 1)
        self.assertTrue(payload["workflow_meta"]["needs_stale_cleanup"])


class TestRetrievalTokenMerge(unittest.TestCase):
    @unittest.skipIf(_merge_retrieval_tokens is None, "缺少 askAI_api 依赖")
    def test_cjk_gram_includes_entity_despite_long_history(self):
        """长会话中历史分词很多时，仍须从【当前问题】锚点拆出「乌克兰」等实体以命中 Neo4j CONTAINS。"""
        long_hist = "用户：半导体出口\n助手：增长\n" * 15
        q = f"{long_hist}\n\n【当前问题】\n最近乌克兰的地缘政治情况"
        _a, toks = _merge_retrieval_tokens(q, max_tokens=20)
        self.assertIn("乌克兰", toks, f"tokens={toks!r}")

    @unittest.skipIf(_merge_retrieval_tokens is None, "缺少 askAI_api 依赖")
    def test_cjk_gram_for_unpunctuated_question(self):
        q = "请介绍乌克兰经济"
        _a, toks = _merge_retrieval_tokens(q, max_tokens=20)
        self.assertIn("乌克兰", toks)

    @unittest.skipIf(_merge_retrieval_tokens is None, "缺少 askAI_api 依赖")
    def test_geo_conflict_topic_injects_entity_tokens(self):
        q = "【当前问题】\n俄乌战争什么时候开始的"
        _a, toks = _merge_retrieval_tokens(q, max_tokens=20)
        self.assertIn("乌克兰", toks)
        self.assertIn("俄罗斯", toks)

    @unittest.skipIf(
        _build_retrieval_query is None or _merge_retrieval_tokens is None,
        "缺少 askAI_api 依赖",
    )
    def test_deictic_followup_inherits_latest_topic(self):
        prior = [
            {"role": "user", "content": "汽车行业的情况"},
            {"role": "assistant", "content": "这里是关于汽车行业的回答摘要"},
        ]
        combined = _build_retrieval_query("分析一下这个行业情况", prior)
        anchor, toks = _merge_retrieval_tokens(combined, max_tokens=20)
        self.assertIn("汽车行业", anchor)
        joined = " ".join(toks)
        self.assertIn("汽车", joined)


class TestSkipPropKeys(unittest.TestCase):
    @unittest.skipIf(_qa_skip_prop_keys is None, "缺少依赖，跳过 askAI_api 导入")
    def test_default_skip_keys(self):
        ks = _qa_skip_prop_keys()
        self.assertIn("embedding", ks)


class TestAppendixEvidencePreprocess(unittest.TestCase):
    @unittest.skipIf(_appendix_evidence_preprocess is None, "缺少 askAI_api 依赖")
    def test_balances_projects_for_appendix_slice(self):
        evidence = []
        for pid in ("p1", "p2", "p3"):
            for idx in range(6):
                evidence.append(
                    {
                        "project_id": pid,
                        "project_name": pid,
                        "score": 1.0,
                        "source": "neo4j_context_match",
                        "snippet": f"{pid}-snippet-{idx}",
                    }
                )

        appendix = _appendix_evidence_preprocess(evidence, max_total=6)
        appendix_projects = [str(item.get("project_id")) for item in appendix]

        self.assertEqual(len(appendix), 6)
        self.assertEqual(set(appendix_projects[:3]), {"p1", "p2", "p3"})
        self.assertGreaterEqual(len(set(appendix_projects)), 3)


class TestWebResultRelevanceFilter(unittest.TestCase):
    @unittest.skipIf(filter_ddgs_rows_by_user_query is None, "缺少模块")
    def test_ranks_irrelevant_row_but_keeps_candidate(self):
        rows = [
            {
                "title": "MX Player - Apps on Google Play",
                "body": "Video player app download",
                "href": "https://example.com/mx",
            }
        ]
        kept, dropped, meta = filter_ddgs_rows_by_user_query(
            rows, "一季度高新技术产品出口里半导体表现如何"
        )
        self.assertEqual(dropped, 0)
        self.assertEqual(len(kept), 1)
        self.assertEqual(meta.get("web_rank_mode"), "score_only")

    @unittest.skipIf(_relevance_tokens_expanded is None, "缺少模块")
    def test_injects_topic_when_long_chinese_chunked(self):
        q = "一季度高新技术产品出口里半导体表现如何"
        toks = _relevance_tokens_expanded(q)
        self.assertIn("半导体", toks)
        self.assertIn("semiconductor", toks)
        self.assertIn("高新技术", toks)

    @unittest.skipIf(_relevance_tokens_expanded is None, "缺少模块")
    def test_injects_sector_leader_aliases(self):
        q = "石油加工贸易板块龙头股异动情况"
        toks = _relevance_tokens_expanded(q)
        self.assertIn("sector", toks)
        self.assertIn("leader", toks)
        self.assertIn("momentum", toks)

    @unittest.skipIf(filter_ddgs_rows_by_user_query is None, "缺少模块")
    def test_keeps_semiconductor_hit(self):
        rows = [
            {
                "title": "半导体出口额同比增长",
                "body": "海关数据显示集成电路出口…",
                "href": "https://example.com/a",
            }
        ]
        kept, dropped, _ = filter_ddgs_rows_by_user_query(rows, "半导体 出口 高新技术")
        self.assertEqual(dropped, 0)
        self.assertEqual(len(kept), 1)

    @unittest.skipIf(_dynamic_web_topk is None, "缺少模块")
    def test_dynamic_topk_widens_broad_query(self):
        self.assertGreaterEqual(_dynamic_web_topk("石油板块最近怎么样"), 6)

    @unittest.skipIf(_dynamic_web_topk is None, "缺少模块")
    def test_dynamic_topk_stays_tighter_for_specific_query(self):
        self.assertLessEqual(_dynamic_web_topk("600688 渤海化学 近期股价表现"), 5)

    @unittest.skipIf(filter_ddgs_rows_by_user_query is None, "缺少模块")
    def test_prefers_trusted_finance_host_in_lexical_rank(self):
        rows = [
            {
                "title": "石油加工贸易板块领涨股渤海化学涨近10%",
                "body": "板块整体回落，但龙头股渤海化学逆势走强。",
                "href": "https://example.com/blog/oil-sector",
            },
            {
                "title": "石油加工贸易板块领涨股渤海化学涨近10%",
                "body": "板块整体回落，但龙头股渤海化学逆势走强。",
                "href": "https://finance.eastmoney.com/a/202604223.html",
            },
        ]
        kept, dropped, _ = filter_ddgs_rows_by_user_query(rows, "石油加工贸易板块龙头股异动")
        self.assertEqual(dropped, 0)
        self.assertEqual(kept[0]["href"], "https://finance.eastmoney.com/a/202604223.html")

    @unittest.skipIf(filter_ddgs_rows_by_user_query is None, "缺少模块")
    def test_finance_market_query_filters_non_finance_hosts(self):
        rows = [
            {
                "title": "某股票股价异动，资金博弈加剧",
                "body": "这是一个泛站点页面，但没有财经站点来源。",
                "href": "https://example.com/posts/stock-move",
            },
            {
                "title": "东方财富股吧：某股票股价异动，市场热议",
                "body": "股吧用户围绕该股票行情、成交量与资金面展开讨论。",
                "href": "https://guba.eastmoney.com/news,600000,123456.html",
            },
        ]
        kept, dropped, meta = filter_ddgs_rows_by_user_query(rows, "这只股票股价为什么突然上涨")
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["href"], "https://guba.eastmoney.com/news,600000,123456.html")
        self.assertTrue(meta.get("web_finance_market_query"))
        self.assertGreaterEqual(dropped, 1)

    @unittest.skipIf(_salvage_web_rows_when_overfiltered is None, "缺少模块")
    def test_salvages_trusted_finance_rows_when_overfiltered(self):
        rows = [
            {
                "title": "普通转载页提到某股票异动",
                "body": "泛站点内容，相关性一般。",
                "href": "https://example.com/stock-jump",
            },
            {
                "title": "东方财富股吧：某股票盘中异动，资金分歧加大",
                "body": "股吧帖子讨论股价、换手率、主力资金与市场分歧。",
                "href": "https://guba.eastmoney.com/news,600000,123456.html",
            },
        ]
        kept, meta = _salvage_web_rows_when_overfiltered(rows, "这只股票股价为什么突然上涨", 3)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["href"], "https://guba.eastmoney.com/news,600000,123456.html")
        self.assertTrue(meta.get("web_salvage_used"))
        self.assertEqual(meta.get("web_salvage_mode"), "trusted_finance_rows")

    @unittest.skipIf(review_web_search_rows is None, "缺少模块")
    def test_review_agent_prefers_trusted_finance_host(self):
        rows = [
            {
                "title": "Oil refining sector bellwether rallies as peers fall",
                "body": "The refining segment weakened broadly, but Bohai Chemical surged as the sector leader.",
                "href": "https://example.com/market-note",
            },
            {
                "title": "Oil refining sector bellwether rallies as peers fall",
                "body": "The refining segment weakened broadly, but Bohai Chemical surged as the sector leader.",
                "href": "https://www.cls.cn/detail/2000011",
            },
        ]
        kept, meta = review_web_search_rows(
            rows,
            "石油加工贸易板块龙头股异动",
            required_topic_tokens=["石油", "板块", "龙头"],
            relevance_tokens=["oil", "refining", "sector", "leader", "momentum"],
            max_results=1,
        )
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["href"], "https://www.cls.cn/detail/2000011")
        self.assertEqual(meta.get("review_agent_strategy"), "semantic_rerank")

    @unittest.skipIf(review_web_search_rows is None, "缺少模块")
    def test_review_agent_prefers_finance_community_post_for_stock_query(self):
        rows = [
            {
                "title": "某股票盘中异动，量价齐升",
                "body": "普通站点转载了一段关于股价上涨的简短描述。",
                "href": "https://example.com/repost/stock-jump",
            },
            {
                "title": "东方财富股吧：某股票盘中异动，资金分歧加大",
                "body": "股吧帖子讨论股价、换手率、主力资金与次日预期。",
                "href": "https://guba.eastmoney.com/news,600000,123456.html",
            },
        ]
        kept, meta = review_web_search_rows(
            rows,
            "某股票股价异动背后是什么原因",
            required_topic_tokens=["股票", "股价", "异动"],
            relevance_tokens=["股票", "股价", "异动", "stock", "price", "market"],
            max_results=1,
        )
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["href"], "https://guba.eastmoney.com/news,600000,123456.html")
        self.assertEqual(meta.get("review_agent_strategy"), "semantic_rerank")


class TestGraphOptimizationAgent(unittest.TestCase):
    @unittest.skipIf(optimize_graph_structure is None, "缺少 GraphOptimizationAgent 模块")
    def test_repair_isolated_nodes(self):
        nodes = [
            {
                "id": "n1",
                "type": "0",
                "value": "实体A",
                "properties": {"sample_id": "s1"},
            },
            {
                "id": "n2",
                "type": "1",
                "value": "事件B",
                "properties": {"sample_id": "s1"},
            },
        ]
        edges = []
        res = optimize_graph_structure("p1", nodes, edges, enable_isolated_repair=True)
        self.assertTrue(res.get("changed"))
        self.assertGreaterEqual(len(res.get("edges") or []), 1)
        report = res.get("report") or {}
        self.assertGreaterEqual(report.get("isolated_nodes_before", 0), 2)
        self.assertEqual(report.get("isolated_nodes_after", 0), 0)

    @unittest.skipIf(optimize_graph_structure is None, "缺少 GraphOptimizationAgent 模块")
    def test_drop_invalid_and_self_loop_edges(self):
        nodes = [
            {"id": "a", "type": "0", "value": "A", "properties": {"sample_id": "s"}},
            {"id": "b", "type": "1", "value": "B", "properties": {"sample_id": "s"}},
        ]
        edges = [
            {"id": "e1", "from": "a", "to": "a", "type": "语义关系", "value": "x"},
            {"id": "e2", "from": "a", "to": "z", "type": "语义关系", "value": "x"},
            {"id": "e3", "from": "a", "to": "b", "type": "语义关系", "value": "x", "properties": {"confidence": 0.2}},
            {"id": "e4", "from": "a", "to": "b", "type": "语义关系", "value": "x", "properties": {"confidence": 0.9}},
        ]
        res = optimize_graph_structure("p1", nodes, edges, enable_isolated_repair=False)
        kept = res.get("edges") or []
        self.assertEqual(len(kept), 1)
        self.assertEqual((kept[0].get("id") or ""), "e4")


if __name__ == "__main__":
    unittest.main()
