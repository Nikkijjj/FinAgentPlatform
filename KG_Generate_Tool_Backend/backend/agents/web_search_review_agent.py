# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

import requests


_GENERIC_PORTAL_HOSTS = frozenset(
    {
        "finance.yahoo.com",
        "www.finance.yahoo.com",
        "www.yahoo.com",
        "yahoo.com",
        "www.marketwatch.com",
        "marketwatch.com",
        "www.investing.com",
        "investing.com",
    }
)

_TRUSTED_FINANCE_HOSTS = frozenset(
    {
        "finance.eastmoney.com",
        "so.eastmoney.com",
        "guba.eastmoney.com",
        "caifuhao.eastmoney.com",
        "www.cls.cn",
        "cls.cn",
        "finance.sina.com.cn",
        "stock.jrj.com.cn",
        "www.cnstock.com",
        "finance.ifeng.com",
        "stock.10jqka.com.cn",
        "www.stcn.com",
        "stock.caijing.com.cn",
        "www.yicai.com",
        "finance.qq.com",
        "xueqiu.com",
        "www.xueqiu.com",
    }
)

_PREFERRED_FINANCE_COMMUNITY_HOSTS = frozenset(
    {
        "guba.eastmoney.com",
        "caifuhao.eastmoney.com",
        "xueqiu.com",
        "www.xueqiu.com",
    }
)

_FINANCE_MARKET_QUERY_HINTS = (
    "金融市场",
    "金融",
    "财经",
    "股票",
    "股市",
    "股价",
    "个股",
    "a股",
    "港股",
    "美股",
    "大盘",
    "指数",
    "证券",
    "行情",
    "涨跌",
)

_GENERIC_PORTAL_TITLE_HINTS = (
    "stock market live",
    "business & finance news",
    "quotes",
    "markets today",
    "latest news",
)

_RECENCY_HINTS = (
    "recent",
    "latest",
    "today",
    "this week",
    "this month",
    "近一周",
    "近一个月",
    "近期",
    "最近",
    "今日",
    "今天",
    "最新",
    "现在",
    "目前",
)

_SECTOR_HINTS = (
    "sector",
    "industry",
    "index",
    "stocks",
    "shares",
    "板块",
    "行业",
    "指数",
)

_FINANCE_HINTS = (
    "stock",
    "stocks",
    "share",
    "shares",
    "price",
    "quote",
    "market",
    "行情",
    "股价",
    "涨跌",
    "走势",
)

_QUERY_TOPIC_ALIASES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("半导体", ("chip", "chips", "sox", "philadelphia semiconductor index", "semiconductor sector")),
    ("芯片", ("chip", "chips", "sox", "semiconductor")),
    ("乌克兰", ("ukraine", "kyiv", "zelensky")),
    ("板块", ("sector", "industry", "theme", "segment")),
    ("行业", ("industry", "sector", "segment")),
    ("龙头", ("leader", "market leader", "bellwether", "top gainer")),
    ("龙头股", ("leader", "market leader", "bellwether", "top gainer")),
    ("领涨", ("top gainer", "leading gainers", "outperform")),
    ("领跌", ("top loser", "laggard", "underperform")),
    ("异动", ("unusual move", "momentum", "surge", "slump")),
)

_SEMANTIC_INTENT_GROUPS: Tuple[Tuple[Tuple[str, ...], Tuple[str, ...]], ...] = (
    (("股价", "行情", "走势", "涨跌"), ("stock", "stocks", "share", "shares", "price", "quote", "market", "trading")),
    (("板块", "行业", "指数"), ("sector", "industry", "index", "etf", "composite")),
    (("龙头", "龙头股", "领涨", "领跌"), ("leader", "market leader", "bellwether", "top gainer", "top loser", "laggard", "outperform", "underperform")),
    (("异动", "主线", "热点"), ("unusual move", "momentum", "surge", "slump", "market theme", "main theme", "hot theme")),
    (("财报", "业绩"), ("earnings", "results", "revenue", "guidance", "quarterly", "annual")),
    (("新闻", "事件", "动态", "近期"), ("news", "headline", "update", "development", "latest")),
    (("半导体", "芯片", "集成电路"), ("semiconductor", "chip", "chips", "sox", "wafer", "fab", "ic")),
    (("新能源", "锂电池"), ("ev", "battery", "lithium", "renewable")),
    (("出口", "进口", "贸易"), ("export", "import", "trade", "customs")),
    (("石油", "炼化", "加工贸易"), ("oil", "petrochemical", "refining", "refiner", "crude", "energy")),
)


def _host_and_path(url: str) -> Tuple[str, str]:
    try:
        parsed = urlparse(str(url or ""))
        return (parsed.netloc or "").strip().lower(), (parsed.path or "").strip()
    except Exception:
        return "", ""


def _contains_token(blob: str, blob_l: str, token: str) -> bool:
    t = str(token or "").strip()
    if len(t) < 2:
        return False
    if t.isascii():
        return t.lower() in blob_l
    return t in blob


def _title_hits(title: str, title_l: str, tokens: Sequence[str]) -> int:
    return sum(1 for token in tokens if _contains_token(title, title_l, token))


def _semantic_alias_tokens(user_query: str) -> List[str]:
    q = str(user_query or "")
    out: List[str] = []
    seen = set()
    for zh_group, alias_group in _SEMANTIC_INTENT_GROUPS:
        if not any(needle in q for needle in zh_group):
            continue
        for token in alias_group:
            t = str(token).strip().lower()
            if len(t) >= 2 and t not in seen:
                seen.add(t)
                out.append(t)
    return out


def _semantic_score_row(
    row: Dict[str, str],
    user_query: str,
    rel_tokens: Sequence[str],
    required_topics: Sequence[str],
) -> Tuple[float, Dict[str, Any]]:
    title = str(row.get("title") or "")
    body = str(row.get("body") or "")
    href = str(row.get("href") or row.get("url") or "")
    blob = f"{title}\n{body}\n{href}"
    blob_l = blob.lower()
    title_l = title.lower()
    host, path = _host_and_path(href)
    semantic_tokens = _semantic_alias_tokens(user_query)
    finance_market_query = any(x in str(user_query or "") for x in _FINANCE_MARKET_QUERY_HINTS)

    topic_hits = sum(1 for token in required_topics if _contains_token(blob, blob_l, token))
    rel_hits = sum(1 for token in rel_tokens if _contains_token(blob, blob_l, token))
    semantic_hits = sum(1 for token in semantic_tokens if _contains_token(blob, blob_l, token))
    finance_hits = sum(1 for token in _FINANCE_HINTS if _contains_token(blob, blob_l, token))
    recency_hits = sum(1 for token in _RECENCY_HINTS if _contains_token(blob, blob_l, token))
    sector_hits = sum(1 for token in _SECTOR_HINTS if _contains_token(blob, blob_l, token))
    title_topic_hits = _title_hits(title, title_l, required_topics)
    title_rel_hits = _title_hits(title, title_l, rel_tokens)
    title_semantic_hits = _title_hits(title, title_l, semantic_tokens)

    score = 0.0
    score += topic_hits * 8.0
    score += semantic_hits * 4.0
    score += rel_hits * 2.0
    score += title_topic_hits * 5.0
    score += title_semantic_hits * 4.0
    score += title_rel_hits * 2.0
    score += min(finance_hits, 3) * 2.0
    if host in _TRUSTED_FINANCE_HOSTS:
        score += 5.0
        if path and path not in ("", "/"):
            score += 3.0
    if finance_market_query and host in _PREFERRED_FINANCE_COMMUNITY_HOSTS:
        score += 8.0

    if any(x in str(user_query or "") for x in ("最近", "近期", "最新", "本周", "近一周", "近一个月", "今日", "今天", "现在", "目前")):
        score += min(recency_hits, 2) * 3.0
    if any(x in str(user_query or "") for x in ("板块", "行业", "指数", "股价", "行情", "走势", "涨跌")):
        score += min(sector_hits, 3) * 3.0

    if host in _GENERIC_PORTAL_HOSTS and path in ("", "/"):
        score -= 6.0
    if finance_market_query and host and host not in _TRUSTED_FINANCE_HOSTS and host not in _GENERIC_PORTAL_HOSTS:
        score -= 8.0
    if any(h in title_l for h in _GENERIC_PORTAL_TITLE_HINTS):
        score -= 4.0
    if path in ("", "/"):
        score -= 1.5
    if len(title.strip()) <= 8:
        score -= 1.0

    return score, {
        "host": host,
        "path": path,
        "topic_hits": topic_hits,
        "semantic_hits": semantic_hits,
        "rel_hits": rel_hits,
        "finance_hits": finance_hits,
        "recency_hits": recency_hits,
        "sector_hits": sector_hits,
        "title_topic_hits": title_topic_hits,
        "title_semantic_hits": title_semantic_hits,
        "title_rel_hits": title_rel_hits,
        "trusted_finance_host": host in _TRUSTED_FINANCE_HOSTS,
        "preferred_finance_community_host": host in _PREFERRED_FINANCE_COMMUNITY_HOSTS,
        "score": round(score, 3),
    }


def _extract_json_object(text: str) -> Dict[str, Any]:
    s = str(text or "").strip()
    if not s:
        return {}
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", s)
    if not m:
        return {}
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _llm_rerank_candidates(
    user_query: str,
    rows: List[Dict[str, str]],
    max_results: int,
) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    sw = (os.getenv("KG_WEB_SEARCH_LLM_RERANK") or "true").strip().lower()
    if sw in ("0", "false", "no", "off"):
        return [], {"llm_rerank_used": False, "llm_rerank_reason": "disabled"}

    api_key = (os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return [], {"llm_rerank_used": False, "llm_rerank_reason": "missing_api_key"}

    top_n = max(2, min(len(rows or []), int(os.getenv("KG_WEB_SEARCH_LLM_RERANK_TOP_N", "6") or 6)))
    if top_n <= 0:
        return [], {"llm_rerank_used": False, "llm_rerank_reason": "no_candidates"}

    candidates = []
    for idx, row in enumerate((rows or [])[:top_n], start=1):
        candidates.append(
            {
                "id": idx,
                "title": str(row.get("title") or "")[:160],
                "url": str(row.get("href") or row.get("url") or "")[:240],
                "body": str(row.get("body") or "")[:280],
            }
        )

    payload = {
        "model": os.getenv("KG_WEB_SEARCH_LLM_RERANK_MODEL", "deepseek-chat"),
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是金融联网检索重排器。"
                    "请从候选网页中选出最能帮助回答用户问题的条目，优先考虑主题相关、财经语境、时效性、标题信息量和具体页面而非站点首页。"
                    "只返回 JSON 对象，格式为 {\"selected_ids\":[1,2],\"reason\":\"...\"}。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "query": user_query,
                        "max_results": max_results,
                        "candidates": candidates,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    timeout_s = max(8, int(os.getenv("KG_WEB_SEARCH_LLM_RERANK_TIMEOUT_SECONDS", "20") or 20))
    base_url = (os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com").rstrip("/")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout_s,
        )
        resp.raise_for_status()
        data = resp.json() or {}
        content = str((((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "")).strip()
        obj = _extract_json_object(content)
        selected_ids = obj.get("selected_ids") if isinstance(obj, dict) else []
        if not isinstance(selected_ids, list):
            selected_ids = []
        chosen: List[Dict[str, str]] = []
        seen = set()
        for raw in selected_ids:
            try:
                idx = int(raw)
            except Exception:
                continue
            if idx < 1 or idx > len(candidates) or idx in seen:
                continue
            seen.add(idx)
            chosen.append(rows[idx - 1])
            if len(chosen) >= max(1, max_results):
                break
        return chosen, {
            "llm_rerank_used": True,
            "llm_rerank_reason": "ok",
            "llm_rerank_candidates": len(candidates),
            "llm_rerank_selected": len(chosen),
            "llm_rerank_model": payload["model"],
            "llm_rerank_response": obj,
        }
    except Exception as exc:
        return [], {
            "llm_rerank_used": False,
            "llm_rerank_reason": f"error:{str(exc)[:120]}",
            "llm_rerank_candidates": len(candidates),
        }


def review_web_search_rows(
    rows: List[Dict[str, str]],
    user_query: str,
    *,
    required_topic_tokens: Optional[Sequence[str]] = None,
    relevance_tokens: Optional[Sequence[str]] = None,
    max_results: int = 2,
) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    """Second-pass semantic rerank for web search rows after lexical ranking."""
    q = str(user_query or "")
    required_topics = [str(x).strip() for x in (required_topic_tokens or []) if str(x).strip()]
    required_seen = set(required_topics)
    for needle, aliases in _QUERY_TOPIC_ALIASES:
        if needle not in q:
            continue
        for alias in aliases:
            token = str(alias).strip().lower()
            if len(token) >= 2 and token not in required_seen:
                required_seen.add(token)
                required_topics.append(token)
    rel_tokens = [str(x).strip() for x in (relevance_tokens or []) if str(x).strip()]
    ranked: List[Tuple[float, Dict[str, str], Dict[str, Any]]] = []
    skipped = 0

    for row in rows or []:
        href = str(row.get("href") or row.get("url") or "")
        if not href and not str(row.get("title") or "").strip() and not str(row.get("body") or "").strip():
            skipped += 1
            continue
        score, detail = _semantic_score_row(row, q, rel_tokens, required_topics)
        ranked.append((score, row, detail))

    ranked.sort(
        key=lambda item: (
            -item[0],
            -(item[2].get("topic_hits") or 0),
            -(item[2].get("semantic_hits") or 0),
            -(item[2].get("sector_hits") or 0),
        )
    )

    semantic_cap = max(1, min(int(max_results or 2), 8))
    semantic_kept = [row for _, row, _ in ranked[:semantic_cap]]
    llm_rows, llm_meta = _llm_rerank_candidates(q, semantic_kept, semantic_cap)
    kept = llm_rows if llm_rows else semantic_kept
    meta: Dict[str, Any] = {
        "review_agent_used": True,
        "review_agent_candidates": len(rows or []),
        "review_agent_ranked": len(ranked),
        "review_agent_skipped": skipped,
        "review_agent_selected": len(kept),
        "review_agent_details": [detail for _, _, detail in ranked[:5]],
        "review_agent_strategy": "semantic_rerank",
    }
    meta.update(llm_meta)
    return kept, meta