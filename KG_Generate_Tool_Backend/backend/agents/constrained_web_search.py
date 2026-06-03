# -*- coding: utf-8 -*-
"""
基于「项目已选抽取样本」锚定的联网检索：查询串仅由样本中出现的证券代码、标题用语，
以及用户问题中能在样本正文中找到的词组成，避免自由发挥导致幻觉检索。
"""
from __future__ import annotations

import json
import math
import os
import re
import traceback
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

try:
    from agents.web_search_review_agent import review_web_search_rows
except ImportError:
    from backend.agents.web_search_review_agent import review_web_search_rows


def _env_int(name: str, default: int) -> int:
    try:
        raw = os.getenv(name)
        if raw is None:
            return default
        return int(str(raw).strip())
    except Exception:
        return default


def _fetch_project_sample_ids(project_id: str) -> List[str]:
    from database import get_client

    pid = str(project_id or "").strip()
    if not pid:
        return []
    client = None
    try:
        client = get_client()
        with client.cursor() as cursor:
            cursor.execute(
                "SELECT data_list FROM finkg1.graph_project WHERE id = %s LIMIT 1",
                (pid,),
            )
            row = cursor.fetchone()
        if not row or not row.get("data_list"):
            return []
        raw = row["data_list"]
        if isinstance(raw, str):
            id_list = json.loads(raw) if raw.strip() else []
        elif isinstance(raw, list):
            id_list = raw
        else:
            id_list = []
        return [str(x) for x in id_list if x is not None and str(x).strip()]
    except Exception:
        traceback.print_exc()
        return []
    finally:
        if client:
            client.close()


def _fetch_project_stock_nums(project_id: str) -> List[str]:
    from database import get_client

    pid = str(project_id or "").strip()
    if not pid:
        return []
    client = None
    try:
        client = get_client()
        with client.cursor() as cursor:
            cursor.execute(
                "SELECT stock_num FROM finkg1.graph_project WHERE id = %s LIMIT 1",
                (pid,),
            )
            row = cursor.fetchone()
        if not row or row.get("stock_num") is None:
            return []
        raw = row["stock_num"]
        if isinstance(raw, str):
            try:
                arr = json.loads(raw) if raw.strip() else []
            except json.JSONDecodeError:
                arr = []
        elif isinstance(raw, list):
            arr = raw
        else:
            arr = []
        out = []
        for x in arr:
            s = str(x).strip()
            if s and s not in out:
                out.append(s)
        return out
    except Exception:
        traceback.print_exc()
        return []
    finally:
        if client:
            client.close()


def _mongo_samples(sample_ids: List[str]) -> List[Dict[str, Any]]:
    if not sample_ids:
        return []
    try:
        # 延迟导入，避免部分测试环境未装全依赖时阻塞模块加载
        from routes.llmGenKG_api import fetch_samples_from_mongo

        return fetch_samples_from_mongo(sample_ids) or []
    except Exception:
        traceback.print_exc()
        return []


def _anchor_corpus(samples: List[Dict[str, Any]], stock_nums: List[str]) -> str:
    parts = []
    for s in stock_nums:
        parts.append(str(s))
    for item in samples:
        parts.append(str(item.get("title") or ""))
        c = item.get("content") or ""
        parts.append(c[:1200])
        rd = item.get("raw_data") or {}
        if isinstance(rd, dict):
            for k in ("symbol", "stock_num", "证券代码", "股票代码"):
                v = rd.get(k)
                if v:
                    parts.append(str(v))
    return "\n".join(parts)


_RE_CODE = re.compile(r"\b(\d{6})\b")
_RE_WORD = re.compile(r"[\u4e00-\u9fa5]{2,14}|[A-Za-z][A-Za-z0-9]{1,15}")
_RE_SECTOR_PHRASE = re.compile(r"[\u4e00-\u9fa5]{2,12}(?:板块|行业)")
# 与用户问题做相关性过滤（剔除 DDG 噪声条目，如无关 App、娱乐站）
_RE_QUERY_TOK = re.compile(r"[\u4e00-\u9fa5]{2,14}|[A-Za-z]{3,24}|\d{6}")
_STOP_FILTER = frozenset(
    {
        "什么",
        "如何",
        "为什么",
        "是否",
        "怎么",
        "哪些",
        "这个",
        "可以",
        "能否",
        "有没有",
        "请问",
        "谢谢",
        "您好",
        "以下",
        "上述",
        "是否",
        "能否",
        "多少",
        "哪些",
        "哪个",
    }
)

_FINANCE_HINT_PAIRS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("金融市场", ("金融市场", "资本市场", "financial market", "capital market")),
    ("金融", ("金融", "财经", "finance", "financial")),
    ("股票", ("股票", "个股", "stock", "stocks", "equity", "equities")),
    ("股市", ("股市", "a股", "market", "stock market", "equity market")),
    ("股价", ("股价", "行情", "price", "stock price", "share price", "quote")),
    ("行情", ("行情", "走势", "market", "quote", "price")),
    ("板块", ("板块", "行业", "sector", "industry", "theme", "segment")),
    ("行业", ("行业", "板块", "sector", "industry", "segment")),
    ("龙头", ("龙头", "龙头股", "leader", "market leader", "bellwether", "top gainer")),
    ("龙头股", ("龙头股", "龙头", "leader", "market leader", "bellwether", "top gainer")),
    ("领涨", ("领涨", "领涨股", "top gainer", "leading gainers", "outperform")),
    ("领跌", ("领跌", "领跌股", "top loser", "laggard", "underperform")),
    ("异动", ("异动", "异动股", "unusual move", "momentum", "surge", "slump")),
    ("主线", ("主线", "main theme", "market theme", "investment theme")),
    ("市值", ("市值", "market cap", "valuation")),
    ("财报", ("财报", "earnings", "financial report")),
    ("业绩", ("业绩", "earnings", "results")),
    ("风险", ("风险", "risk", "exposure")),
    ("事件", ("事件", "news", "event", "development")),
    ("新闻", ("新闻", "news", "headline")),
    ("百科", ("百科", "baike", "wikipedia", "encyclopedia")),
)

_IRRELEVANT_RESULT_HOSTS = frozenset(
    {
        "qzone.qq.com",
        "qzs.qzone.qq.com",
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

_STRICT_FINANCE_HOSTS = frozenset(
    set(_TRUSTED_FINANCE_HOSTS)
    | {
        "quote.eastmoney.com",
        "emweb.securities.eastmoney.com",
        "data.eastmoney.com",
        "fund.eastmoney.com",
        "finance.stockstar.com",
        "stock.stockstar.com",
        "www.cs.com.cn",
        "cs.com.cn",
        "stock.hexun.com",
        "www.hexun.com",
    }
)

_FINANCE_MARKET_QUERY_KEYWORDS = (
    "金融市场",
    "金融",
    "财经",
    "资本市场",
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
    "k线",
    "市盈率",
    "市净率",
    "龙虎榜",
    "研报",
    "券商",
)

_FINANCE_SOURCE_HINTS = (
    "东方财富",
    "股吧",
    "雪球",
    "同花顺",
    "财联社",
    "新浪财经",
)

_IRRELEVANT_RESULT_HINTS = (
    "qq空间",
    "手机qq空间",
    "社交",
    "说说",
    "相册",
    "日志",
    "留言板",
    "空间下载",
    "app下载",
    "mobile html",
    "分享生活",
)


def _extract_sector_phrases(user_query: str) -> List[str]:
    """提取“xx板块/xx行业”短语，避免联网检索时只保留基词（如“石油”）。"""
    q = str(user_query or "")
    if not q:
        return []
    out: List[str] = []
    seen = set()
    for m in _RE_SECTOR_PHRASE.finditer(q):
        t = str(m.group(0) or "").strip()
        # 过滤过泛短语，保留“石油板块/半导体行业”等具体目标
        if len(t) < 4 or t in ("哪些板块", "什么板块", "哪个板块", "哪些行业", "什么行业", "哪个行业"):
            continue
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:6]


def _query_overlap_tokens(user_query: str) -> List[str]:
    """从用户/检索用语中提取可用于网页相关性过滤的词元。"""
    q = (user_query or "").strip()
    out: List[str] = []
    seen = set()
    # 优先保留“xx板块/xx行业”短语，确保检索意图不被弱化成“xx”。
    for t in _extract_sector_phrases(q):
        if t not in seen:
            seen.add(t)
            out.append(t)
    for m in _RE_QUERY_TOK.finditer(q):
        t = m.group(0).strip()
        t = re.sub(r"(怎么样|如何|怎么回事|怎么|吗|呢|呀|啊|吧|情况如何|情况怎么样)$", "", t).strip()
        if len(t) < 2 or t in _STOP_FILTER:
            continue
        if len(t) > 8 and any(x in t for x in ("怎么样", "如何", "怎么", "情况")):
            continue
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:18]


def _question_core_snippet(user_query: str, max_len: int = 72) -> str:
    q = re.sub(r"\s+", " ", str(user_query or "").strip())
    q = re.sub(r"^[请麻烦帮我想问一下告诉我了解一下介绍一下]+", "", q)
    q = re.sub(r"(怎么样|如何|怎么回事|怎么|吗|呢|呀|啊|吧|情况如何|情况怎么样)$", "", q)
    q = re.sub(r"(最近|近期|最新)(的)?", lambda m: m.group(0).replace("的", " "), q)
    q = re.sub(r"\s+", " ", q)
    q = q.strip()
    if len(q) > max_len:
        q = q[:max_len].rstrip()
    return q


def _unique_query_terms(user_query: str, max_terms: int = 6) -> List[str]:
    terms = _query_overlap_tokens(user_query)
    # 优先保留较长中文词和代码等“独特词”。
    terms.sort(key=lambda x: (-len(x), x))
    out: List[str] = []
    seen = set()
    for t in terms:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= max_terms:
            break
    return out


def _inject_finance_hints(user_query: str, seen: set, out: List[str]) -> None:
    q = str(user_query or "")
    for zh, hints in _FINANCE_HINT_PAIRS:
        if zh not in q:
            continue
        for hint in hints:
            s = str(hint).strip()
            if s and s not in seen:
                seen.add(s)
                out.append(s)


def _is_finance_market_query(user_query: str) -> bool:
    q = str(user_query or "")
    if not q:
        return False
    return any(token in q for token in _FINANCE_MARKET_QUERY_KEYWORDS)


def _inject_finance_source_hints(user_query: str, seen: set, out: List[str]) -> None:
    if not _is_finance_market_query(user_query):
        return
    for hint in _FINANCE_SOURCE_HINTS:
        s = str(hint).strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)


def _inject_search_intent_hints(user_query: str, seen: set, out: List[str]) -> None:
    q = str(user_query or "")
    topic_tokens = _required_topic_tokens(q)

    if any(x in q for x in ("最近", "近期", "最新", "本周", "近一周", "近一个月", "今日", "今天")):
        for hint in ("recent", "latest", "this week", "today"):
            if hint not in seen:
                seen.add(hint)
                out.append(hint)

    if topic_tokens and any(x in q for x in ("股价", "行情", "走势", "涨跌", "指数", "板块")):
        for hint in ("板块", "行业", "sector", "industry", "index", "stocks", "shares"):
            if hint not in seen:
                seen.add(hint)
                out.append(hint)
    _inject_finance_source_hints(q, seen, out)


def _anchor_matches_query(anchor: str, user_query: str) -> bool:
    s = str(anchor or "").strip()
    if not s:
        return False
    if _RE_CODE.search(s):
        return True
    required_topics = _required_topic_tokens(user_query)
    if required_topics:
        low = s.lower()
        for token in required_topics:
            if token.isascii():
                if token in low:
                    return True
            elif token in s:
                return True
        return False
    return True


def _compose_question_first_query_parts(
    user_query: str,
    anchor_parts: List[str],
    max_terms: int = 12,
) -> List[str]:
    parts: List[str] = []
    seen = set()

    core = _question_core_snippet(user_query)
    if core:
        seen.add(core)
        parts.append(core)

    for t in _unique_query_terms(user_query, max_terms=6):
        if t not in seen:
            seen.add(t)
            parts.append(t)

    _inject_search_intent_hints(user_query, seen, parts)
    _inject_finance_hints(user_query, seen, parts)

    for p in anchor_parts:
        s = str(p).strip()
        if s and s not in seen:
            seen.add(s)
            parts.append(s)
        if len(parts) >= max_terms:
            break
    return parts[:max_terms]


# 中文主题词 → 英文检索页常见写法（避免「仅有中文词」时英文摘要全被过滤）
_TOPIC_ZH_TO_EN: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("半导体", ("semiconductor", "semiconductors", "wafer", "silicon")),
    ("芯片", ("chip", "chips", "silicon")),
    ("集成电路", ("integrated circuit", "ic design")),
    ("新能源", ("renewable", "ev battery", "lithium")),
    ("锂电池", ("lithium battery", "battery")),
    ("石油", ("oil", "petroleum", "energy")),
    ("炼化", ("refining", "petrochemical", "refiner")),
    ("加工贸易", ("processing trade", "trade", "refining trade")),
    ("石油加工贸易", ("oil refining", "petrochemical", "refining trade")),
)
# 进出口 / 宏观表述常见英文摘要用词（问题里出现时再注入）
_TOPIC_TRADE_ZH_TO_EN: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("出口", ("export", "exports")),
    ("进口", ("import", "imports")),
    ("海关", ("customs")),
    ("贸易", ("trade")),
    ("高新技术", ("high-tech", "high tech", "technology")),
)
# 地缘冲突类：中英摘要用词（俄乌相关问题里英文网页多，避免过滤误杀）
_TOPIC_GEO_ZH_TO_EN: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("俄乌战争", ("russia", "ukraine", "invasion", "donbas")),
    ("俄乌冲突", ("russia", "ukraine", "donbas")),
    ("乌克兰战争", ("ukraine", "russia")),
    ("乌克兰", ("ukraine", "kyiv")),
)


def _inject_zh_en_pairs(
    q: str,
    pairs: Tuple[Tuple[str, Tuple[str, ...]], ...],
    seen: set,
    out: List[str],
) -> None:
    """若主题词出现在全文 q 中，则强制加入中文词（避免被下方正则长块切碎）并追加英文对照。"""
    for zh, ens in pairs:
        if zh not in q:
            continue
        if zh not in seen:
            seen.add(zh)
            out.append(zh)
        for en in ens:
            el = en.strip().lower()
            if len(el) >= 2 and el not in seen:
                seen.add(el)
                out.append(el)


def _relevance_tokens_expanded(user_query: str) -> List[str]:
    """在问题词元基础上扩展常见中英对照，减少 DDG 英文摘要被误杀。"""
    base = _query_overlap_tokens(user_query)
    seen = set(base)
    out = list(base)
    q = user_query or ""
    _inject_finance_hints(q, seen, out)
    _inject_zh_en_pairs(q, _TOPIC_ZH_TO_EN, seen, out)
    _inject_zh_en_pairs(q, _TOPIC_TRADE_ZH_TO_EN, seen, out)
    _inject_zh_en_pairs(q, _TOPIC_GEO_ZH_TO_EN, seen, out)
    return out[:40]


def _required_topic_tokens(user_query: str) -> List[str]:
    q = str(user_query or "")
    seen = set()
    out: List[str] = []

    for t in _extract_sector_phrases(q):
        if t not in seen:
            seen.add(t)
            out.append(t)

    def _append_pairs(pairs: Tuple[Tuple[str, Tuple[str, ...]], ...]) -> None:
        for zh, ens in pairs:
            if zh not in q:
                continue
            if zh not in seen:
                seen.add(zh)
                out.append(zh)
            for en in ens:
                el = str(en).strip().lower()
                if len(el) >= 2 and el not in seen:
                    seen.add(el)
                    out.append(el)

    _append_pairs(_TOPIC_ZH_TO_EN)
    _append_pairs(_TOPIC_TRADE_ZH_TO_EN)
    _append_pairs(_TOPIC_GEO_ZH_TO_EN)
    return out[:24]


def _extract_host(url: str) -> str:
    try:
        return (urlparse(str(url or "")).netloc or "").strip().lower()
    except Exception:
        return ""


def _row_text_blob(row: Dict[str, str]) -> str:
    title = str(row.get("title") or "")
    body = str(row.get("body") or "")
    href = str(row.get("href") or row.get("url") or "")
    return f"{title}\n{body}\n{href}".strip()


def _count_token_hits(tokens: List[str], text: str, text_l: str) -> int:
    hits = 0
    for token in tokens or []:
        t = str(token or "").strip()
        if len(t) < 2:
            continue
        if t.isascii():
            if t.lower() in text_l:
                hits += 1
        elif t in text:
            hits += 1
    return hits


def _score_ddgs_row(
    row: Dict[str, str],
    user_query: str,
    toks: List[str],
    required_topics: List[str],
) -> Tuple[float, Dict[str, Any]]:
    title = str(row.get("title") or "").strip()
    body = str(row.get("body") or "").strip()
    text_blob = f"{title}\n{body}".strip()
    text_blob_l = text_blob.lower()
    title_l = title.lower()
    href = str(row.get("href") or row.get("url") or "").strip()
    host = _extract_host(href)
    path = ""
    try:
        path = (urlparse(href).path or "").strip()
    except Exception:
        path = ""

    topic_hits = _count_token_hits(required_topics, text_blob, text_blob_l)
    rel_hits = _count_token_hits(toks, text_blob, text_blob_l)
    title_topic_hits = _count_token_hits(required_topics, title, title_l)
    title_rel_hits = _count_token_hits(toks, title, title_l)
    code_hits = _count_token_hits(_extract_codes_from_text(str(user_query or "")), text_blob, text_blob_l)
    url_hits = _count_token_hits(toks, href, href.lower())
    finance_bonus = 0
    if any(x in str(user_query or "") for x in ("股价", "行情", "走势", "涨跌", "指数", "板块", "石油", "炼化")):
        finance_bonus = _count_token_hits(
            ["股价", "行情", "走势", "指数", "板块", "行业", "龙头", "领涨", "异动", "price", "quote", "market", "stock", "share", "sector", "industry", "leader", "bellwether", "top gainer", "momentum", "oil", "energy", "refining"],
            text_blob,
            text_blob_l,
        )

    score = 0.0
    score += topic_hits * 9.0
    score += title_topic_hits * 6.0
    score += rel_hits * 2.5
    score += title_rel_hits * 3.0
    score += code_hits * 8.0
    score += min(url_hits, 2) * 0.5
    score += min(finance_bonus, 4) * 2.0
    if host in _TRUSTED_FINANCE_HOSTS:
        score += 8.0
        if path and path not in ("", "/"):
            score += 4.0
    if host in _PREFERRED_FINANCE_COMMUNITY_HOSTS:
        score += 10.0

    noisy = _looks_like_irrelevant_result(row, user_query)
    if noisy:
        score -= 8.0
    if host in _IRRELEVANT_RESULT_HOSTS:
        score -= 12.0
    if not href:
        score -= 2.0
    if len(title) <= 6:
        score -= 1.0

    return score, {
        "host": host,
        "path": path,
        "topic_hits": topic_hits,
        "rel_hits": rel_hits,
        "title_topic_hits": title_topic_hits,
        "title_rel_hits": title_rel_hits,
        "code_hits": code_hits,
        "url_hits": url_hits,
        "finance_bonus": finance_bonus,
        "trusted_finance_host": host in _TRUSTED_FINANCE_HOSTS,
        "noisy": noisy,
        "score": round(score, 3),
    }


def _looks_like_irrelevant_result(row: Dict[str, str], user_query: str) -> bool:
    host = _extract_host(str(row.get("href") or row.get("url") or ""))
    if host in _IRRELEVANT_RESULT_HOSTS:
        return True

    blob = _row_text_blob(row)
    blob_l = blob.lower()
    finance_query = _is_finance_market_query(user_query)

    if finance_query and host and host not in _STRICT_FINANCE_HOSTS:
        finance_needles = (
            "金融",
            "财经",
            "股价",
            "行情",
            "股票",
            "股市",
            "证券",
            "finance",
            "financial",
            "stock",
            "stocks",
            "share",
            "shares",
            "quote",
            "market",
            "equity",
        )
        if not any(n.lower() in blob_l for n in finance_needles):
            return True

    required_topics = _required_topic_tokens(user_query)
    if required_topics:
        topic_hit = False
        for token in required_topics:
            if token.isascii():
                if token in blob_l:
                    topic_hit = True
                    break
            elif token in blob:
                topic_hit = True
                break
        if not topic_hit:
            return True

    if any(h in blob_l for h in _IRRELEVANT_RESULT_HINTS):
        finance_hits = 0
        for _, hints in _FINANCE_HINT_PAIRS:
            for hint in hints:
                s = str(hint).strip().lower()
                if s and s in blob_l:
                    finance_hits += 1
                    break
        if finance_hits == 0:
            return True

    if finance_query or any(k in str(user_query or "") for k in ("股价", "行情", "市值", "财报", "业绩")):
        finance_needles = ("股价", "行情", "市值", "price", "quote", "market", "stock", "share")
        if not any(n.lower() in blob_l for n in finance_needles):
            generic_noise = ("下载", "社交", "分享", "论坛", "视频", "游戏", "音乐", "壁纸")
            if any(n in blob for n in generic_noise) or host in _IRRELEVANT_RESULT_HOSTS:
                return True

    return False


def filter_ddgs_rows_by_user_query(
    rows: List[Dict[str, str]],
    user_query: str,
) -> Tuple[List[Dict[str, str]], int, Dict[str, Any]]:
    """
    对 DDG 结果只做相关性打分与排序，不再因词元重合不足而整体丢弃候选。
    """
    aux: Dict[str, Any] = {}
    toks = _relevance_tokens_expanded(user_query)
    required_topics = _required_topic_tokens(user_query)
    must_tokens = _must_relevance_tokens(user_query)
    finance_query = _is_finance_market_query(user_query)

    min_score = max(0.0, float(os.getenv("KG_WEB_MIN_RELEVANCE_SCORE", "8.0") or 8.0))
    min_must_hits = max(1, _env_int("KG_WEB_MIN_MUST_HITS", 1))

    ranked: List[Tuple[float, int, Dict[str, str], Dict[str, Any]]] = []
    malformed = 0
    dropped_by_score = 0
    dropped_by_must = 0
    for idx, row in enumerate(rows or []):
        if not any(str(row.get(k) or "").strip() for k in ("title", "body", "href", "url")):
            malformed += 1
            continue
        host = _extract_host(str(row.get("href") or row.get("url") or ""))
        if finance_query and host and host not in _STRICT_FINANCE_HOSTS:
            malformed += 1
            continue
        score, detail = _score_ddgs_row(row, user_query, toks, required_topics)
        blob = _row_text_blob(row)
        blob_l = blob.lower()
        must_hits = _count_token_hits(must_tokens, blob, blob_l)
        detail["must_hits"] = must_hits

        if score < min_score:
            dropped_by_score += 1
            continue
        if must_tokens and must_hits < min_must_hits:
            dropped_by_must += 1
            continue

        ranked.append((score, idx, row, detail))

    fallback_relaxed = False
    if not ranked:
        fallback_relaxed = True
        for idx, row in enumerate(rows or []):
            if not any(str(row.get(k) or "").strip() for k in ("title", "body", "href", "url")):
                continue
            host = _extract_host(str(row.get("href") or row.get("url") or ""))
            if finance_query and host and host not in _STRICT_FINANCE_HOSTS:
                continue
            score, detail = _score_ddgs_row(row, user_query, toks, required_topics)
            blob = _row_text_blob(row)
            blob_l = blob.lower()
            detail["must_hits"] = _count_token_hits(must_tokens, blob, blob_l)
            ranked.append((score, idx, row, detail))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    if fallback_relaxed:
        keep_n = max(1, _env_int("KG_WEB_RELAXED_KEEP_TOPN", 2))
        ranked = ranked[:keep_n]

    ordered_rows = [row for _, _, row, _ in ranked]
    aux["web_rank_mode"] = "score_with_hard_gates"
    aux["web_ranked_count"] = len(ordered_rows)
    aux["web_rank_preview"] = [detail for _, _, _, detail in ranked[:6]]
    aux["web_min_relevance_score"] = min_score
    aux["web_min_must_hits"] = min_must_hits if must_tokens else 0
    aux["web_must_tokens"] = must_tokens
    aux["web_finance_market_query"] = finance_query
    aux["web_dropped_by_score"] = dropped_by_score
    aux["web_dropped_by_must"] = dropped_by_must
    aux["web_filter_fallback_relaxed"] = fallback_relaxed

    return ordered_rows, malformed, aux


def _salvage_web_rows_when_overfiltered(
    rows: List[Dict[str, str]],
    user_query: str,
    final_topk: int,
) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    q = str(user_query or "")
    toks = _relevance_tokens_expanded(q)
    required_topics = _required_topic_tokens(q)
    finance_query = _is_finance_market_query(q)
    candidates: List[Tuple[float, int, Dict[str, str], Dict[str, Any]]] = []

    for idx, row in enumerate(rows or []):
        if not any(str(row.get(k) or "").strip() for k in ("title", "body", "href", "url")):
            continue
        href = str(row.get("href") or row.get("url") or "").strip()
        host = _extract_host(href)
        if finance_query and host and host not in _STRICT_FINANCE_HOSTS:
            continue
        score, detail = _score_ddgs_row(row, q, toks, required_topics)
        # 救援分支不再套 min_score / must_hits 硬阈值，只要求来源和问题至少有基本财经相关性。
        if finance_query:
            if host in _PREFERRED_FINANCE_COMMUNITY_HOSTS:
                score += 6.0
            elif host in _TRUSTED_FINANCE_HOSTS:
                score += 4.0
        if score <= 0 and finance_query:
            continue
        candidates.append((score, idx, row, detail))

    candidates.sort(key=lambda item: (-item[0], item[1]))
    keep_n = max(1, min(final_topk, 2 if finance_query else final_topk))
    kept = [row for _, _, row, _ in candidates[:keep_n]]
    meta = {
        "web_salvage_used": bool(kept),
        "web_salvage_mode": "trusted_finance_rows" if finance_query else "best_effort_rows",
        "web_salvage_candidates": len(candidates),
        "web_salvage_preview": [detail for _, _, _, detail in candidates[:4]],
    }
    return kept, meta


def _query_specificity_profile(user_query: str) -> Dict[str, int]:
    core = _question_core_snippet(user_query)
    uniq = _unique_query_terms(user_query, max_terms=8)
    codes = _extract_codes_from_text(user_query)
    required = _required_topic_tokens(user_query)
    return {
        "core_len": len(core),
        "unique_term_count": len(uniq),
        "code_count": len(codes),
        "required_topic_count": len(required),
    }


def _must_relevance_tokens(user_query: str) -> List[str]:
    """
    生成“问题核心词”集合，用于硬相关过滤：
    - 优先保留证券代码
    - 保留主题必选词（如半导体/石油/板块等）
    - 补充少量较长独特词，提升问句语义约束
    """
    must: List[str] = []
    seen = set()

    for code in _extract_codes_from_text(user_query):
        c = str(code).strip()
        if c and c not in seen:
            seen.add(c)
            must.append(c)

    for t in _required_topic_tokens(user_query):
        s = str(t).strip()
        if len(s) >= 2 and s not in seen:
            seen.add(s)
            must.append(s)

    long_terms = [x for x in _unique_query_terms(user_query, max_terms=8) if len(str(x).strip()) >= 3]
    for t in long_terms[:4]:
        s = str(t).strip()
        if s and s not in seen:
            seen.add(s)
            must.append(s)

    return must[:12]


def _dynamic_web_topk(user_query: str, requested: Optional[int] = None) -> int:
    sp = _query_specificity_profile(user_query)
    if sp["code_count"] == 0 and (sp["core_len"] <= 10 or sp["unique_term_count"] <= 2):
        dynamic = max(1, min(_env_int("KG_WEB_SEARCH_TOPK_BROAD", 8), 10))
    elif sp["code_count"] > 0 or sp["required_topic_count"] > 0 or sp["unique_term_count"] >= 4:
        dynamic = max(1, min(_env_int("KG_WEB_SEARCH_TOPK_SPECIFIC", 4), 10))
    else:
        dynamic = max(1, min(_env_int("KG_WEB_SEARCH_TOPK_NORMAL", 5), 10))
    if requested is None:
        return dynamic
    try:
        req = max(1, min(int(requested), 10))
    except Exception:
        return dynamic
    return max(req, dynamic)


def _candidate_fetch_size(final_topk: int) -> int:
    mult = max(2, _env_int("KG_WEB_SEARCH_FETCH_MULTIPLIER", 3))
    floor_n = max(final_topk, _env_int("KG_WEB_SEARCH_FETCH_FLOOR", 10))
    ceil_n = max(floor_n, _env_int("KG_WEB_SEARCH_FETCH_CEILING", 16))
    return min(max(final_topk * mult, floor_n), ceil_n)


def _extract_codes_from_text(text: str) -> List[str]:
    found = _RE_CODE.findall(text or "")
    out = []
    for x in found:
        if x not in out:
            out.append(x)
    return out[:6]


def _dedupe_query_parts(parts: List[str]) -> List[str]:
    merged: List[str] = []
    seenp = set()
    for p in parts:
        p = str(p).strip()
        if not p or p in seenp:
            continue
        seenp.add(p)
        merged.append(p)
    return merged


def _terms_allowed_by_corpus(user_query: str, corpus: str) -> List[str]:
    """仅保留在用户问题中出现、且在样本锚定语料中同样出现的词/短语（防乱搜）。"""
    cq = (corpus or "").lower()
    q = user_query or ""
    picked: List[str] = []
    seen = set()
    # 板块/行业短语属于检索核心意图，即便样本语料未出现完整短语也保留。
    for t in _extract_sector_phrases(q):
        if t not in seen:
            seen.add(t)
            picked.append(t)
    for m in _RE_CODE.finditer(q):
        t = m.group(1)
        if t in cq and t not in seen:
            seen.add(t)
            picked.append(t)
    for m in _RE_WORD.finditer(q):
        t = m.group(0).strip()
        if len(t) < 2:
            continue
        low = t.lower()
        if low in cq and t not in seen:
            seen.add(t)
            picked.append(t)
        elif t in corpus and t not in seen:
            seen.add(t)
            picked.append(t)
    return picked[:10]


def _open_domain_geo_conflict_question(user_query: str) -> bool:
    """地缘/冲突开放提问：样本锚定串若只有证券代码+公告标题，DDG 极易偏离用户真实意图。"""
    u = (user_query or "").strip()
    if len(u) < 4:
        return False
    needles = (
        "俄乌战争",
        "俄乌冲突",
        "乌克兰战争",
        "乌俄战争",
        "俄罗斯乌克兰",
        "入侵乌克兰",
        "乌克兰局势",
        "俄乌",
        "顿巴斯",
        "巴赫穆特",
        "克里米亚",
    )
    return any(n in u for n in needles)


def _normalize_web_query_text(user_query: str, max_len: int = 220) -> str:
    """
    联网检索查询净化：
    - 优先抽取「当前问题」锚点
    - 去掉对话角色前缀（用户/助手）
    - 压缩空白并限制长度，避免把整段历史喂给搜索引擎
    """
    q = str(user_query or "").strip()
    if not q:
        return ""

    marker = "【当前问题】"
    if marker in q:
        tail = q.rsplit(marker, 1)[-1].strip()
        if tail:
            q = tail

    q = re.sub(r"(?:^|\n)\s*(用户|助手)\s*[：:]\s*", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    if len(q) > max_len:
        q = q[:max_len].strip()
    return q


def build_constrained_search_query(
    project_id: str,
    user_query: str,
) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    构造搜索查询串；优先保留用户原问题与独特词，同时在可用时附加项目样本锚点。
    meta 含 anchors 摘要供调试与前端展示。
    """
    pid = str(project_id or "").strip()
    uq = _normalize_web_query_text(user_query)
    ids = _fetch_project_sample_ids(pid)
    stocks = _fetch_project_stock_nums(pid)
    samples = _mongo_samples(ids)
    corpus = _anchor_corpus(samples, stocks)
    if not corpus.strip():
        fallback_parts = _compose_question_first_query_parts(uq, [], max_terms=max(4, _env_int("KG_WEB_DIRECT_QUERY_MAX_TERMS", 8)))
        fallback_query = " ".join(_dedupe_query_parts(fallback_parts))[: max(40, _env_int("KG_WEB_SEARCH_QUERY_MAX_CHARS", 160))]
        if fallback_query:
            return fallback_query, {
                "ok": True,
                "reason": "no_samples_direct_query_fallback",
                "project_id": pid,
                "sample_count": 0,
                "anchor_mode": "question_direct",
                "query": fallback_query,
                "user_terms_filtered": _unique_query_terms(uq),
            }
        return None, {
            "ok": False,
            "reason": "no_samples",
            "project_id": pid,
            "sample_count": 0,
        }

    codes_in_corpus = _extract_codes_from_text(corpus)
    title_head = ""
    if samples:
        title_head = (samples[0].get("title") or "").strip()
    # 标题截断为检索核心，避免过长
    if len(title_head) > 48:
        title_head = title_head[:48]

    allowed_extra = _terms_allowed_by_corpus(uq, corpus)
    anchor_parts: List[str] = []
    if codes_in_corpus:
        anchor_parts.extend(codes_in_corpus[:2])
    elif stocks:
        anchor_parts.extend(str(s) for s in stocks[:2])
    if title_head and _anchor_matches_query(title_head, uq):
        anchor_parts.append(title_head)
    anchor_parts.extend([x for x in allowed_extra if _anchor_matches_query(x, uq)])

    merged = _dedupe_query_parts(
        _compose_question_first_query_parts(
            uq,
            anchor_parts,
            max_terms=max(6, _env_int("KG_WEB_QUESTION_FIRST_MAX_TERMS", 12)),
        )
    )

    anchor_mode = "question_plus_anchor"
    fallback_terms: List[str] = []

    # 严格锚定：用户词必须出现在样本语料中。若样本里根本没有「半导体」等词，
    # merged 可能为空——此时用户会感觉「开了联网也没用」。回退策略：只要项目仍有样本，
    # 则用「样本证券代码/标题前缀 + 用户问题中的关键词」拼检索串；噪声由 filter_ddgs_rows_by_user_query 兜底。
    if not merged:
        fb_env = (os.getenv("KG_WEB_SEARCH_FALLBACK_USER_TERMS") or "true").strip().lower()
        if fb_env not in ("0", "false", "no", "off"):
            fb_max = max(2, min(12, _env_int("KG_WEB_FALLBACK_QUERY_MAX_TERMS", 6)))
            fallback_terms = _unique_query_terms(uq, max_terms=fb_max)
            anchor_pref: List[str] = []
            if codes_in_corpus:
                anchor_pref.extend(codes_in_corpus[:1])
            elif stocks:
                anchor_pref.append(str(stocks[0]).strip())
            if title_head and _anchor_matches_query(title_head, uq):
                anchor_pref.append(title_head.strip()[:48])
            cand = _compose_question_first_query_parts(uq, anchor_pref + fallback_terms, max_terms=fb_max + 4)
            merged = _dedupe_query_parts(cand)
            if merged:
                anchor_mode = "fallback_question_terms"

    if not merged:
        return None, {
            "ok": False,
            "reason": "empty_query_parts",
            "project_id": pid,
            "sample_count": len(samples),
            "hint": "no_query_tokens_and_fallback_disabled_or_empty_question",
        }

    max_q = max(40, _env_int("KG_WEB_SEARCH_QUERY_MAX_CHARS", 160))
    blend_snip = ""
    open_blend = False
    sw = (os.getenv("KG_WEB_SEARCH_OPEN_TOPIC_BLEND") or "true").strip().lower()
    if sw not in ("0", "false", "no", "off") and _open_domain_geo_conflict_question(uq):
        max_snip = max(32, min(96, max_q // 2))
        blend_snip = re.sub(r"\s+", " ", uq).strip()[:max_snip]
        if len(blend_snip) >= 6:
            merged = _dedupe_query_parts([blend_snip] + list(merged))
            open_blend = True

    query_str = " ".join(merged)[:max_q]

    meta_out: Dict[str, Any] = {
        "ok": True,
        "project_id": pid,
        "sample_count": len(samples),
        "sample_ids": ids[:20],
        "stock_nums_project": stocks,
        "codes_in_samples": codes_in_corpus[:4],
        "title_used": title_head,
        "user_terms_filtered": allowed_extra,
        "anchor_mode": anchor_mode,
        "fallback_user_terms": fallback_terms if anchor_mode in ("fallback_user_terms", "fallback_question_terms") else [],
        "query": query_str,
        "open_topic_query_blend": open_blend,
        "open_topic_snippet": blend_snip if open_blend else "",
    }
    return query_str, meta_out


def _duckduckgo_search_text_rows(
    keywords: str,
    max_results: int,
) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    """
    改为国内直连抓取纯净版必应 (cn.bing.com) ，避免 DuckDuckGo 在国内被墙导致的问题。
    如果直连搜索失败，会自动回退尝试鸭鸭搜/Bing 官方接口。
    """
    aux: Dict[str, Any] = {}

    # === 【新增逻辑】优先使用直连必应爬虫（无墙，国内可用） ===
    try:
        import requests
        from lxml import html
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        url = f"https://cn.bing.com/search?q={requests.utils.quote(keywords)}"
        res = requests.get(url, headers=headers, timeout=8)
        res.raise_for_status()
        tree = html.fromstring(res.text)
        bing_rows = []
        for el in tree.xpath('//li[@class="b_algo"]'):
            title = "".join(el.xpath('.//h2/a//text()')).strip()
            link = "".join(el.xpath('.//h2/a/@href')).strip()
            body_nodes = el.xpath('.//div[@class="b_caption"]//p//text()')
            if not body_nodes:
                body_nodes = el.xpath('.//p[@class="b_lineclamp2"]//text()')
            body = "".join(body_nodes).strip()
            if title and link:
                bing_rows.append({"title": title, "url": link, "href": link, "body": body})
                if len(bing_rows) >= max_results:
                    break
        if bing_rows:
            aux["source"] = "cn.bing.com (direct routing)"
            return bing_rows, aux
    except Exception as e:
        aux["cn_bing_error"] = str(e)
    # =======================================================

    try:
        from ddgs import DDGS  # type: ignore
        aux["ddgs_pkg"] = "ddgs"
    except ImportError:
        try:
            # Backward compatibility for environments that still use old package name.
            from duckduckgo_search import DDGS  # type: ignore
            aux["ddgs_pkg"] = "duckduckgo_search"
        except ImportError:
            aux["error"] = "ddgs_not_installed"
            return [], aux

    clean_keywords = _normalize_web_query_text(keywords)
    if not clean_keywords:
        aux["error"] = "empty_keywords"
        return [], aux

    raw_order = (os.getenv("KG_WEB_SEARCH_DDG_BACKENDS") or "bing,brave,duckduckgo,yahoo").strip()
    backends = [b.strip().lower() for b in raw_order.split(",") if b.strip()]
    # 兼容新版 ddgs（html/lite 已被移除）。
    allowed = {
        "bing",
        "brave",
        "duckduckgo",
        "mojeek",
        "mullvad_brave",
        "mullvad_google",
        "wikipedia",
        "yahoo",
        "yandex",
        # 兼容老版本可能仍存在的后端。
        "html",
        "lite",
    }
    backends = [b for b in backends if b in allowed] or ["bing", "duckduckgo", "brave"]

    primary_region = (os.getenv("KG_WEB_SEARCH_REGION") or "wt-wt").strip() or "wt-wt"
    fb_region = (os.getenv("KG_WEB_SEARCH_FALLBACK_REGION") or "cn-zh").strip()
    regions: List[Optional[str]] = [primary_region]
    if fb_region and fb_region not in regions:
        regions.append(fb_region)

    attempts: List[Dict[str, Any]] = []

    def _normalize_rows(rows_obj: Any) -> List[Dict[str, str]]:
        rows_list = list(rows_obj or [])
        norm: List[Dict[str, str]] = []
        for row in rows_list:
            if not isinstance(row, dict):
                continue
            norm.append(
                {
                    "title": str(row.get("title") or ""),
                    "href": str(row.get("href") or row.get("url") or ""),
                    "url": str(row.get("url") or row.get("href") or ""),
                    "body": str(row.get("body") or row.get("snippet") or ""),
                }
            )
        return norm

    def _try_public_text(ddgs: Any, q: str, reg: Optional[str], bk: str) -> List[Dict[str, str]]:
        """Prefer public DDGS.text for cross-version compatibility."""
        text_fn = getattr(ddgs, "text", None)
        if not callable(text_fn):
            return []

        base_variants = [
            {"keywords": q, "max_results": max_results, "backend": bk},
            {"query": q, "max_results": max_results, "backend": bk},
            {"keywords": q, "max_results": max_results, "backends": [bk]},
            {"query": q, "max_results": max_results, "backends": [bk]},
            {"keywords": q, "backend": bk},
            {"query": q, "backend": bk},
            {"keywords": q, "max_results": max_results},
            {"query": q, "max_results": max_results},
        ]
        call_variants = []
        for kv in base_variants:
            call_variants.append(dict(kv))
            if isinstance(reg, str) and reg.strip():
                with_region = dict(kv)
                with_region["region"] = reg
                call_variants.insert(0, with_region)
        positional_variants = [
            (q,),
            (q, reg),
            (q, reg, None),
            (q, reg, None, max_results),
        ]

        last_err: Optional[Exception] = None
        for kwargs in call_variants:
            try:
                rows = text_fn(**kwargs)
                out = _normalize_rows(rows)
                if out:
                    return out
            except TypeError as e:
                last_err = e
                continue
            except Exception as e:
                raise e

        for args in positional_variants:
            try:
                rows = text_fn(*args)
                out = _normalize_rows(rows)
                if out:
                    return out
            except TypeError as e:
                last_err = e
                continue
            except Exception as e:
                raise e

        if last_err is not None:
            raise last_err
        return []

    # 自动探测并使用代理（支持配置或默认本地科学代理）
    proxy_url = (os.environ.get("KG_WEB_PROXY") or 
                 os.environ.get("HTTPS_PROXY") or 
                 os.environ.get("HTTP_PROXY") or 
                 os.environ.get("https_proxy") or 
                 os.environ.get("http_proxy") or 
                 "http://127.0.0.1:7890")  # 提供一个常见的默认本地梯子端口降级尝试
                 
    ddgs_kwargs = {}
    if proxy_url:
        ddgs_kwargs["proxy"] = proxy_url     # >= 7.x 新版使用 proxy 参数
        ddgs_kwargs["proxies"] = proxy_url   # < 7.x 旧版可能使用 proxies
        
    try:
        ddgs_inst = DDGS(**ddgs_kwargs)
    except TypeError:
        # 如果当前版本严格限制了无关 kwargs 抛 TypeError，作兼容降级：
        try:
            ddgs_inst = DDGS(proxy=proxy_url) if proxy_url else DDGS()
        except TypeError:
            try:
                ddgs_inst = DDGS(proxies=proxy_url) if proxy_url else DDGS()
            except TypeError:
                ddgs_inst = DDGS()

    with ddgs_inst as ddgs:
        for reg in regions:
            for bk in backends:
                try:
                    rows = _try_public_text(ddgs, clean_keywords, reg, bk)
                    path = "public_text"
                    if not rows:
                        # Backward compatibility: some old builds expose private backend methods.
                        fn = getattr(ddgs, f"_text_{bk}", None)
                        if callable(fn):
                            rows = _normalize_rows(fn(clean_keywords, reg, None, max_results))
                            path = f"private_{bk}"
                    if rows:
                        aux["ddgs_backend"] = bk
                        aux["ddgs_call_path"] = path
                        aux["region_used"] = reg
                        aux["ddgs_attempts"] = attempts
                        return list(rows), aux
                    attempts.append(
                        {"backend": bk, "region": reg, "rows": 0}
                    )
                except Exception as e:
                    msg = str(e)
                    attempts.append(
                        {"backend": bk, "region": reg, "error": msg[:500]}
                    )
                    # 网络层面被主动拒绝时，继续轮询更多引擎通常只会刷重复报错。
                    if (
                        "10061" in msg
                        or "actively refused" in msg.lower()
                        or "connecterror" in msg.lower()
                    ):
                        aux["ddgs_attempts"] = attempts
                        aux["error"] = "ddgs_connect_refused"
                        return [], aux
    aux["ddgs_attempts"] = attempts
    aux["error"] = "ddgs_all_backends_failed"
    return [], aux


def run_constrained_web_search(
    project_id: str,
    user_query: str,
    max_results: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    执行受限检索，返回与 retrieve_project_kg 兼容的 evidence 列表（snippet 前缀标明来源）。
    """
    q, meta = build_constrained_search_query(project_id, user_query)
    if not q:
        return [], meta

    final_topk = _dynamic_web_topk(user_query, max_results)
    fetch_n = _candidate_fetch_size(final_topk)
    results: List[Dict[str, Any]] = []

    rows, ddgs_meta = _duckduckgo_search_text_rows(q, fetch_n)
    meta = {**meta, **ddgs_meta}
    meta["web_dynamic_topk"] = final_topk
    meta["web_candidate_fetch_size"] = fetch_n
    meta["web_query_specificity"] = _query_specificity_profile(user_query)

    rows_before_rank = len(rows)
    ranked_rows, malformed_dropped, rank_meta = filter_ddgs_rows_by_user_query(rows, user_query)
    meta.update(rank_meta)
    meta["web_ddgs_prefilter_count"] = rows_before_rank
    meta["web_ddgs_relevance_dropped"] = malformed_dropped

    if not ranked_rows and rows_before_rank > 0:
        salvaged_rows, salvage_meta = _salvage_web_rows_when_overfiltered(rows, user_query, final_topk)
        meta.update(salvage_meta)
        if salvaged_rows:
            ranked_rows = salvaged_rows
            meta["web_failure_hint"] = "overfiltered_salvaged"

    rerank_pool = max(final_topk, min(len(ranked_rows), _env_int("KG_WEB_SEARCH_RERANK_POOL", 8)))
    reranked_rows, review_meta = review_web_search_rows(
        ranked_rows[:rerank_pool],
        user_query,
        required_topic_tokens=_required_topic_tokens(user_query),
        relevance_tokens=_relevance_tokens_expanded(user_query),
        max_results=final_topk,
    )
    meta.update(review_meta)
    rows = reranked_rows if reranked_rows else ranked_rows[:final_topk]
    meta["web_ranking_strategy"] = (
        "lexical_salvage_plus_semantic_rerank"
        if meta.get("web_salvage_used")
        else "lexical_plus_semantic_rerank"
    )

    if not rows and rows_before_rank == 0 and not ddgs_meta.get("error"):
        meta["web_failure_hint"] = "ddgs_empty"
    elif not rows and rows_before_rank > 0:
        meta["web_failure_hint"] = "semantic_rerank_empty"

    for i, row in enumerate(rows):
        title = str(row.get("title") or "").strip()
        href = str(row.get("href") or row.get("url") or "").strip()
        body = str(row.get("body") or "").strip()
        src_line = (
            f"\n────────\n来源网址（须在回答中附给用户）：{href}" if href else ""
        )
        head = (
            "[联网检索·语义重排] 已先按问题相关性排序，再对候选网页做二阶段语义重排；仅作公开市场信息参考。\n"
            if meta.get("review_agent_used")
            else "[联网检索·样本锚定排序] 检索查询已限制为本项目已选公告样本中的代码与用语，并按相关性排序。\n"
        )
        if meta.get("web_salvage_used"):
            head = (
                "[联网检索·保底回退] 原始候选已命中可信财经来源；因严格过滤/重排未稳定选出摘要，本条按可信源与问题相关性保底保留。\n"
            )
        snippet = (
            f"{head}"
            f"标题: {title}\n链接: {href}\n摘要: {body[:500]}{src_line}"
        )
        results.append(
            {
                "project_id": str(project_id),
                "node_id": f"web_{i}",
                "score": 0.42,
                "snippet": snippet,
                "source": "constrained_web",
                "url": href,
                "page_title": title,
            }
        )

    meta["result_count"] = len(results)
    return results, meta


def run_constrained_web_search_multi(
    project_ids: List[str],
    user_query: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    在用户可见的多个项目上分别做「样本锚定」联网检索，合并结果并按 URL 去重。
    用于未指定单一 project_id 时，由 Agent 跨项目补充网页摘要。
    """
    pids = [str(p).strip() for p in (project_ids or []) if str(p).strip()]
    max_projects = max(1, _env_int("KG_WEB_SEARCH_MAX_PROJECTS", 15))
    per_proj_n = max(1, _env_int("KG_WEB_SEARCH_RESULTS_PER_PROJECT_MULTI", 3))

    combined: List[Dict[str, Any]] = []
    seen_urls = set()
    per_project_meta: List[Dict[str, Any]] = []
    scanned = 0

    for pid in pids[:max_projects]:
        ev, meta = run_constrained_web_search(pid, user_query, max_results=per_proj_n)
        scanned += 1
        row = {"project_id": pid, **(meta if isinstance(meta, dict) else {})}
        per_project_meta.append(row)
        for e in ev or []:
            url = str((e or {}).get("url") or "").strip()
            if url:
                if url in seen_urls:
                    continue
                seen_urls.add(url)
            combined.append(e)

    project_errors = [
        str((m or {}).get("error") or "").strip()
        for m in per_project_meta
        if isinstance(m, dict)
    ]
    project_errors = [x for x in project_errors if x]
    project_hints = [
        str((m or {}).get("web_failure_hint") or "").strip()
        for m in per_project_meta
        if isinstance(m, dict)
    ]
    project_hints = [x for x in project_hints if x]

    agg_meta: Dict[str, Any] = {
        "multi_project": True,
        "projects_scanned": scanned,
        "project_ids": pids[:max_projects],
        "result_count": len(combined),
        "per_project": per_project_meta,
    }
    if scanned > 0 and len(combined) == 0:
        if project_errors and len(set(project_errors)) == 1:
            agg_meta["error"] = project_errors[0]
        if project_hints and len(set(project_hints)) == 1:
            agg_meta["web_failure_hint"] = project_hints[0]
    return combined, agg_meta


def merge_kg_and_web_evidence(
    kg_evidence: List[Dict[str, Any]],
    web_evidence: List[Dict[str, Any]],
    max_total: int = 14,
) -> List[Dict[str, Any]]:
    """
    图谱与网页证据合并：
    - 保留图谱优先
    - 当网页证据存在时，为其预留最小槽位，避免被图谱证据完全挤出
    """
    kg_list = list(kg_evidence or [])
    web_list = list(web_evidence or [])
    cap = max(6, int(max_total or 14))
    if not kg_list and not web_list:
        return []
    if not web_list:
        return kg_list[:cap]
    if not kg_list:
        return web_list[:cap]

    # 默认至少保留 2 条网页摘要（可通过环境变量覆盖）。
    reserve_min = max(1, _env_int("KG_QA_WEB_RESERVED_MIN", 2))
    reserve_max = max(reserve_min, _env_int("KG_QA_WEB_RESERVED_MAX", max(2, cap // 2)))
    reserve_web = min(len(web_list), reserve_max, max(reserve_min, cap // 3))
    kg_cap = max(0, cap - reserve_web)

    merged: List[Dict[str, Any]] = []
    if kg_cap > 0 and reserve_web > 0:
        chunks = reserve_web + 1
        chunk_size = int(math.ceil(kg_cap / chunks))
        for i in range(chunks):
            start = i * chunk_size
            end = min(kg_cap, start + chunk_size)
            merged.extend(kg_list[start:end])
            if i < reserve_web:
                merged.append(web_list[i])
    else:
        merged.extend(kg_list[:kg_cap])
        merged.extend(web_list[:reserve_web])

    # 回填剩余槽位，优先补图谱，再补网页。
    if len(merged) < cap:
        merged.extend(kg_list[kg_cap: kg_cap + (cap - len(merged))])
    if len(merged) < cap:
        merged.extend(web_list[reserve_web: reserve_web + (cap - len(merged))])
    return merged[:cap]
