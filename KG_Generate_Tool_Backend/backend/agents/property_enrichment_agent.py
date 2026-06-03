from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


_DATE_PATTERNS = [
    re.compile(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})日?"),
    re.compile(r"(20\d{2})(\d{2})(\d{2})"),
]


def _safe_props(item: Dict[str, Any]) -> Dict[str, Any]:
    props = item.get("properties") if isinstance(item.get("properties"), dict) else {}
    item["properties"] = props
    return props


def _clean_text(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _norm_date_text(text: str) -> str:
    t = _clean_text(text)
    if not t:
        return ""
    for pat in _DATE_PATTERNS:
        m = pat.search(t)
        if not m:
            continue
        y, mo, d = m.group(1), m.group(2), m.group(3)
        try:
            dt = datetime(int(y), int(mo), int(d))
            return dt.strftime("%Y-%m-%d")
        except Exception:
            continue
    return ""


def _extract_tickers(text: str) -> List[str]:
    t = _clean_text(text)
    if not t:
        return []
    out = set()
    for m in re.findall(r"\b(\d{6})\.(SH|SZ)\b", t, flags=re.IGNORECASE):
        out.add(f"{m[0]}.{m[1].upper()}")
    for m in re.findall(r"\b(\d{5})\.HK\b", t, flags=re.IGNORECASE):
        out.add(f"{m}.HK")
    # Bare A-share code fallback
    for m in re.findall(r"(?<!\d)(\d{6})(?!\d)", t):
        out.add(m)
    return sorted(out)


def _extract_amount(text: str) -> Optional[Dict[str, Any]]:
    t = _clean_text(text)
    if not t:
        return None
    m = re.search(r"([+-]?\d+(?:\.\d+)?)\s*(亿|万|千)?\s*(元|人民币|美元|港元)", t)
    if not m:
        return None
    num = float(m.group(1))
    unit_scale = {"亿": 1e8, "万": 1e4, "千": 1e3, None: 1.0, "": 1.0}
    scale = unit_scale.get(m.group(2), 1.0)
    currency = m.group(3)
    return {
        "amount_raw": m.group(0),
        "amount_value": round(num * scale, 4),
        "amount_currency": currency,
    }


def _extract_percent(text: str) -> Optional[float]:
    t = _clean_text(text)
    if not t:
        return None
    m = re.search(r"([+-]?\d+(?:\.\d+)?)\s*%", t)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


def _infer_polarity(text: str) -> str:
    t = _clean_text(text)
    if not t:
        return "neutral"
    pos = ("上涨", "增持", "中标", "预增", "盈利", "回购", "利好", "增长", "修复")
    neg = ("下跌", "减持", "亏损", "处罚", "问询", "立案", "质押", "违约", "利空", "下滑")
    p = sum(1 for k in pos if k in t)
    n = sum(1 for k in neg if k in t)
    if p > n:
        return "positive"
    if n > p:
        return "negative"
    return "neutral"


def _infer_certainty(text: str) -> str:
    t = _clean_text(text)
    if not t:
        return "unknown"
    if any(k in t for k in ("公告", "披露", "已", "完成", "收到", "正式")):
        return "confirmed"
    if any(k in t for k in ("拟", "计划", "将", "预计", "可能", "或", "传闻")):
        return "tentative"
    return "unknown"


def _canonical_name(value: str) -> str:
    v = _clean_text(value)
    if not v:
        return ""
    # Remove ticker suffix in parentheses and normalize punctuation.
    v = re.sub(r"[（(]\s*\d{5,6}(?:\.(?:HK|SH|SZ))?\s*[)）]", "", v, flags=re.IGNORECASE)
    return v.strip(" -_|,，。；;:")


def _collect_aliases(value: str, context: str) -> List[str]:
    text = f"{value} {context}".strip()
    aliases = set()
    for m in re.findall(r"(?:简称|又称|别名)[:：]?\s*([\u4e00-\u9fa5A-Za-z0-9]{2,20})", text):
        aliases.add(m)
    for m in re.findall(r"([\u4e00-\u9fa5A-Za-z0-9]{2,20})\s*[（(][^)）]{0,12}[)）]", text):
        aliases.add(m)
    cn = _canonical_name(value)
    aliases.discard(cn)
    aliases.discard(value)
    return sorted(a for a in aliases if a)


def _role_from_key(key: str, ntype: Any) -> str:
    k = _clean_text(key)
    if str(ntype) in ("1", "event", "事件"):
        return "event"
    if any(x in k for x in ("收购方", "买方", "增持方", "融资方", "主体")):
        return "subject"
    if any(x in k for x in ("标的", "对象", "被收购方", "对手方")):
        return "object"
    if any(x in k for x in ("监管", "交易所", "证监", "法院")):
        return "regulator"
    return "entity"


def _pick_evidence_sentence(text: str, hints: List[str]) -> str:
    t = _clean_text(text)
    if not t:
        return ""
    parts = re.split(r"(?<=[。！？!?])", t)
    if not parts:
        return t[:160]
    hints = [h for h in hints if h]
    for p in parts:
        if all(h not in p for h in hints):
            continue
        return p.strip()[:180]
    return parts[0].strip()[:180]


def enrich_nodes_properties(
    nodes: List[Dict[str, Any]],
    samples: List[Dict[str, Any]],
    project_id: str,
) -> List[Dict[str, Any]]:
    if not nodes:
        return []

    sample_by_id = {
        str((s or {}).get("id") or ""): s
        for s in (samples or [])
        if str((s or {}).get("id") or "").strip()
    }
    corpus = "\n".join(_clean_text((s or {}).get("content")) for s in (samples or []))

    out = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        props = _safe_props(node)
        value = _clean_text(node.get("value"))
        key = _clean_text(node.get("key"))
        sid = _clean_text(props.get("sample_id"))
        sample = sample_by_id.get(sid) if sid else None
        sample_content = _clean_text((sample or {}).get("content"))
        context = _clean_text(props.get("context") or sample_content)

        props.setdefault("project_id", project_id)
        props.setdefault("enriched_by", "PropertyEnrichmentAgent")
        props.setdefault("canonical_name", _canonical_name(value) or value)
        aliases = _collect_aliases(value, context)
        if aliases:
            props.setdefault("aliases", aliases)

        tickers = _extract_tickers(f"{value} {context}")
        if tickers:
            props.setdefault("tickers", tickers)

        date_norm = _norm_date_text(f"{props.get('event_time') or ''} {context}")
        if not date_norm and sample is not None:
            date_norm = _norm_date_text((sample or {}).get("event_time"))
        if date_norm:
            props.setdefault("event_time_norm", date_norm)

        amt = _extract_amount(context)
        if amt:
            props.setdefault("amount_raw", amt["amount_raw"])
            props.setdefault("amount_value", amt["amount_value"])
            props.setdefault("amount_currency", amt["amount_currency"])

        pct = _extract_percent(context)
        if pct is not None:
            props.setdefault("percent_value", pct)

        props.setdefault("polarity", _infer_polarity(context or value))
        props.setdefault("certainty", _infer_certainty(context))
        props.setdefault("role", _role_from_key(key, node.get("type")))

        if value:
            mention_count = len(re.findall(re.escape(value), corpus)) if corpus else 0
            props.setdefault("mention_count", mention_count)

        ev_sent = _pick_evidence_sentence(context, [value, key])
        if ev_sent:
            props.setdefault("evidence_sentence", ev_sent)

        node["properties"] = props
        out.append(node)
    return out


def _infer_edge_direction(rel_type: str, value: str, context: str) -> str:
    t = f"{rel_type} {value} {context}"
    if any(k in t for k in ("上涨", "增持", "修复", "改善", "提升", "增长", "利好")):
        return "positive"
    if any(k in t for k in ("下跌", "减持", "亏损", "处罚", "下滑", "恶化", "利空")):
        return "negative"
    return "neutral"


def _infer_edge_strength(conf: float, text: str) -> str:
    if conf >= 0.88:
        return "strong"
    if conf >= 0.7:
        return "medium"
    if any(k in text for k in ("显著", "大幅", "明显", "强烈")):
        return "medium"
    return "weak"


def _infer_temporal_order(text: str) -> str:
    t = _clean_text(text)
    if any(k in t for k in ("随后", "之后", "其后", "继而")):
        return "after"
    if any(k in t for k in ("此前", "先于", "之前")):
        return "before"
    if any(k in t for k in ("同日", "当日", "当天")):
        return "same_day"
    return "unknown"


def _infer_trigger_phrase(value: str, context: str) -> str:
    v = _clean_text(value)
    if 2 <= len(v) <= 18:
        return v
    c = _clean_text(context)
    for kw in (
        "发布公告",
        "触发市场异动",
        "披露业绩变动",
        "触发监管事项",
        "发生融资安排",
        "带动板块波动",
        "因果影响",
        "时间先后",
    ):
        if kw in c:
            return kw
    return v[:18] if v else "语义关联"


def enrich_edges_properties(
    edges: List[Dict[str, Any]],
    nodes: List[Dict[str, Any]],
    samples: List[Dict[str, Any]],
    project_id: str,
) -> List[Dict[str, Any]]:
    if not edges:
        return []

    node_map = {
        str((n or {}).get("id") or ""): n
        for n in (nodes or [])
        if str((n or {}).get("id") or "").strip()
    }
    sample_by_id = {
        str((s or {}).get("id") or ""): s
        for s in (samples or [])
        if str((s or {}).get("id") or "").strip()
    }

    out = []
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        props = _safe_props(edge)
        src = node_map.get(str(edge.get("from") or ""), edge.get("from_node") or {})
        dst = node_map.get(str(edge.get("to") or ""), edge.get("to_node") or {})

        sid = _clean_text(props.get("sample_id"))
        sample = sample_by_id.get(sid) if sid else None
        context = _clean_text(props.get("context") or (sample or {}).get("content"))

        rel_type = _clean_text(edge.get("type"))
        rel_val = _clean_text(edge.get("value"))
        conf = float(props.get("confidence", 0.55) or 0.55)
        src_value = _clean_text((src or {}).get("value"))
        dst_value = _clean_text((dst or {}).get("value"))

        props.setdefault("project_id", project_id)
        props.setdefault("enriched_by", "PropertyEnrichmentAgent")
        props.setdefault("trigger_phrase", _infer_trigger_phrase(rel_val, context))
        props.setdefault("direction", _infer_edge_direction(rel_type, rel_val, context))
        props.setdefault("strength", _infer_edge_strength(conf, f"{rel_val} {context}"))
        props.setdefault("temporal_order", _infer_temporal_order(context))
        props.setdefault("certainty", _infer_certainty(context))

        evidence = _pick_evidence_sentence(context, [src_value, dst_value, rel_val])
        if evidence:
            props.setdefault("evidence_sentence", evidence)

        tickers = _extract_tickers(f"{src_value} {dst_value} {context}")
        if tickers:
            props.setdefault("tickers", tickers)

        amt = _extract_amount(context)
        if amt:
            props.setdefault("amount_raw", amt["amount_raw"])
            props.setdefault("amount_value", amt["amount_value"])
            props.setdefault("amount_currency", amt["amount_currency"])

        pct = _extract_percent(context)
        if pct is not None:
            props.setdefault("percent_value", pct)

        date_norm = _norm_date_text(f"{props.get('event_time') or ''} {context}")
        if not date_norm and sample is not None:
            date_norm = _norm_date_text((sample or {}).get("event_time"))
        if date_norm:
            props.setdefault("event_time_norm", date_norm)

        edge["properties"] = props
        out.append(edge)

    return out
