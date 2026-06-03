from flask import Blueprint, jsonify, request, Response, stream_with_context, current_app
from neo4j import GraphDatabase
from database import get_client

import requests
import os
import traceback
import hashlib
import time
import re
import uuid
import json
from agents.query_orchestrator_agent import (
    QueryPlannerAgent as OrchQueryPlannerAgent,
    SynthesisAgent as OrchSynthesisAgent,
    aggregate_rank as orch_aggregate_rank,
    conflict_awareness_skill as orch_conflict_awareness_skill,
    cross_project_retrieval_skill as orch_cross_project_retrieval_skill,
    evidence_citation_skill as orch_evidence_citation_skill,
    generate_answer as orch_generate_answer,
    list_user_projects as orch_list_user_projects,
)
from agents.agent_context import AgentContext
from agents.cache_layers import cache_get as tiered_cache_get
from agents.cache_layers import cache_set as tiered_cache_set
from agents.intent_taxonomy import INTENT_GENERAL, INTENT_KG_QUERY, INTENT_OPEN_DOMAIN
from agents.query_capability_agent import (
    build_general_answer_prompt_parts,
    classify_query_intent as capability_classify_query_intent,
    generate_general_answer as capability_generate_general_answer,
    generate_platform_guidance_answer as capability_generate_platform_guidance_answer,
    is_kg_quality_report_analysis_query,
    _is_general_chat_query,
    platform_guidance_system_prompt,
)
from agents.kg_quality_analysis_agent import generate_kg_quality_analysis_report
from agents.constrained_web_search import (
    merge_kg_and_web_evidence,
    run_constrained_web_search,
    run_constrained_web_search_multi,
)

askAI_bp = Blueprint('askAI', __name__)

# --- Langfuse tracing decorator ---
from functools import wraps
def langfuse_trace(endpoint_name):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            langfuse = getattr(current_app, 'langfuse', None)
            trace = None
            if langfuse:
                trace = langfuse.trace(
                    name=endpoint_name,
                    user_id=request.remote_addr or "anonymous",
                    metadata={"path": request.path}
                )
                request.langfuse_trace = trace
            try:
                response = f(*args, **kwargs)
                if trace:
                    trace.end()
                return response
            except Exception as e:
                if trace:
                    trace.end(level="ERROR", metadata={"error": str(e)})
                raise
        return wrapper
    return decorator

# Example usage for a route (add to your actual endpoints as needed):
# @askAI_bp.route('/trace_test', methods=['GET'])
# @langfuse_trace('trace_test')
# def trace_test():
#     trace = getattr(request, 'langfuse_trace', None)
#     if trace:
#         trace.span(name="test_span", metadata={"info": "test"}).end()
#     return jsonify({"msg": "Langfuse tracing works!"})

API_KEY = "sk-ef3bb4d2e83f4d78849ba0145ad8b7e4"
BASE_URL = "https://api.deepseek.com"
CHAT_MODEL = "deepseek-chat"

# NEO4J_URI = "neo4j://localhost:7687"
# NEO4J_USER = "neo4j"
# NEO4J_PASSWORD = "24721tianyue@"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "20040909"
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

_QA_ANSWER_CACHE_NS = "qa_answer"
_QA_RETRIEVAL_CACHE_NS = "qa_retrieval"


def _parse_bool(v, default=False):
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")


def _env_int(name, default):
    try:
        raw = os.getenv(name)
        if raw is None:
            return default
        return int(str(raw).strip())
    except Exception:
        return default


def _env_float(name, default):
    try:
        raw = os.getenv(name)
        if raw is None:
            return default
        return float(str(raw).strip())
    except Exception:
        return default


def _deepseek_post(payload, timeout_s, stream=False):
    """对 DeepSeek 请求做轻量重试，缓解偶发 TLS EOF/网络抖动。"""
    url = f"{BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        # 避免复用到异常连接导致 EOF，优先稳定性
        "Connection": "close",
    }
    max_retries = max(0, _env_int("KG_QA_LLM_MAX_RETRIES", 2))
    base_backoff_s = max(0.1, _env_float("KG_QA_LLM_RETRY_BACKOFF_SECONDS", 0.8))
    last_exc = None

    for attempt in range(max_retries + 1):
        try:
            return requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=(10, timeout_s),
                stream=stream,
            )
        except requests.exceptions.RequestException as e:
            last_exc = e
            if attempt >= max_retries:
                raise
            sleep_s = base_backoff_s * (2 ** attempt)
            time.sleep(sleep_s)

    if last_exc is not None:
        raise last_exc
    raise RuntimeError("deepseek request failed unexpectedly")


def _qa_skip_prop_keys():
    """检索时合并进关键词的节点/边属性黑名单（避免向量等大字段撑爆 prompt）。"""
    raw = os.getenv("KG_QA_SKIP_PROPERTY_KEYS", "embedding,vector,contentEmbedding")
    return [x.strip() for x in raw.split(",") if x.strip()]


def _cache_get(key):
    if not key:
        return None
    return tiered_cache_get(_QA_ANSWER_CACHE_NS, key)


def _cache_set(key, value, ttl_seconds):
    if not key:
        return
    tiered_cache_set(_QA_ANSWER_CACHE_NS, key, value, max(1, int(ttl_seconds)))


def _call_chat_completion(messages, model_name, temperature=0.2, timeout_env="KG_QA_LLM_TIMEOUT_SECONDS"):
    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature
    }
    timeout_s = max(10, _env_int(timeout_env, 60))
    resp = _deepseek_post(payload=payload, timeout_s=timeout_s, stream=False)
    resp.raise_for_status()
    data = resp.json() or {}
    return str(((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()


def _call_chat_completion_raw(
    messages,
    model_name,
    temperature=0.2,
    tools=None,
    tool_choice=None,
    timeout_env="KG_QA_LLM_TIMEOUT_SECONDS",
):
    """
    返回首个 choice 的 message 原始结构，用于 function-calling。
    """
    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
    }
    if tools:
        payload["tools"] = tools
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice
    timeout_s = max(10, _env_int(timeout_env, 60))
    resp = _deepseek_post(payload=payload, timeout_s=timeout_s, stream=False)
    resp.raise_for_status()
    data = resp.json() or {}
    msg = ((data.get("choices") or [{}])[0].get("message") or {})
    if not isinstance(msg, dict):
        msg = {"role": "assistant", "content": str(msg or "")}
    return msg


def _safe_json_load_dict(s):
    try:
        obj = json.loads(s or "{}")
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _truncate_fc_query(text, cap=220):
    q = str(text or "").strip()
    if not q:
        return ""
    if len(q) > cap:
        return q[:cap]
    return q


def _build_kg_function_tools():
    return [
        {
            "type": "function",
            "function": {
                "name": "get_user_project_ids",
                "description": "获取当前用户有权限访问的项目 ID 列表。",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "retrieve_project_kg",
                "description": "在指定项目中检索知识图谱证据。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "项目 ID"},
                        "query": {"type": "string", "description": "检索问句或关键词"},
                        "top_k": {"type": "integer", "description": "返回条数上限"},
                    },
                    "required": ["project_id", "query"],
                },
            },
        },
    ]


def _dispatch_kg_function_call(
    tool_name,
    args,
    *,
    user_id,
    username,
    allowed_projects,
    retrieval_query,
    top_k_per_project,
):
    allowed_set = set(allowed_projects or [])
    if tool_name == "get_user_project_ids":
        return {
            "ok": True,
            "tool": tool_name,
            "projects": sorted(allowed_set),
            "evidence": [],
        }

    if tool_name == "retrieve_project_kg":
        pid = str((args or {}).get("project_id") or "").strip()
        if not pid:
            return {"ok": False, "tool": tool_name, "error": "project_id is required", "evidence": []}
        if pid not in allowed_set:
            return {
                "ok": False,
                "tool": tool_name,
                "error": "project access denied",
                "project_id": pid,
                "evidence": [],
            }
        q = _truncate_fc_query((args or {}).get("query") or retrieval_query)
        if not q:
            q = _truncate_fc_query(retrieval_query)
        tk = (args or {}).get("top_k")
        try:
            tk_i = int(tk)
        except Exception:
            tk_i = int(top_k_per_project or 10)
        # top_k<=0 视为不限量；否则做安全上限保护。
        if tk_i > 0:
            tk_i = max(1, min(20, tk_i))
        ev = retrieve_project_kg(pid, q, top_k=tk_i)
        return {
            "ok": True,
            "tool": tool_name,
            "project_id": pid,
            "query": q,
            "top_k": tk_i,
            "evidence": ev,
            "evidence_count": len(ev or []),
        }

    return {"ok": False, "tool": tool_name, "error": "unsupported tool", "evidence": []}


def _function_call_retrieve_enhance(
    *,
    enabled,
    query,
    retrieval_query,
    user_id,
    username,
    project_ids,
    base_evidence,
    top_k_per_project,
):
    """
    受控 function-calling 检索增强：
    - 白名单工具
    - 参数校验与项目权限约束
    - 最多 N 步
    """
    if not enabled:
        return base_evidence, {"enabled": False, "executed": False, "reason": "disabled"}
    if not project_ids:
        return base_evidence, {"enabled": True, "executed": False, "reason": "no_projects"}

    max_steps = max(1, min(5, _env_int("KG_QA_FUNCTION_CALLING_MAX_STEPS", 3)))
    model_name = "deepseek-chat"
    tools = _build_kg_function_tools()
    fc_evidence = []
    call_logs = []
    call_guard = set()

    evidence_preview = []
    for idx, e in enumerate((base_evidence or [])[:8], start=1):
        if not isinstance(e, dict):
            continue
        snippet = str(e.get("snippet") or "").replace("\n", " ")[:140]
        evidence_preview.append(f"{idx}. pid={e.get('project_id')} src={e.get('source')} {snippet}")
    evidence_preview_text = "\n".join(evidence_preview) if evidence_preview else "（当前无证据）"

    messages = [
        {
            "role": "system",
            "content": (
                "你是金融图谱检索编排助手。你只能通过函数调用补充证据，禁止编造证据。"
                "如果已有证据足够，可直接停止调用函数。"
                "优先调用 retrieve_project_kg；必要时可先调用 get_user_project_ids。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"用户问题：{query}\n"
                f"检索串：{retrieval_query}\n"
                f"可用项目：{sorted(project_ids)}\n"
                f"当前证据预览：\n{evidence_preview_text}\n"
                "请按需调用工具补充证据。若无需继续，直接给出一句“完成”。"
            ),
        },
    ]

    try:
        for _ in range(max_steps):
            assistant_msg = _call_chat_completion_raw(
                messages=messages,
                model_name=model_name,
                temperature=0,
                tools=tools,
                tool_choice="auto",
            )
            role = str(assistant_msg.get("role") or "assistant")
            content = str(assistant_msg.get("content") or "")
            tool_calls = assistant_msg.get("tool_calls") or []
            if not isinstance(tool_calls, list):
                tool_calls = []

            assistant_to_append = {"role": role, "content": content}
            if tool_calls:
                assistant_to_append["tool_calls"] = tool_calls
            messages.append(assistant_to_append)

            if not tool_calls:
                break

            for tc in tool_calls:
                if not isinstance(tc, dict):
                    continue
                tc_id = str(tc.get("id") or uuid.uuid4().hex)
                fn = tc.get("function") or {}
                tool_name = str(fn.get("name") or "").strip()
                args = _safe_json_load_dict(fn.get("arguments") or "{}")
                dedup_key = json.dumps(
                    {"name": tool_name, "args": args},
                    ensure_ascii=False,
                    sort_keys=True,
                )
                if dedup_key in call_guard:
                    tool_res = {
                        "ok": True,
                        "tool": tool_name,
                        "skipped": True,
                        "reason": "duplicate_call",
                        "evidence": [],
                    }
                else:
                    call_guard.add(dedup_key)
                    tool_res = _dispatch_kg_function_call(
                        tool_name,
                        args,
                        user_id=user_id,
                        username=username,
                        allowed_projects=project_ids,
                        retrieval_query=retrieval_query,
                        top_k_per_project=top_k_per_project,
                    )
                if tool_res.get("ok") and isinstance(tool_res.get("evidence"), list):
                    fc_evidence.extend(tool_res.get("evidence") or [])

                call_logs.append(
                    {
                        "tool": tool_name,
                        "ok": bool(tool_res.get("ok")),
                        "project_id": tool_res.get("project_id"),
                        "evidence_count": len(tool_res.get("evidence") or []),
                        "error": tool_res.get("error"),
                        "skipped": bool(tool_res.get("skipped")),
                    }
                )
                tool_echo = dict(tool_res)
                if isinstance(tool_echo.get("evidence"), list):
                    tool_echo["evidence"] = _evidence_snippets_for_debug(tool_echo["evidence"], max_items=8, max_chars=220)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "content": json.dumps(tool_echo, ensure_ascii=False),
                    }
                )
    except Exception as e:
        traceback.print_exc()
        return base_evidence, {
            "enabled": True,
            "executed": bool(call_logs),
            "error": str(e),
            "tool_calls": call_logs,
            "added_evidence": 0,
        }

    merged = aggregate_evidence(
        {"base": list(base_evidence or []), "fc": list(fc_evidence or [])},
        max_items=max(8, _env_int("KG_QA_MERGED_EVIDENCE_MAX", 14)),
    )
    return merged, {
        "enabled": True,
        "executed": True,
        "max_steps": max_steps,
        "tool_calls": call_logs,
        "added_evidence": len(fc_evidence or []),
        "final_evidence": len(merged or []),
    }


def _stream_chat_completion_chunks(
    messages, model_name, temperature=0.2, timeout_env="KG_QA_LLM_TIMEOUT_SECONDS"
):
    """
    OpenAI 兼容流式（DeepSeek /chat/completions stream=true）。
    每次 yield dict：可选键 "reasoning"（reasoning_content）、可选键 "content"（正文）。
    """
    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "stream": True,
    }
    timeout_s = max(30, _env_int(timeout_env, 120))
    max_retries = max(0, _env_int("KG_QA_LLM_STREAM_MAX_RETRIES", 2))
    got_any_chunk = False
    for attempt in range(max_retries + 1):
        try:
            with _deepseek_post(payload=payload, timeout_s=timeout_s, stream=True) as resp:
                resp.raise_for_status()
                for raw in resp.iter_lines(decode_unicode=True):
                    if not raw:
                        continue
                    line = raw.strip()
                    if line.startswith("data:"):
                        line = line[5:].strip()
                    if line == "[DONE]":
                        return
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    for ch in obj.get("choices") or []:
                        delta = ch.get("delta") or {}
                        reasoning_piece = delta.get("reasoning_content") or ""
                        content_piece = delta.get("content") or ""
                        out = {}
                        if reasoning_piece:
                            out["reasoning"] = reasoning_piece
                        if content_piece:
                            out["content"] = content_piece
                        if out:
                            got_any_chunk = True
                            yield out
            return
        except requests.exceptions.RequestException:
            if got_any_chunk or attempt >= max_retries:
                raise
            time.sleep(0.6 * (2 ** attempt))


_NO_KG_EVIDENCE_PREFIX = (
    "【重要】本轮未向模型提供任何来自用户知识图谱的证据片段。"
    "请勿使用「根据您图谱」「图谱里」「根据你构建的知识图谱」等表述；"
    "应基于常识与公开信息作答，必要时可说明信息来源为公开报道或一般知识。\n\n"
)


def _build_general_messages(
    query, deep_think, detail_level, prior_messages, no_kg_evidence_prefix=False
):
    """与 query_capability_agent.generate_general_answer 相同 messages 结构。"""
    model_name = "deepseek-reasoner" if _parse_bool(deep_think, False) else "deepseek-chat"
    system_prompt, style_hint, extra_guidance = build_general_answer_prompt_parts(query, detail_level, deep_think=_parse_bool(deep_think, False))
    prefix = _NO_KG_EVIDENCE_PREFIX if no_kg_evidence_prefix else ""
    prompt = (
        f"{prefix}"
        f"{style_hint}\n"
        f"{extra_guidance}\n"
        "请结合上文理解指代，只针对「当前问题」作答。\n"
        f"当前问题：{query}"
    )
    msgs = [{"role": "system", "content": system_prompt}]
    if prior_messages:
        for m in prior_messages:
            role = m.get("role") if isinstance(m, dict) else None
            if role not in ("user", "assistant"):
                continue
            content = _truncate_chat_text(m.get("content") if isinstance(m, dict) else None, 2400)
            if content:
                msgs.append({"role": role, "content": content})
    msgs.append({"role": "user", "content": prompt})
    return msgs, model_name, 0.3


def _build_platform_guidance_messages(query, fine_intent, deep_think, detail_level, prior_messages):
    """与 generate_platform_guidance_answer 对齐的 messages，用于流式接口。"""
    model_name = "deepseek-reasoner" if _parse_bool(deep_think, False) else "deepseek-chat"
    style_hint = (
        "回答尽量短，步骤用自然段或少量分点即可。"
        if detail_level == "brief"
        else "回答可稍长，条理清楚，但不要套固定八股模板。"
    )
    prompt = (
        f"{style_hint}\n"
        f"当前识别意图标签：{fine_intent}\n"
        "请结合上文理解指代，只针对「当前问题」作答。\n"
        f"用户问题：{query}"
    )
    msgs = [{"role": "system", "content": platform_guidance_system_prompt(fine_intent)}]
    if prior_messages:
        for m in prior_messages:
            role = m.get("role") if isinstance(m, dict) else None
            if role not in ("user", "assistant"):
                continue
            content = _truncate_chat_text(m.get("content") if isinstance(m, dict) else None, 2400)
            if content:
                msgs.append({"role": role, "content": content})
    msgs.append({"role": "user", "content": prompt})
    return msgs, model_name, 0.25


def generate_platform_guidance_answer(
    query, fine_intent, deep_think=False, detail_level="brief", prior_messages=None
):
    return capability_generate_platform_guidance_answer(
        query=query,
        fine_intent=fine_intent,
        deep_think=deep_think,
        detail_level=detail_level,
        parse_bool_fn=_parse_bool,
        call_chat_completion_fn=_call_chat_completion,
        prior_messages=prior_messages,
    )


def _build_evidence_messages(query, evidence, deep_think, detail_level, prior_messages, web_attempted=False):
    """与 generate_answer_from_evidence 相同 messages（需 evidence 非空）。"""
    if evidence:
        _enrich_evidence_project_names(evidence)
    model_name = "deepseek-reasoner" if _parse_bool(deep_think, False) else "deepseek-chat"
    prompt = _build_answer_prompt(query, evidence, detail_level, web_attempted=web_attempted, deep_think=deep_think)
    msgs = [
        {
            "role": "system",
            "content": (
                "你是严谨且专业的金融知识图谱分析助手。请以证据为锚点作答，并在此基础上进行有边界的专业推演："
                "可以结合金融常识、行业机制、风险传导路径做分析，但不得脱离证据事实。"
                "对关键观点请区分事实依据与推断结论；证据不足时不要拒答，应给出条件化判断、潜在情景和待补充数据项。"
                "输出保持自然分析文风，不强制固定报告模板。"
                "用户消息中会要求：正文直接从段落开始（勿写「## 回答」），仅用唯一二级标题「## 参考与证据」引出附录；附录中网页条目须含 Markdown 链接形式的 URL。"
            ) if _parse_bool(deep_think, False) else (
                "你是严谨的金融知识图谱问答助手：只依据用户提供的证据链作答，不臆测、不补全缺失数字。"
                "用户消息中会要求：正文直接从段落开始（勿写「## 回答」），仅用唯一二级标题「## 参考与证据」引出附录；附录中网页条目须含 Markdown 链接形式的 URL。"
            ),
        },
    ]
    if prior_messages:
        for m in prior_messages:
            role = (m.get("role") or "").strip()
            if role not in ("user", "assistant"):
                continue
            c = _truncate_chat_text(m.get("content"), 2400)
            if c:
                msgs.append({"role": role, "content": c})
    msgs.append({"role": "user", "content": prompt})
    return msgs, model_name, 0.2


def _now_sql():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def _new_session_id():
    return f"session_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"


def _make_session_title(text):
    t = str(text or "").strip().replace("\n", " ")
    return t[:60] if t else "新会话"


def _safe_json_dumps(obj):
    import json
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return "{}"


def _ensure_chat_session(user_id, session_id, first_query):
    """
    确保 chat_session 存在，不存在则创建。
    """
    uid = str(user_id or "").strip()
    sid = str(session_id or "").strip() or _new_session_id()
    now = _now_sql()
    client = None
    try:
        client = get_client()
        with client.cursor() as cursor:
            cursor.execute(
                """
                SELECT session_id
                FROM finkg1.chat_session
                WHERE session_id = %s
                LIMIT 1
                """,
                (sid,)
            )
            exists = cursor.fetchone()
            if exists:
                cursor.execute(
                    """
                    UPDATE finkg1.chat_session
                    SET updated_at = %s
                    WHERE session_id = %s
                    """,
                    (now, sid)
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO finkg1.chat_session
                    (session_id, user_id, title, created_at, updated_at, last_message_at, message_count, is_deleted)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (sid, uid, _make_session_title(first_query), now, now, now, 0, 0)
                )
        client.commit()
        return sid
    except Exception:
        traceback.print_exc()
        return sid
    finally:
        if client:
            client.close()


def _truncate_chat_text(s, max_len=2400):
    t = str(s or "").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _session_history_for_intent(prior_msgs):
    """本会话内已持久化的多轮对话摘要，供意图/检索拼接。"""
    if not prior_msgs:
        return ""
    parts = []
    for m in prior_msgs:
        role = (m.get("role") or "").strip()
        label = "用户" if role == "user" else "助手"
        c = _truncate_chat_text(m.get("content"), 1800)
        if c:
            parts.append(f"{label}：{c}")
    return "\n".join(parts)


def _latest_user_query_text(prior_msgs):
    if not prior_msgs:
        return ""
    for m in reversed(prior_msgs):
        if (m.get("role") or "").strip() != "user":
            continue
        content = _truncate_chat_text(m.get("content"), 240)
        if content:
            return content
    return ""


def _rewrite_deictic_followup_query(user_query, prior_msgs):
    """把“这个行业/该板块/它”类追问改写为带上轮主题的检索锚点。"""
    q = str(user_query or "").strip()
    if not q:
        return q
    if not prior_msgs:
        return q

    deictic_markers = (
        "这个行业",
        "该行业",
        "这个板块",
        "该板块",
        "这个领域",
        "该领域",
        "这个赛道",
        "该赛道",
        "这个方向",
        "该方向",
        "这个主题",
        "该主题",
        "这个项目",
        "该项目",
        "这家公司",
        "该公司",
        "这个企业",
        "该企业",
        "这个",
        "该",
        "其",
        "它",
    )
    if not any(marker in q for marker in deictic_markers):
        return q

    latest_user = _latest_user_query_text(prior_msgs)
    if not latest_user:
        return q
    if latest_user in q:
        return q

    return f"{latest_user}；{q}"


def _build_retrieval_query(user_query, prior_msgs):
    """检索用语：当前句 + 上文，便于指代消解。"""
    rewritten_query = _rewrite_deictic_followup_query(user_query, prior_msgs)
    if not prior_msgs:
        return rewritten_query
    hist = _session_history_for_intent(prior_msgs)
    if not hist:
        return rewritten_query
    combined = f"{hist}\n\n【当前问题】\n{rewritten_query}"
    cap = max(3000, _env_int("KG_QA_RETRIEVAL_QUERY_MAX_CHARS", 8000))
    if len(combined) > cap:
        combined = combined[-cap:]
    return combined


def _extract_anchor_query_for_retrieval(combined_query: str) -> str:
    """
    从拼接后的检索串中取出「当前问题」锚点，用于 Neo4j 关键词命中与分词。
    避免会话上文过长导致：① CONTAINS 整句不可能命中；② 分词仅取前 N 个词时被历史占满。
    """
    q = str(combined_query or "").strip()
    marker = "【当前问题】"
    if marker in q:
        tail = q.rsplit(marker, 1)[-1].strip()
        if tail:
            return tail
    cap = max(80, _env_int("KG_QA_ANCHOR_QUERY_MAX_CHARS", 600))
    if len(q) > cap:
        return q[-cap:].strip()
    return q


def _split_retrieval_tokens(text: str, max_tokens: int) -> list:
    """按标点切分检索词；中文无空格时也能切成多个片段。"""
    query_text = str(text or "").strip().lower()
    token_candidates = re.split(r"[\s,，。;；:：!?！？()（）\[\]{}]+", query_text)
    tokens = []
    seen = set()
    for t in token_candidates:
        t = t.strip()
        if len(t) < 2:
            continue
        if _is_noisy_retrieval_token(t):
            continue
        if t not in seen:
            seen.add(t)
            tokens.append(t)
        if len(tokens) >= max_tokens:
            break
    return tokens


def _is_noisy_retrieval_token(token: str) -> bool:
    """过滤过于泛化的问句词，降低跨项目误命中。"""
    t = str(token or "").strip().lower()
    if not t:
        return True
    noisy = {
        "情况",
        "如何",
        "请问",
        "一下",
        "这个",
        "那个",
        "哪些",
        "什么",
        "怎么",
        "怎样",
        "问题",
        "当前",
        "最近",
        "相关",
        "信息",
        "数据",
        "表现",
        "板块",
        "用户",
        "助手",
        "当前问题",
    }
    if t in noisy:
        return True
    if re.fullmatch(r"[\u4e00-\u9fff]+", t):
        if len(t) <= 3 and any(ch in t for ch in "的吗呢吧啊呀嘛了"):
            return True
        if t.endswith(("情况", "如何", "问题")):
            return True
    return False


def _topic_expanded_retrieval_tokens(anchor: str) -> list:
    """
    特定主题（地缘/冲突等）下补充检索词元，使图谱 CONTAINS 能命中「仅有实体名」的节点，
    而不依赖问句整句与节点文案完全一致。
    """
    a = str(anchor or "").strip()
    if not a:
        return []
    out = []
    seen = set()
    # 俄乌相关：用户问战争时间时，图谱里往往是「乌克兰」经济与事件节点，未必含「俄乌战争」全文
    _ru_ua_markers = (
        "俄乌战争",
        "俄乌冲突",
        "乌克兰战争",
        "乌俄战争",
        "俄罗斯乌克兰",
        "入侵乌克兰",
        "俄乌",
    )
    if any(m in a for m in _ru_ua_markers) or ("乌克兰" in a and ("战争" in a or "冲突" in a or "局势" in a)):
        for t in ("乌克兰", "俄罗斯", "俄乌"):
            if t not in seen:
                seen.add(t)
                out.append(t)

    # 半导体主题：用户问“半导体板块”时，图谱里常写作“芯片/集成电路/晶圆”等。
    _semi_markers = (
        "半导体",
        "芯片",
        "集成电路",
        "晶圆",
        "ic",
        "soc",
    )
    if any(m in a.lower() for m in _semi_markers):
        for t in ("半导体", "芯片", "集成电路", "晶圆", "ic", "chip", "semiconductor"):
            if t not in seen:
                seen.add(t)
                out.append(t)
    return out[:8]


def _anchor_cjk_character_grams(anchor: str, max_chars: int = 48, max_grams: int = 16) -> list:
    """
    对含汉字的锚点做 2～4 字滑动窗，使「乌克兰」等实体可命中仅含该词、不含整句的图谱节点。
    （若只靠标点切分整句为一个 token，Neo4j ctx CONTAINS 无法匹配碎片化存储的实体。）

    纯拉丁/数字锚点不拆字，避免 uk、rai 等噪声。
    """
    a = str(anchor or "").strip()
    if not a or not re.search(r"[\u4e00-\u9fff]", a):
        return []
    cap = min(len(a), max(0, int(max_chars or 48)))
    out = []
    seen = set()
    for size in (2, 3, 4):
        for i in range(0, max(0, cap - size + 1)):
            gram = (a[i : i + size]).strip().lower()
            if len(gram) < 2 or gram in seen:
                continue
            if _is_noisy_retrieval_token(gram):
                continue
            seen.add(gram)
            out.append(gram)
            if len(out) >= max_grams:
                return out
    return out


def _merge_retrieval_tokens(combined_query: str, max_tokens: int = 20) -> tuple:
    """
    合并锚点与全文分词：优先锚点标点切分 → **锚点汉字滑动窗** → 再补充全文。
    滑动窗保证当前问句中的专有名词不会因「整句一个 token」或会话历史抢先占满 token 配额而错失。
    """
    anchor = _extract_anchor_query_for_retrieval(combined_query)
    primary = _split_retrieval_tokens(anchor, max_tokens=max_tokens)
    cjk_grams = _anchor_cjk_character_grams(anchor)
    topic_x = _topic_expanded_retrieval_tokens(anchor)
    secondary = _split_retrieval_tokens(combined_query, max_tokens=max_tokens)
    merged = []
    seen = set()
    for t in primary + cjk_grams + topic_x + secondary:
        if t not in seen:
            seen.add(t)
            merged.append(t)
        if len(merged) >= max_tokens:
            break
    return anchor, merged


def load_prior_messages_for_session(session_id, user_id, username=None, uid=None, max_messages=24):
    """
    从 MySQL 读取本会话内、本轮写入之前的历史消息（user/assistant）。
    校验 session 归属 user_id / username / uid 之一。
    """
    sid = str(session_id or "").strip()
    candidates = []
    for raw in (user_id, username, uid):
        if raw is None:
            continue
        t = str(raw).strip()
        if t and t not in candidates:
            candidates.append(t)
    if not sid or not candidates:
        return []
    client = None
    try:
        client = get_client()
        with client.cursor() as cursor:
            placeholders = ",".join(["%s"] * len(candidates))
            cursor.execute(
                f"""
                SELECT session_id
                FROM finkg1.chat_session
                WHERE session_id = %s AND is_deleted = 0 AND TRIM(user_id) IN ({placeholders})
                LIMIT 1
                """,
                tuple([sid] + candidates),
            )
            if not cursor.fetchone():
                return []
            cursor.execute(
                """
                SELECT role, content
                FROM finkg1.chat_message
                WHERE session_id = %s
                ORDER BY id ASC
                """,
                (sid,),
            )
            rows = cursor.fetchall() or []
    except Exception:
        traceback.print_exc()
        return []
    finally:
        if client:
            client.close()
    msgs = []
    for r in rows:
        msgs.append(
            {"role": str(r.get("role") or ""), "content": str(r.get("content") or "")}
        )
    if len(msgs) > max_messages:
        msgs = msgs[-max_messages:]
    return msgs


def _parse_chat_message_extra(raw_extra):
    if isinstance(raw_extra, dict):
        return raw_extra
    if raw_extra in (None, ""):
        return {}
    if isinstance(raw_extra, str):
        try:
            parsed = json.loads(raw_extra)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _serialize_chat_history_row(row):
    extra = _parse_chat_message_extra((row or {}).get("extra_json"))
    item = {
        "role": str((row or {}).get("role") or ""),
        "content": str((row or {}).get("content") or ""),
    }
    reasoning = str(extra.get("reasoning") or "").strip()
    deep_think = _parse_bool(extra.get("deep_think"), False) or bool(reasoning)
    if deep_think:
        item["deep_think"] = True
    if reasoning:
        item["reasoning"] = reasoning
    evidence = extra.get("evidence")
    if isinstance(evidence, list):
        item["evidence"] = evidence
    web_search_meta = extra.get("web_search_meta")
    if isinstance(web_search_meta, dict):
        item["web_search_meta"] = web_search_meta
    quality_hints = extra.get("quality_hints")
    if isinstance(quality_hints, list):
        item["quality_hints"] = quality_hints
    if extra.get("web_search_attempted") is not None:
        item["web_search_attempted"] = _parse_bool(extra.get("web_search_attempted"), False)
    if extra.get("kg_lookup_status") is not None:
        item["kg_lookup_status"] = str(extra.get("kg_lookup_status") or "")
    if extra.get("intent_coarse") is not None:
        item["intent_coarse"] = str(extra.get("intent_coarse") or "")
    if extra.get("intent") is not None:
        item["intent"] = str(extra.get("intent") or "")
    return item


def _append_chat_message(session_id, role, content, intent="", model_used="", confidence=None, extra=None):
    sid = str(session_id or "").strip()
    if not sid:
        return
    now = _now_sql()
    client = None
    try:
        client = get_client()
        with client.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO finkg1.chat_message
                (session_id, role, content, intent, model_used, confidence, extra_json, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    sid,
                    str(role or "user"),
                    str(content or ""),
                    str(intent or ""),
                    str(model_used or ""),
                    confidence if confidence is not None else None,
                    _safe_json_dumps(extra or {}),
                    now,
                )
            )
            cursor.execute(
                """
                UPDATE finkg1.chat_session
                SET updated_at = %s,
                    last_message_at = %s,
                    message_count = message_count + 1
                WHERE session_id = %s
                """,
                (now, now, sid)
            )
        client.commit()
    except Exception:
        traceback.print_exc()
    finally:
        if client:
            client.close()


def persist_chat_turn(user_id, session_id, user_query, result_payload):
    """
    持久化一轮问答（用户消息 + 助手消息）。
    """
    data = (result_payload or {}).get("data") or {}
    sid = _ensure_chat_session(user_id, session_id, user_query)
    _append_chat_message(
        session_id=sid,
        role="user",
        content=user_query,
        intent=data.get("intent", ""),
        extra={"type": "user_input"},
    )
    _append_chat_message(
        session_id=sid,
        role="assistant",
        content=data.get("answer", ""),
        intent=data.get("intent", ""),
        model_used=data.get("model_used", ""),
        confidence=data.get("confidence", None),
        extra={
            "deep_think": bool(str(data.get("reasoning") or "").strip()),
            "reasoning": data.get("reasoning", ""),
            "intent": data.get("intent", ""),
            "intent_coarse": data.get("intent_coarse", ""),
            "kg_lookup_status": data.get("kg_lookup_status", ""),
            "evidence": data.get("evidence", []),
            "web_search_meta": data.get("web_search_meta") or {},
            "web_search_attempted": bool(data.get("web_search_attempted")),
            "projects_searched": data.get("projects_searched", []),
            "stats": data.get("stats", {}),
            "quality_hints": data.get("quality_hints", []),
        },
    )
    return sid


def _graph_project_creator_candidates(user_id, username=None):
    """
    graph_project.creator 可能存 user_data.user_name，也可能存数字 id 的字符串。
    请求里常传 user_data.id；若同一 id 在 user_data 多行（脏数据），应传 username 消歧。
    """
    raw = str(user_id or "").strip()
    if not raw:
        return []
    cand = []
    seen = set()

    def _add(x):
        s = str(x).strip()
        if s and s not in seen:
            seen.add(s)
            cand.append(s)

    _add(raw)
    un_req = str(username or "").strip()
    if un_req:
        _add(un_req)
    client = None
    try:
        client = get_client()
        with client.cursor() as cursor:
            if raw.isdigit():
                cursor.execute(
                    "SELECT DISTINCT user_name FROM user_data WHERE id = %s",
                    (int(raw),),
                )
                rows = cursor.fetchall() or []
                names = [str(r["user_name"]).strip() for r in rows if r.get("user_name")]
                if len(names) <= 1:
                    for n in names:
                        _add(n)
                else:
                    if un_req and un_req in names:
                        _add(un_req)
                    else:
                        for n in names:
                            _add(n)
            else:
                cursor.execute(
                    "SELECT DISTINCT id FROM user_data WHERE user_name = %s",
                    (raw,),
                )
                for row in cursor.fetchall() or []:
                    if row and row.get("id") is not None:
                        _add(str(row["id"]))
    except Exception:
        traceback.print_exc()
    finally:
        if client:
            client.close()
    return cand


def _is_admin_identity(user_id=None, username=None, uid=None, explicit_is_admin=False):
    """尽量仅靠后端可得信息判断管理员身份，避免依赖前端传参是否完整。"""
    if _parse_bool(explicit_is_admin, False):
        return True

    raw_values = [user_id, uid, username]
    seen = set()
    candidates = []

    def _add(value):
        s = str(value or "").strip()
        if s and s not in seen:
            seen.add(s)
            candidates.append(s)

    for value in raw_values:
        _add(value)

    for ident in (user_id, uid):
        for value in _graph_project_creator_candidates(ident, username):
            _add(value)

    for value in list(candidates):
        if value == "1" or value.lower() == "admin":
            return True
    return False


def get_user_project_ids(user_id, username=None, uid=None, is_admin=False):
    """
    Tool-1: 根据 user_id（多为 user_data.id）获取该用户可见项目列表。
    建议同时传 username（与 user_data.user_name 一致），以便与 graph_project.creator 对齐。
    返回 list[str]，异常时返回空数组。
    """
    is_admin = _is_admin_identity(user_id, username=username, uid=uid, explicit_is_admin=is_admin)

    candidates = []
    if not is_admin:
        # 同时接受 user_id / uid：前端在不同页面里这两个字段可能其一为空。
        # 任一字段可解析到同一账号，都应纳入项目可见范围，避免只命中部分项目。
        seen = set()
        for ident in (user_id, uid):
            one = _graph_project_creator_candidates(ident, username)
            for c in one:
                s = str(c).strip()
                if s and s not in seen:
                    seen.add(s)
                    candidates.append(s)
        if not candidates:
            return []

    client = None
    try:
        client = get_client()
        with client.cursor() as cursor:
            if is_admin:
                cursor.execute(
                    """
                    SELECT id
                    FROM finkg1.graph_project
                    ORDER BY create_time DESC
                    """
                )
            else:
                ph = ",".join(["%s"] * len(candidates))
                cursor.execute(
                    f"""
                    SELECT id
                    FROM finkg1.graph_project
                    WHERE TRIM(CAST(creator AS CHAR)) IN ({ph})
                    ORDER BY create_time DESC
                    """,
                    tuple(candidates),
                )
            rows = cursor.fetchall() or []
        return [str(row.get("id")) for row in rows if row and row.get("id") is not None]
    except Exception:
        traceback.print_exc()
        return []
    finally:
        if client:
            client.close()


def _fetch_graph_project_name_map(project_ids):
    """project_id -> project_name（MySQL graph_project）；查不到则不在 map 中。"""
    ids = []
    seen = set()
    for x in project_ids or []:
        s = str(x).strip() if x is not None else ""
        if s and s not in seen:
            seen.add(s)
            ids.append(s)
    if not ids:
        return {}
    client = None
    try:
        client = get_client()
        ph = ",".join(["%s"] * len(ids))
        with client.cursor() as cursor:
            cursor.execute(
                f"SELECT id, project_name FROM finkg1.graph_project WHERE id IN ({ph})",
                tuple(ids),
            )
            rows = cursor.fetchall() or []
        out = {}
        for r in rows or []:
            if not r:
                continue
            pid = str(r.get("id") or "").strip()
            if not pid:
                continue
            pname = (r.get("project_name") or "").strip()
            out[pid] = pname or pid
        return out
    except Exception:
        traceback.print_exc()
        return {}
    finally:
        if client:
            client.close()


def _enrich_evidence_project_names(evidence):
    """为每条 evidence 写入 project_name，供提示词与引用展示。"""
    if not evidence:
        return evidence
    pids = []
    for e in evidence:
        if isinstance(e, dict) and e.get("project_id") is not None:
            pids.append(str(e["project_id"]).strip())
    m = _fetch_graph_project_name_map(pids)
    for e in evidence:
        if not isinstance(e, dict):
            continue
        pid = str(e.get("project_id") or "").strip()
        e["project_name"] = m.get(pid) or pid
    return evidence


def _neighbor_context_score(context: str, tokens: list) -> float:
    """邻接节点若与用户词重合略加分，仍低于直接文本命中。"""
    ctx = (context or "").lower()
    hits = sum(1 for t in (tokens or []) if t and len(str(t).strip()) >= 2 and str(t).lower() in ctx)
    base = 0.72
    return base + min(0.08, hits * 0.015)


def _neo4j_neighbor_evidence(project_text: str, seed_element_ids: list, exclude_ids: set, tokens: list):
    """
    基于 Neo4j 图上一跳邻接边扩展证据（突出图库相对「表 + LIKE」的差异）。
    seed_element_ids: 文本命中 / 兜底节点的 elementId 列表。
    """
    if not _parse_bool(os.getenv("KG_NEO4J_EXPAND_ENABLED", "true"), True):
        return []
    if not seed_element_ids:
        return []
    limit = max(1, _env_int("KG_NEO4J_EXPAND_MAX_TOTAL", 12))
    seed_cap = max(1, _env_int("KG_NEO4J_EXPAND_MAX_SEEDS", 8))
    seeds = [str(s).strip() for s in seed_element_ids if str(s).strip()][:seed_cap]
    if not seeds:
        return []
    excl = [str(x) for x in exclude_ids if str(x).strip()]
    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (seed:KnowledgeNode)
                WHERE elementId(seed) IN $seed_ids
                  AND toString(seed.project_id) = toString($project_id)
                MATCH (seed)-[r]-(nb:KnowledgeNode)
                WHERE toString(nb.project_id) = toString($project_id)
                WITH nb, r,
                     CASE
                       WHEN nb.context IS NOT NULL AND trim(toString(nb.context)) <> ''
                       THEN trim(toString(nb.context))
                       ELSE trim(coalesce(toString(nb.value), toString(nb.name), ''))
                     END AS nb_display
                WHERE trim(nb_display) <> ''
                  AND (size($exclude_ids) = 0 OR NOT elementId(nb) IN $exclude_ids)
                WITH nb,
                     collect(DISTINCT type(r)) AS rel_types,
                     collect(DISTINCT trim(coalesce(toString(r.value), '')
                       + CASE WHEN trim(coalesce(toString(r.eventRel), '')) <> ''
                         THEN ':' + trim(toString(r.eventRel)) ELSE '' END))[0..15] AS rel_hints
                RETURN elementId(nb) AS node_id,
                       CASE
                         WHEN nb.context IS NOT NULL AND trim(toString(nb.context)) <> ''
                         THEN trim(toString(nb.context))
                         ELSE trim(coalesce(toString(nb.value), toString(nb.name), ''))
                       END AS context,
                       coalesce(nb.project_id, $project_id) AS project_id,
                       rel_types,
                       rel_hints
                LIMIT $limit
                """,
                {
                    "project_id": project_text,
                    "seed_ids": seeds,
                    "exclude_ids": excl,
                    "limit": int(limit),
                },
            )
            rows = list(result)
    except Exception:
        traceback.print_exc()
        return []

    out = []
    for row in rows:
        ctx = str(row.get("context") or "").strip()
        if not ctx:
            continue
        rel_types = row.get("rel_types") or []
        if not isinstance(rel_types, list):
            rel_types = []
        rel_preview = "、".join(str(x) for x in rel_types[:6] if x) or "（未命名类型）"
        nid = str(row.get("node_id") or "")
        sc = _neighbor_context_score(ctx, tokens)
        rel_hints_raw = row.get("rel_hints") or []
        if not isinstance(rel_hints_raw, list):
            rel_hints_raw = []
        hints = []
        for h in rel_hints_raw[:12]:
            hs = str(h).strip()
            if hs and hs not in hints:
                hints.append(hs)
        rel_line = ""
        if hints:
            rel_line = "边上语义：" + "；".join(hints[:8]) + "\n"
        snippet = (
            f"[图谱扩展·Neo4j关联路径] 由检索命中节点经 **1-hop** 边扩展到的相邻节点。\n"
            f"{rel_line}"
            f"Neo4j 动态关系类型标签：{rel_preview}。\n相邻节点摘录：{ctx[:650]}"
        )
        out.append(
            {
                "project_id": str(row.get("project_id") or project_text),
                "node_id": nid,
                "score": float(sc),
                "snippet": snippet[:900],
                "source": "neo4j_neighbor",
                "rel_types": rel_types[:8],
                "rel_hints": hints[:12],
            }
        )
    return out


def _retrieve_relationship_keyword_evidence(project_text, anchor, tokens, limit):
    """
    按关键词命中「边上的全部可检索属性 + 端点节点名称/上下文」的关系证据。
    """
    anchor_s = str(anchor or "").strip()
    toks = [t for t in (tokens or []) if str(t).strip() and len(str(t).strip()) >= 2]
    if not anchor_s and not toks:
        return []
    lim = max(1, int(limit or 8))
    skip_keys = _qa_skip_prop_keys()
    rel_min_conf = float(os.getenv("KG_QA_REL_MIN_CONF", "0.55") or 0.55)
    exclude_opt_rel = _parse_bool(os.getenv("KG_QA_EXCLUDE_OPTIMIZATION_REL", "true"), True)
    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (a:KnowledgeNode)-[r]-(b:KnowledgeNode)
                WHERE toString(a.project_id) = toString($project_id)
                  AND toString(b.project_id) = toString($project_id)
                                    AND (r.confidence IS NULL OR toFloat(r.confidence) >= $rel_min_conf)
                                    AND (
                                        $exclude_opt_rel = false
                                        OR (
                                            coalesce(toString(r.source), '') <> 'GraphOptimizationAgent'
                                            AND coalesce(toString(r.value), '') <> '同样本关联'
                                        )
                                    )
                WITH r, a, b,
                     trim(reduce(acc = '',
                       k IN [x IN keys(r) WHERE NOT x IN $skip_prop_keys | x] |
                                             acc + ' ' + substring(
                                                 CASE
                                                     WHEN r[k] IS NULL THEN ''
                                                     WHEN valueType(r[k]) STARTS WITH 'LIST'
                                                     THEN reduce(buf = '', it IN r[k] |
                                                         buf + ' ' +
                                                         CASE
                                                             WHEN it IS NULL THEN ''
                                                             WHEN valueType(it) STARTS WITH 'LIST' OR valueType(it) STARTS WITH 'MAP' THEN ''
                                                             ELSE coalesce(toString(it), '')
                                                         END
                                                     )
                                                     WHEN valueType(r[k]) STARTS WITH 'MAP' THEN ''
                                                     ELSE coalesce(toString(r[k]), '')
                                                 END,
                                                 0,
                                                 320
                                             )
                     )) AS r_dyn
                WITH r, a, b, r_dyn,
                     toLower(trim(
                       coalesce(toString(a.context), '') + ' ' + coalesce(toString(a.value), '') + ' ' +
                       coalesce(toString(a.name), '') + ' ' +
                       coalesce(toString(b.context), '') + ' ' + coalesce(toString(b.value), '') + ' ' +
                       coalesce(toString(b.name), '') + ' ' +
                       coalesce(toString(r.value), '') + ' ' + coalesce(toString(r.eventRel), '') + ' ' +
                       type(r) + ' ' + r_dyn
                     )) AS hay
                WHERE trim(hay) <> ''
                WITH r, a, b, r_dyn, hay,
                     CASE
                       WHEN $anchor <> '' AND hay CONTAINS toLower(trim($anchor)) THEN 2
                       WHEN size($tokens) > 0 AND any(t IN $tokens WHERE size(t) >= 2 AND hay CONTAINS t)
                       THEN 1
                       ELSE 0
                     END AS match_score
                WHERE match_score > 0
                RETURN coalesce(toString(a.value), '') AS av,
                       coalesce(toString(b.value), '') AS bv,
                       coalesce(toString(a.context), '') AS ac,
                       coalesce(toString(b.context), '') AS bc,
                       type(r) AS rtype,
                       coalesce(toString(r.value), '') AS rvalue,
                       coalesce(toString(r.eventRel), '') AS revent,
                       r_dyn AS r_props_blob,
                       toFloat(match_score) AS score
                ORDER BY score DESC
                LIMIT $limit
                """,
                {
                    "project_id": project_text,
                    "anchor": anchor_s,
                    "tokens": toks,
                    "rel_min_conf": rel_min_conf,
                    "exclude_opt_rel": exclude_opt_rel,
                    "skip_prop_keys": skip_keys,
                    "limit": lim,
                },
            )
            rows = list(result)
    except Exception:
        traceback.print_exc()
        return []

    out = []
    for row in rows:
        av = str(row.get("av") or "").strip()[:160]
        bv = str(row.get("bv") or "").strip()[:160]
        rtype = str(row.get("rtype") or "").strip()
        rval = str(row.get("rvalue") or "").strip()
        rev = str(row.get("revent") or "").strip()
        blob = str(row.get("r_props_blob") or "").strip()[:400]
        rv = rval or rev
        extra = ""
        if blob:
            extra = f"\n边属性摘要：{blob}"
        snippet = (
            f"[图谱检索·关系匹配] 「{av or '?' }」 —[{rtype}] {rv or '—'}→ 「{bv or '?'}」"
            f"{extra}"
        )
        rid = hashlib.md5(
            f"{project_text}|{av}|{bv}|{rtype}|{rv}".encode("utf-8", errors="ignore")
        ).hexdigest()[:16]
        out.append(
            {
                "project_id": project_text,
                "node_id": f"rel:{rid}",
                "score": float(row.get("score") or 0.7),
                "snippet": snippet[:920],
                "source": "neo4j_relationship_match",
                "rel_type": rtype,
                "from_label": av,
                "to_label": bv,
            }
        )
    return out


def _history_snapshot_match_score(hay: str, anchor: str, tokens: list) -> float:
    h = str(hay or "").lower()
    if not h:
        return 0.0
    a = str(anchor or "").strip().lower()
    if a and a in h:
        return 2.0

    noisy = {
        "项目",
        "图谱",
        "信息",
        "内容",
        "相关",
        "数据",
        "市场",
        "行业",
        "板块",
        "情况",
        "近期",
        "最近",
        "事件",
        "公告",
        "表现",
        "波动",
    }
    strong_topic_hit = False
    matched = set()
    for t in (tokens or []):
        tt = str(t or "").strip().lower()
        if len(tt) < 2:
            continue
        if tt in noisy:
            continue
        if tt in h:
            matched.add(tt)
            if any(k in tt for k in ("半导体", "芯片", "集成电路", "晶圆", "semiconductor", "chip", "ic")):
                strong_topic_hit = True

    # 强主题词命中可直接通过；否则至少要求两个有效词元共同命中，避免泛词误召回。
    if strong_topic_hit:
        return 1.2
    if len(matched) >= 2:
        return 1.0
    return 0.0


def _history_focus_tokens(anchor: str, tokens: list) -> list:
    """历史快照兜底检索的强约束词，避免被泛词误命中。"""
    out = []
    seen = set()
    for t in _split_retrieval_tokens(anchor or "", max_tokens=32):
        tt = str(t or "").strip().lower()
        if len(tt) < 2:
            continue
        if tt not in seen:
            seen.add(tt)
            out.append(tt)
    for t in (tokens or []):
        tt = str(t or "").strip().lower()
        if len(tt) < 3:
            continue
        if tt not in seen:
            seen.add(tt)
            out.append(tt)
    return out[:24]


def _retrieve_history_snapshot_evidence(project_text, anchor, tokens, limit):
    """
    兜底检索：在 extraction_history 的历史构建快照中按关键词扫描节点/关系，
    覆盖“同一项目存在多个构建图谱版本”但当前工作区图未检出的场景。
    """
    lim = max(1, int(limit or 6))
    snapshot_scan_limit = max(1, _env_int("KG_QA_HISTORY_SNAPSHOT_SCAN_LIMIT", 20))
    focus_tokens = _history_focus_tokens(anchor, tokens)

    client = None
    rows = []
    try:
        client = get_client()
        with client.cursor() as cursor:
            cursor.execute(
                """
                SELECT run_id, title, created_at, nodes_snapshot, edges_snapshot
                FROM extraction_history
                WHERE project_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (project_text, snapshot_scan_limit),
            )
            rows = cursor.fetchall() or []
    except Exception:
        traceback.print_exc()
        rows = []
    finally:
        if client:
            client.close()

    out = []
    seen = set()
    for row in rows:
        run_id = str((row or {}).get("run_id") or "").strip()
        title = str((row or {}).get("title") or "").strip()

        nodes = []
        edges = []
        try:
            nodes_raw = (row or {}).get("nodes_snapshot")
            if isinstance(nodes_raw, str) and nodes_raw.strip():
                nodes = json.loads(nodes_raw)
            elif isinstance(nodes_raw, list):
                nodes = nodes_raw
        except Exception:
            nodes = []

        try:
            edges_raw = (row or {}).get("edges_snapshot")
            if isinstance(edges_raw, str) and edges_raw.strip():
                edges = json.loads(edges_raw)
            elif isinstance(edges_raw, list):
                edges = edges_raw
        except Exception:
            edges = []

        for n in (nodes or []):
            if not isinstance(n, dict):
                continue
            val = str(n.get("value") or "").strip()
            key = str(n.get("key") or "").strip()
            props = n.get("properties") if isinstance(n.get("properties"), dict) else {}
            ctx = str(props.get("context") or "").strip()
            hay = " ".join([val, key, ctx]).strip()
            sc = _history_snapshot_match_score(hay, anchor, tokens)
            if sc <= 0:
                continue
            h_low = hay.lower()
            if focus_tokens and not any(ft in h_low for ft in focus_tokens):
                continue
            snippet = f"[历史图谱快照] run_id={run_id or '-'} title={title or '-'} 节点：{val or key or '未命名节点'}；依据：{(ctx or val or key)[:280]}"
            dk = hashlib.md5(snippet.encode("utf-8", errors="ignore")).hexdigest()
            if dk in seen:
                continue
            seen.add(dk)
            out.append(
                {
                    "project_id": project_text,
                    "node_id": f"hist_node:{dk[:16]}",
                    "score": 0.62 if sc >= 2 else 0.55,
                    "snippet": snippet[:920],
                    "source": "history_snapshot_match",
                    "run_id": run_id,
                }
            )
            if len(out) >= lim:
                return out

        for e in (edges or []):
            if not isinstance(e, dict):
                continue
            typ = str(e.get("type") or "").strip()
            val = str(e.get("value") or "").strip()
            event_rel = str(e.get("eventRel") or "").strip()
            props = e.get("properties") if isinstance(e.get("properties"), dict) else {}
            ctx = str(props.get("context") or "").strip()
            hay = " ".join([typ, val, event_rel, ctx]).strip()
            sc = _history_snapshot_match_score(hay, anchor, tokens)
            if sc <= 0:
                continue
            h_low = hay.lower()
            if focus_tokens and not any(ft in h_low for ft in focus_tokens):
                continue
            snippet = f"[历史图谱快照·关系] run_id={run_id or '-'} title={title or '-'} 关系：{typ or '未命名'} {val or event_rel or ''}；依据：{(ctx or val or event_rel or typ)[:280]}"
            dk = hashlib.md5(snippet.encode("utf-8", errors="ignore")).hexdigest()
            if dk in seen:
                continue
            seen.add(dk)
            out.append(
                {
                    "project_id": project_text,
                    "node_id": f"hist_rel:{dk[:16]}",
                    "score": 0.6 if sc >= 2 else 0.53,
                    "snippet": snippet[:920],
                    "source": "history_snapshot_match",
                    "run_id": run_id,
                }
            )
            if len(out) >= lim:
                return out

    return out


def retrieve_project_kg(project_id, query, top_k=3):
    """
    Tool-2: 单项目检索工具（不依赖 contentEmbedding 向量索引）。
    采用「节点关键词匹配 + 关系关键词匹配 + 最新兜底」；一跳邻接扩展邻居证据。
    匹配字段：context/value/name/key + **Neo4j 节点上其余属性（可通过 KG_QA_SKIP_PROPERTY_KEYS 排除向量等大字段）**；
    另检索「边上全部属性 + 端点节点文本」是否与问句关键词重合。
    """
    project_text = str(project_id).strip() if project_id is not None else ""
    combined_query = str(query or "").strip()
    if not project_text or not combined_query:
        return []

    k_raw = int(top_k or 0)
    no_limit = k_raw <= 0
    k = max(1, k_raw) if not no_limit else 0
    anchor, tokens = _merge_retrieval_tokens(
        combined_query,
        max_tokens=max(12, _env_int("KG_QA_RETRIEVAL_TOKEN_CAP", 20)),
    )
    skip_keys = _qa_skip_prop_keys()

    rows = []
    has_query_match = False
    try:
        with driver.session() as session:
            cypher = """
                MATCH (n:KnowledgeNode)
                    WHERE toString(n.project_id) = toString($project_id)
                    WITH n,
                         trim(reduce(acc = '',
                           k IN [x IN keys(n) WHERE NOT x IN $skip_prop_keys | x] |
                                                     acc + ' ' + substring(
                                                         CASE
                                                             WHEN n[k] IS NULL THEN ''
                                                             WHEN valueType(n[k]) STARTS WITH 'LIST'
                                                             THEN reduce(buf = '', it IN n[k] |
                                                                 buf + ' ' +
                                                                 CASE
                                                                     WHEN it IS NULL THEN ''
                                                                     WHEN valueType(it) STARTS WITH 'LIST' OR valueType(it) STARTS WITH 'MAP' THEN ''
                                                                     ELSE coalesce(toString(it), '')
                                                                 END
                                                             )
                                                             WHEN valueType(n[k]) STARTS WITH 'MAP' THEN ''
                                                             ELSE coalesce(toString(n[k]), '')
                                                         END,
                                                         0,
                                                         320
                                                     )
                         )) AS dyn_blob
                    WITH n,
                         toLower(trim(
                           coalesce(toString(n.context), '') + ' ' +
                           coalesce(toString(n.value), '') + ' ' +
                           coalesce(toString(n.name), '') + ' ' +
                           coalesce(toString(n.key), '') + ' ' +
                           dyn_blob
                         )) AS ctx,
                         CASE
                           WHEN n.context IS NOT NULL AND trim(toString(n.context)) <> ''
                           THEN trim(toString(n.context))
                           ELSE trim(coalesce(toString(n.value), toString(n.name), ''))
                         END AS display_text,
                         dyn_blob
                    WHERE trim(ctx) <> ''
                    WITH n, ctx, display_text, dyn_blob,
                         CASE
                           WHEN $anchor <> '' AND ctx CONTAINS toLower(trim($anchor)) THEN 2
                           WHEN size($tokens) > 0 AND any(t IN $tokens WHERE size(t) >= 2 AND ctx CONTAINS t)
                           THEN 1
                           ELSE 0
                         END AS match_score
                    WHERE match_score > 0
                    RETURN elementId(n) AS node_id,
                           display_text AS context,
                           substring(dyn_blob, 0, 520) AS dyn_blob,
                           coalesce(n.project_id, $project_id) AS project_id,
                           toFloat(match_score) AS score
                    ORDER BY score DESC
                """
            params = {
                    "project_id": project_text,
                    "anchor": anchor,
                    "tokens": tokens,
                    "skip_prop_keys": skip_keys,
                }
            if not no_limit:
                cypher += "\nLIMIT $top_k"
                params["top_k"] = int(k)
            result = session.run(cypher, params)
            rows = list(result)
            has_query_match = bool(rows)
    except Exception:
        traceback.print_exc()
        return []

    allow_latest_fallback = _parse_bool(
        os.getenv("KG_QA_ALLOW_LATEST_NODE_FALLBACK", "false"),
        False,
    )

    if not rows and allow_latest_fallback:
        try:
            with driver.session() as session:
                cypher_fb = """
                    MATCH (n:KnowledgeNode)
                    WHERE toString(n.project_id) = toString($project_id)
                    WITH n,
                         trim(reduce(acc = '',
                           k IN [x IN keys(n) WHERE NOT x IN $skip_prop_keys | x] |
                                                     acc + ' ' + substring(
                                                         CASE
                                                             WHEN n[k] IS NULL THEN ''
                                                             WHEN valueType(n[k]) STARTS WITH 'LIST'
                                                             THEN reduce(buf = '', it IN n[k] |
                                                                 buf + ' ' +
                                                                 CASE
                                                                     WHEN it IS NULL THEN ''
                                                                     WHEN valueType(it) STARTS WITH 'LIST' OR valueType(it) STARTS WITH 'MAP' THEN ''
                                                                     ELSE coalesce(toString(it), '')
                                                                 END
                                                             )
                                                             WHEN valueType(n[k]) STARTS WITH 'MAP' THEN ''
                                                             ELSE coalesce(toString(n[k]), '')
                                                         END,
                                                         0,
                                                         320
                                                     )
                         )) AS dyn_blob,
                         CASE
                           WHEN n.context IS NOT NULL AND trim(toString(n.context)) <> ''
                           THEN trim(toString(n.context))
                           ELSE trim(coalesce(toString(n.value), toString(n.name), ''))
                         END AS display_text
                    WHERE trim(display_text) <> '' OR trim(dyn_blob) <> ''
                    RETURN elementId(n) AS node_id,
                           CASE
                             WHEN trim(display_text) <> '' THEN display_text
                             ELSE substring(dyn_blob, 0, 800)
                           END AS context,
                           substring(dyn_blob, 0, 520) AS dyn_blob,
                           coalesce(n.project_id, $project_id) AS project_id,
                           toFloat(0.01) AS score
                                        ORDER BY elementId(n) DESC
                    """
                params_fb = {"project_id": project_text, "skip_prop_keys": skip_keys}
                if not no_limit:
                    cypher_fb += "\nLIMIT $top_k"
                    params_fb["top_k"] = int(k)
                fallback = session.run(cypher_fb, params_fb)
                rows = list(fallback)
        except Exception:
            traceback.print_exc()
            rows = []

    rel_lim = max(1, _env_int("KG_QA_REL_MATCH_LIMIT", 10))
    if not rows:
        # 兜底：即使节点文本未命中，也尝试关系关键词匹配，避免“关系有证据但节点未命中”时误判 miss。
        rel_only = _retrieve_relationship_keyword_evidence(project_text, anchor, tokens, rel_lim)
        if rel_only:
            return rel_only
        # 二级兜底：扫描项目历史构建快照，覆盖同项目多图谱版本场景。
        hist_only = _retrieve_history_snapshot_evidence(
            project_text,
            anchor,
            tokens,
            max(6, _env_int("KG_QA_HISTORY_SNAPSHOT_EVIDENCE_LIMIT", 8)),
        )
        if hist_only:
            return hist_only
        return []

    evidence = []
    seed_ids = []
    for row in rows:
        base = str(row.get("context") or "").strip()
        dyn = str(row.get("dyn_blob") or "").strip()
        snippet = base
        if dyn:
            snippet = f"{base}\n【节点其它属性（参与检索合并）】{dyn}" if base else f"【节点属性检索】{dyn}"
        if not snippet.strip():
            continue
        nid = str(row.get("node_id") or "")
        seed_ids.append(nid)
        evidence.append(
            {
                "project_id": str(row.get("project_id") or project_text),
                "node_id": nid,
                "score": float(row.get("score") or 0.0),
                "snippet": snippet[:920],
                "source": "neo4j_context_match" if has_query_match else "neo4j_context_fallback",
            }
        )

    # 仅在“真实关键词命中”时做图扩展，避免兜底节点引入过多邻接噪声。
    if has_query_match:
        exclude = set(seed_ids)
        neighbors = _neo4j_neighbor_evidence(project_text, seed_ids, exclude, tokens)
        evidence.extend(neighbors)

    # 关系匹配不依赖节点命中：板块/主题类问题常体现在边语义而非节点 context。
    evidence.extend(
        _retrieve_relationship_keyword_evidence(project_text, anchor, tokens, rel_lim)
    )

    if not evidence:
        evidence.extend(
            _retrieve_history_snapshot_evidence(
                project_text,
                anchor,
                tokens,
                max(6, _env_int("KG_QA_HISTORY_SNAPSHOT_EVIDENCE_LIMIT", 8)),
            )
        )

    if evidence:
        uniq = {}
        for item in evidence:
            snippet = str(item.get("snippet") or "").strip()
            if not snippet:
                continue
            key = hashlib.md5(snippet.encode("utf-8", errors="ignore")).hexdigest()
            prev = uniq.get(key)
            if prev is None or float(item.get("score") or 0.0) > float(prev.get("score") or 0.0):
                uniq[key] = item
        evidence = sorted(uniq.values(), key=lambda x: float(x.get("score") or 0.0), reverse=True)
    return evidence


def aggregate_evidence(project_evidence_map, max_items=12):
    """
    Tool-3: 跨项目证据聚合（去重、重排、截断）。
    """
    merged = []
    for _, items in (project_evidence_map or {}).items():
        if isinstance(items, list):
            merged.extend(items)

    uniq = {}
    for item in merged:
        snippet = str(item.get("snippet") or "").strip()
        if not snippet:
            continue
        key = hashlib.md5(snippet.encode("utf-8")).hexdigest()
        prev = uniq.get(key)
        if prev is None or float(item.get("score") or 0.0) > float(prev.get("score") or 0.0):
            uniq[key] = item

    ranked = sorted(
        uniq.values(),
        key=lambda x: float(x.get("score") or 0.0),
        reverse=True
    )
    cap = int(max_items or 0)
    if cap <= 0:
        cap = len(ranked)
    if len(ranked) <= cap:
        return ranked

    buckets = {}
    for item in ranked:
        pid = str(item.get("project_id") or "").strip() or "__unknown__"
        buckets.setdefault(pid, []).append(item)

    if len(buckets) <= 1:
        return ranked[:cap]

    per_project_cap = _env_int("KG_QA_AGGREGATE_PER_PROJECT_CAP", 0)
    if per_project_cap <= 0:
        per_project_cap = max(1, (cap + len(buckets) - 1) // len(buckets))

    project_order = sorted(
        buckets.keys(),
        key=lambda p: float((buckets[p][0] if buckets[p] else {}).get("score") or 0.0),
        reverse=True,
    )

    selected = []
    idx = {p: 0 for p in project_order}
    taken = {p: 0 for p in project_order}
    while len(selected) < cap:
        progressed = False
        for p in project_order:
            if taken[p] >= per_project_cap:
                continue
            i = idx[p]
            items = buckets.get(p) or []
            if i >= len(items):
                continue
            selected.append(items[i])
            idx[p] = i + 1
            taken[p] += 1
            progressed = True
            if len(selected) >= cap:
                break
        if not progressed:
            break

    if len(selected) < cap:
        seen_ids = {id(x) for x in selected}
        for it in ranked:
            if id(it) in seen_ids:
                continue
            selected.append(it)
            if len(selected) >= cap:
                break

    return selected[:cap]


def _web_evidence_body_without_footer(snippet: str) -> str:
    """联网证据 snippet 末尾可能含「来源网址」分隔块，摘要展示时先去掉以免重复。"""
    s = str(snippet or "")
    if "\n────────\n" in s:
        return s.split("\n────────\n", 1)[0].strip()
    return s.strip()


def _evidence_type(evidence_item: dict) -> str:
    """统一判定证据类型，避免提示词侧漏判网页证据。"""
    if not isinstance(evidence_item, dict):
        return "图谱"
    src = str(evidence_item.get("source") or "").strip()
    snip = str(evidence_item.get("snippet") or "")
    if src == "constrained_web" or "[联网检索" in snip:
        return "网页摘要"
    if src == "neo4j_neighbor" or "[图谱扩展·Neo4j关联路径]" in snip:
        return "图谱扩展"
    return "图谱"


def _is_definition_style_query(query: str) -> bool:
    q = str(query or "").strip().lower()
    if not q:
        return False
    marks = (
        "是什么",
        "是啥",
        "什么意思",
        "定义",
        "概念",
        "是什么东西",
        "what is",
        "definition",
    )
    return any(m in q for m in marks)


def _prioritize_web_for_definition_query(evidence: list, query: str) -> list:
    """定义类问题优先给模型看网页摘要，减少被行情类证据主导。"""
    ev = list(evidence or [])
    if not ev or not _is_definition_style_query(query):
        return ev
    web = [x for x in ev if _evidence_type(x) == "网页摘要"]
    non_web = [x for x in ev if _evidence_type(x) != "网页摘要"]
    if not web:
        return ev
    return web + non_web


def _relation_signature(e: dict) -> tuple:
    """关系证据签名：同主体-同客体-同主题 视为一组。"""
    if not isinstance(e, dict):
        return ("", "", "", "")
    pid = str(e.get("project_id") or "").strip()
    src = str(e.get("source") or "").strip()
    if src != "neo4j_relationship_match":
        return ("", "", "", "")

    frm = str(e.get("from_label") or "").strip()
    to = str(e.get("to_label") or "").strip()
    topic = str(e.get("rel_type") or "").strip()

    if (not frm or not to) and str(e.get("snippet") or ""):
        m = re.search(r"「([^」]{1,120})」\s*—\[[^\]]*\].*?→\s*「([^」]{1,120})」", str(e.get("snippet") or ""))
        if m:
            frm = frm or m.group(1).strip()
            to = to or m.group(2).strip()
    if not topic:
        s = str(e.get("snippet") or "")
        m2 = re.search(r"—\[([^\]]{1,80})\]", s)
        if m2:
            topic = m2.group(1).strip()
    return (pid, frm, to, topic)


def _project_balanced_order(items: list) -> list:
    """按项目轮转重排证据，避免多项目问答时提示词只被首个项目占满。"""
    rows = [x for x in (items or []) if isinstance(x, dict)]
    if len(rows) <= 1:
        return rows

    buckets = {}
    for row in rows:
        pid = str(row.get("project_id") or "").strip() or "__unknown__"
        buckets.setdefault(pid, []).append(row)

    if len(buckets) <= 1:
        return sorted(rows, key=lambda r: float(r.get("score") or 0.0), reverse=True)

    for pid, bucket in buckets.items():
        buckets[pid] = sorted(bucket, key=lambda r: float(r.get("score") or 0.0), reverse=True)

    project_order = sorted(
        buckets.keys(),
        key=lambda pid: float((buckets[pid][0] if buckets[pid] else {}).get("score") or 0.0),
        reverse=True,
    )

    ordered = []
    cursor = {pid: 0 for pid in project_order}
    while True:
        progressed = False
        for pid in project_order:
            idx = cursor[pid]
            bucket = buckets.get(pid) or []
            if idx >= len(bucket):
                continue
            ordered.append(bucket[idx])
            cursor[pid] = idx + 1
            progressed = True
        if not progressed:
            break
    return ordered


def _appendix_evidence_preprocess(evidence: list, max_total: int = 14) -> list:
    """
    附录证据预处理：
    1) 关系证据按「同主体-同客体-同主题」折叠：每组保留 1 条代表 + 1 条补充；
    2) 固定分组顺序：知识图谱-核心事实 -> 知识图谱-关系/扩展 -> 网页摘要。
    """
    rows = [x for x in (evidence or []) if isinstance(x, dict)]
    if not rows:
        return []

    relation_groups = {}
    non_relation = []
    for e in rows:
        sig = _relation_signature(e)
        if sig[0] and sig[1] and sig[2]:
            relation_groups.setdefault(sig, []).append(e)
        else:
            non_relation.append(e)

    folded_relations = []
    for _, items in relation_groups.items():
        ranked = sorted(items, key=lambda r: float(r.get("score") or 0.0), reverse=True)
        # 每组保留代表 + 补充，减少同义关系边堆叠。
        folded_relations.extend(ranked[:2])

    core = []
    rel_or_expand = []
    web = []
    for e in non_relation + folded_relations:
        et = _evidence_type(e)
        src = str(e.get("source") or "")
        if et == "网页摘要":
            web.append(e)
        elif src in ("neo4j_relationship_match", "neo4j_neighbor") or et == "图谱扩展":
            rel_or_expand.append(e)
        else:
            core.append(e)

    core = _project_balanced_order(core)
    rel_or_expand = _project_balanced_order(rel_or_expand)
    web = _project_balanced_order(web)

    ordered = core + rel_or_expand + web
    cap = max(1, int(max_total or 14))
    return ordered[:cap]


def _evidence_brief_for_prompt(snippet: str, max_len: int = 100) -> str:
    """从证据片段里抽一句话级「要点」，供模型在正文中向用户解释该条证据在讲什么。"""
    t = re.sub(r"\s+", " ", str(snippet or "").strip())
    if "摘要:" in t:
        t = t.split("摘要:", 1)[-1].strip()
    if "片段:" in t and t.startswith("["):
        t = t.split("片段:", 1)[-1].strip()
    if len(t) > max_len * 2:
        t = t[: max_len * 2]
    if len(t) > max_len:
        t = t[:max_len] + "…"
    return t or "（无文本摘要）"


def _build_answer_prompt(query, evidence, detail_level, web_attempted=False, deep_think=False):
    """
    基于给定的 query 和 evidence（来自 Neo4j 图谱 + 可选合并网页摘要），
    拼接给 LLM 的 user prompt 模板（核心环节：严格限定事实幻觉边界并引导回复格式）。
    """
    detail_hint = "详细" if detail_level == "detailed" else "简明扼要"
    style_hint = (
        f"【写作风格】请使用{detail_hint}的语言。如果有多个不同公司的信息，请分段或使用列表清晰呈现。"
        "优先以证据给出事实判断，再给出推断性分析与可能传导路径；"
        "允许结合金融常识做适度发散，但必须标注不确定性和触发条件。"
        "若证据不足，不要拒答，请给出条件化结论与需要补充的数据项；"
        "禁止编造原始事实或具体数值。"
    ) if _parse_bool(deep_think, False) else (
        f"【写作风格】请使用{detail_hint}的语言。如果有多个不同公司的信息，请分段或使用列表清晰呈现。"
        "必须严格约束在给定证据的事实范围内，不要进行无关的发散。"
    )

    appendix_evidence = _appendix_evidence_preprocess(
        evidence,
        max_total=max(8, _env_int("KG_QA_APPENDIX_MAX_ITEMS", 14)),
    )

    evidence_text = ""
    for idx, e in enumerate(appendix_evidence, start=1):
        snip = str(e.get("snippet") or "")
        pid = str(e.get("project_id") or "")
        pn = str(e.get("project_name") or "")
        etype = _evidence_type(e)
        p_str = f"project_id={pid}"
        if pn:
            p_str += f" project_name={pn}"
        if etype:
            p_str += f" 类型={etype}"
        evidence_text += f"[证据{idx}] {p_str}\n要点：{snip}\n\n"

    has_web = any(_evidence_type(e) == "网页摘要" for e in (appendix_evidence or []))

    web_guard = ""
    if has_web:
        web_guard = (
            "\n【重要】「类型=网页摘要」来自受限联网检索（样本锚定），仅代表公开市场摘要，不等同公告原文。"
            "正文综合叙述中须自然融入与**用户问题主题一致**的网页要点（勿堆砌编号）；无关网页不要展开。\n"
            "每条网页摘要附录时必须同时给出 **可点击的 Markdown 链接** `[标题](完整URL)`，并在其后写出完整 `https://…` 裸链便于复制。\n"
            "若与图谱结论冲突，须在正文综合叙述中说明差异与不确定性。\n"
        )
        
    web_integrate_rule = (
        "正文：综合「类型=图谱」「类型=图谱扩展」与「类型=网页摘要」中能支撑结论的要点，写成连贯叙述；网页部分不得写成公告原文口吻。"
        if has_web
        else "正文：基于「类型=图谱」「类型=图谱扩展」作答；若本轮未找寻到或未开启联网补充数据，仅作答已有图谱知识即可。"
    )
    appendix_web_rule = (
        "**网页摘要** 小节：每条必须含 **①** Markdown 链接 `[可见标题](https://完整域名路径)`；**②** 单独一行或以括号形式再次写出同一完整 URL（裸链）。禁止只有标题而无链接。"
        if has_web
        else ("**网页摘要** 小节：写「无」并简述原因（联网补强本轮未命中）。" if web_attempted else "")
    )
    
    appendix_section = (
        "  - **附录**：供核对出处，可分「知识图谱」「网页摘要」两类列出；此处可使用分点。\n"
        "  - **知识图谱**：逐条「证据编号 — 项目名 — 一句话要点」（须结合上表「要点」转述，禁止只写编号）。\n"
        f"  - {appendix_web_rule}\n"
    ) if web_attempted else (
        "  - **附录**：供核对出处。列出「知识图谱」证据。\n"
        "  - **知识图谱**：逐条「证据编号 — 项目名 — 一句话要点」（须结合上表「要点」转述，禁止只写编号）。\n"
    )

    deep_think_extension_rule = (
        "  - 在正文中，先完成对用户问题的直接回答；随后必须追加一个以“【延展分析】”开头的独立段落。\n"
        "  - “【延展分析】”部分要比普通回答更深入，可展开行业机制、市场传导、情景推演与风险边界；"
        "但所有推演都要和给定证据保持可追溯关联。\n"
        "  - 若证据偏弱，在“【延展分析】”中明确条件化判断与待补充数据项，而不是拒答。\n"
        "  - 作为软控制，建议“【延展分析】”不少于2到3段，每段尽量包含完整观点、依据与解释。\n"
    ) if _parse_bool(deep_think, False) else ""
    
    structure_block = (
        "\n【输出结构 — 必须严格遵守】\n"
        "• **正文禁止使用 `## 回答` 或其他 `##` 二级标题**；如需增强层次，请使用 `###` 三级标题组织正文，例如 `### 核心结论`、`### 影响分析`、`### 操作建议`。\n"
        "• **全文只允许出现唯一一个** Markdown 二级标题：`## 参考与证据`（附录仅此一行标题）。禁止其他 `##`。\n\n"
        "【正文 — 综合回答】\n"
        f"  - {web_integrate_rule}\n"
        "  - **面向用户阅读**：自然、连贯的中文（可多段），直接回应用户问题。\n"
        "  - **禁止**采用「结论：」「依据：」以及「证据1…证据2…」流水编号式结构；少用僵硬条款罗列。\n"
        "  - 可用 `###` 小标题、短列表和 **加粗** 突出重点；正文必须自然出现 1 到 3 个贴切 emoji，可放在小标题或关键结论前，但不要花哨堆砌。\n"
        "  - 可在叙述中自然点到依据来源（如「项目图谱显示…」「公开报道提到…」），不必穷举证据编号。\n"
        "  - 禁止出现 project_id、node_id、裸数字项目编号。\n\n"
        f"{deep_think_extension_rule}"
        "## 参考与证据\n"
        f"{appendix_section}"
        "【可读性】附录要让读者不看原始证据表也能理解每条在支撑什么。\n\n"
    )

    return (
        "你是专业的金融信息分析助手（知识图谱问答）。请严格基于给定证据作答，禁止编造公告中不存在的数据与结论。\n"
        "若证据不足以支撑结论，须明确写出「依据不足」并说明缺少哪类信息。\n"
        f"{web_guard}"
        f"{style_hint}\n"
        f"{structure_block}"
        f"用户问题：{query}\n\n"
        f"证据集合（每条含「要点」便于你向用户解释「证据n」是什么）：\n{evidence_text}\n"
    )

def _build_answer_prompt_legacy(query, evidence, detail_level):
    max_snippet_chars = max(120, _env_int("KG_QA_SNIPPET_MAX_CHARS", 420))
    max_total_chars = max(800, _env_int("KG_QA_PROMPT_EVIDENCE_MAX_CHARS", 3600))
    lines = []
    used_chars = 0
    has_web = False
    for idx, e in enumerate(evidence, start=1):
        snippet = str(e.get("snippet") or "").strip()[:max_snippet_chars]
        if not snippet:
            continue
        is_web = str(e.get("source") or "") == "constrained_web" or "[联网检索·样本锚定]" in snippet
        is_neighbor = str(e.get("source") or "") == "neo4j_neighbor" or "[图谱扩展·Neo4j关联路径]" in snippet
        if is_web:
            has_web = True
        next_cost = len(snippet)
        if used_chars + next_cost > max_total_chars:
            break
        used_chars += next_cost
        if is_web:
            ev_type = "网页摘要"
        elif is_neighbor:
            ev_type = "图谱扩展"
        else:
            ev_type = "图谱"
        pname = str(e.get("project_name") or e.get("project_id") or "").strip()
        ex_limit = min(max_snippet_chars, 420)
        if is_web:
            body_txt = _web_evidence_body_without_footer(snippet)
            brief = _evidence_brief_for_prompt(body_txt, 120)
            excerpt = body_txt[:ex_limit] + ("…" if len(body_txt) > ex_limit else "")
            url_u = str(e.get("url") or "").strip()
            if not url_u:
                for line in body_txt.split("\n"):
                    ln = line.strip()
                    if ln.startswith("链接:"):
                        url_u = ln.split(":", 1)[-1].strip()
                        break
            url_block = (
                f"\n来源网址（附录须写 `[标题](URL)`；本条 URL：{url_u}"
                if url_u
                else ""
            )
            lines.append(
                f"[证据{idx}] 类型={ev_type} 项目「{pname}」\n"
                f"要点（写回答时请用通俗语言转述该要点，勿只写编号）：{brief}\n"
                f"摘录：{excerpt}{url_block}"
            )
        else:
            brief = _evidence_brief_for_prompt(snippet, 120)
            excerpt = snippet[:ex_limit] + ("…" if len(snippet) > ex_limit else "")
            lines.append(
                f"[证据{idx}] 类型={ev_type} 项目「{pname}」\n"
                f"要点（写回答时请用通俗语言转述该要点，勿只写编号）：{brief}\n"
                f"摘录：{excerpt}"
            )
    evidence_text = "\n\n".join(lines)

    style_hint = "请优先给出简洁结论，随后补充关键依据。" if detail_level == "brief" else "请给出详细分析，分点说明结论、原因与风险。"
    web_guard = ""
    if has_web:
        web_guard = (
            "\n【重要】「类型=网页摘要」来自受限联网检索（样本锚定），仅代表公开市场摘要，不等同公告原文。"
            "正文综合叙述中须自然融入与**用户问题主题一致**的网页要点（勿堆砌编号）；无关网页不要展开。\n"
            "每条网页摘要附录时必须同时给出 **可点击的 Markdown 链接** `[标题](完整URL)`，并在其后写出完整 `https://…` 裸链便于复制。\n"
            "若与图谱结论冲突，须在正文综合叙述中说明差异与不确定性。\n"
        )

    web_integrate_rule = (
        "正文：综合「类型=图谱」「类型=图谱扩展」与「类型=网页摘要」中能支撑结论的要点，写成连贯叙述；网页部分不得写成公告原文口吻。"
        if has_web
        else "正文：基于「类型=图谱」「类型=图谱扩展」作答；若本轮无网页证据或未开启联网补强，可用一两句话说明即可。"
    )
    web_attempted = kwargs.get("web_attempted", False) if "web_attempted" in kwargs else False
    appendix_web_rule = (
        "**网页摘要** 小节：每条必须含 **①** Markdown 链接 `[可见标题](https://完整域名路径)`；**②** 单独一行或以括号形式再次写出同一完整 URL（裸链）。禁止只有标题而无链接。"
        if has_web
        else ("**网页摘要** 小节：写「无」并简述原因（本轮无网页命中）。" if web_attempted else "")
    )
    
    appendix_section = (
        "  - **附录**：供核对出处，可分「知识图谱」「网页摘要」两类列出；此处可使用分点。\n"
        "  - **知识图谱**：逐条「证据编号 — 项目名 — 一句话要点」（须结合上表「要点」转述，禁止只写编号）。\n"
        f"  - {appendix_web_rule}\n"
    ) if web_attempted else (
        "  - **附录**：供核对出处。列出「知识图谱」证据。\n"
        "  - **知识图谱**：逐条「证据编号 — 项目名 — 一句话要点」（须结合上表「要点」转述，禁止只写编号）。\n"
    )
    
    structure_block = (
        "\n【输出结构 — 必须严格遵守】\n"
        "• **正文开头禁止使用「## 回答」字样或任何用于标识正文的小标题**：直接从第一段文字开始写综合答案（可多段）；在附录开始前不要输出任何 `##` 二级标题。\n"
        "• **全文只允许出现唯一一个** Markdown 二级标题：`## 参考与证据`（附录仅此一行标题）。禁止其他 `##`。\n\n"
        "【正文 — 综合回答】\n"
        f"  - {web_integrate_rule}\n"
        "  - **面向用户阅读**：自然、连贯的中文（可多段），直接回应用户问题。\n"
        "  - **禁止**采用「结论：」「依据：」以及「证据1…证据2…」流水编号式结构；少用条款罗列。\n"
        "  - 可用 `###` 小标题、短列表和 **加粗** 突出重点；正文必须自然出现 1 到 3 个贴切 emoji，可放在小标题或关键结论前，但不要花哨堆砌。\n"
        "  - 可在叙述中自然点到依据来源（如「项目图谱显示…」「公开报道提到…」），不必穷举证据编号。\n"
        "  - 禁止出现 project_id、node_id、裸数字项目编号。\n\n"
        "## 参考与证据\n"
        f"{appendix_section}"
        "【可读性】附录要让读者不看原始证据表也能理解每条在支撑什么。\n\n"
    )

    return (
        "你是专业的金融信息分析助手（知识图谱问答）。请严格基于给定证据作答，禁止编造公告中不存在的数据与结论。\n"
        "若证据不足以支撑结论，须明确写出「依据不足」并说明缺少哪类信息。\n"
        f"{web_guard}"
        f"{style_hint}\n"
        f"{structure_block}"
        f"用户问题：{query}\n\n"
        f"证据集合（每条含「要点」便于你向用户解释「证据n」是什么）：\n{evidence_text}\n"
    )


def generate_answer_from_evidence(
    query, evidence, deep_think=False, detail_level="brief", prior_messages=None
):
    """
    Tool-4: 回答生成器。支持 deepseek-chat / deepseek-reasoner。
    prior_messages: 本会话内已持久化的多轮 user/assistant，用于指代消解与连贯回答。
    """
    if not evidence:
        return "当前项目库无相关证据，建议先构建图谱或调整关键词后再提问。"

    messages, model_name, temp = _build_evidence_messages(
        query, evidence, deep_think, detail_level, prior_messages
    )
    try:
        return _call_chat_completion(
            messages=messages,
            model_name=model_name,
            temperature=temp,
        )
    except Exception:
        traceback.print_exc()
        fallback = []
        for idx, e in enumerate(evidence[:3], start=1):
            pn = str(e.get("project_name") or e.get("project_id") or "").strip()
            fallback.append(
                f"{idx}. 「{pn}」{str(e.get('snippet') or '')[:120]}"
            )
        if fallback:
            return "模型调用超时或失败，已返回证据摘要（降级模式）：\n" + "\n".join(fallback)
        return "回答生成阶段失败，请稍后重试。"


def estimate_confidence(evidence):
    if not evidence:
        return 0.0
    scores = [float(e.get("score") or 0.0) for e in evidence]
    if not scores:
        return 0.0
    avg = sum(scores) / len(scores)
    if avg < 0:
        avg = 0.0
    if avg > 1:
        avg = 1.0
    return round(avg, 4)


def detect_conflict_hints(evidence):
    """
    简单冲突提示：同一批证据同时出现明显相反描述时提醒人工复核。
    """
    if not evidence:
        return []
    text = " ".join([str(e.get("snippet") or "") for e in evidence[:10]])
    hints = []
    opposite_pairs = [
        ("增长", "下降"),
        ("上升", "下滑"),
        ("盈利", "亏损"),
        ("利好", "利空"),
    ]
    for a, b in opposite_pairs:
        if a in text and b in text:
            hints.append(f"证据中同时出现“{a}”与“{b}”描述，建议人工复核。")
    return hints


def classify_query_intent(query, conversation_history=None):
    return capability_classify_query_intent(
        query=query,
        call_chat_completion_fn=_call_chat_completion,
        conversation_history=conversation_history,
    )


def generate_general_answer(query, deep_think=False, detail_level="brief", prior_messages=None):
    return capability_generate_general_answer(
        query=query,
        deep_think=deep_think,
        detail_level=detail_level,
        parse_bool_fn=_parse_bool,
        call_chat_completion_fn=_call_chat_completion,
        prior_messages=prior_messages,
    )


# =========================
# Agent + Skill + Tool 三层架构
# =========================
# Tools（执行层）
def list_user_projects(user_id, username=None, uid=None, is_admin=False):
    aux_uid = uid
    aux_is_admin = is_admin

    def _fn(primary_uid):
        return get_user_project_ids(primary_uid, username, uid=aux_uid, is_admin=aux_is_admin)

    return orch_list_user_projects(user_id, _fn)


def aggregate_rank(chunks, max_items=12):
    return orch_aggregate_rank(chunks, aggregate_evidence, max_items=max_items)


def generate_answer(context, query, deep_think=False, detail_level="brief", prior_messages=None):
    return orch_generate_answer(
        context=context,
        query=query,
        generate_answer_from_evidence_fn=generate_answer_from_evidence,
        deep_think=deep_think,
        detail_level=detail_level,
        prior_messages=prior_messages,
    )


# Skills（能力模板层）
def cross_project_retrieval_skill(project_ids, query, top_k_per_project=10):
    return orch_cross_project_retrieval_skill(
        project_ids=project_ids,
        query=query,
        retrieve_project_kg_fn=retrieve_project_kg,
        aggregate_rank_fn=aggregate_rank,
        top_k_per_project=top_k_per_project,
    )


def evidence_citation_skill(evidence):
    return orch_evidence_citation_skill(evidence)


def conflict_awareness_skill(evidence):
    return orch_conflict_awareness_skill(
        evidence=evidence,
        detect_conflict_hints_fn=detect_conflict_hints,
        estimate_confidence_fn=estimate_confidence,
    )


# Agents（决策层）
class QueryPlannerAgent(OrchQueryPlannerAgent):
    def __init__(self):
        super().__init__(classify_query_intent_fn=classify_query_intent)


class SynthesisAgent(OrchSynthesisAgent):
    def __init__(self):
        super().__init__(
            generate_answer_fn=generate_answer,
            generate_general_answer_fn=generate_general_answer,
            evidence_citation_skill_fn=evidence_citation_skill,
            conflict_awareness_skill_fn=conflict_awareness_skill,
        )


def _fallback_text_from_evidence(evidence):
    fb = []
    for idx, e in enumerate((evidence or [])[:3], start=1):
        fb.append(f"{idx}. [项目 {e.get('project_id')}] {str(e.get('snippet') or '')[:120]}")
    if fb:
        return "模型调用超时或失败，已返回证据摘要（降级模式）：\n" + "\n".join(fb)
    return "回答生成阶段失败，请稍后重试。"


def _evidence_snippets_for_debug(evidence, max_items=25, max_chars=500):
    """供 retrieval_debug 返回，便于排查「为何无命中」。"""
    out = []
    for e in (evidence or [])[:max_items]:
        if not isinstance(e, dict):
            continue
        out.append(
            {
                "project_id": e.get("project_id"),
                "node_id": e.get("node_id"),
                "source": e.get("source"),
                "rel_type": e.get("rel_type"),
                "score": e.get("score"),
                "snippet_preview": str(e.get("snippet") or "")[:max_chars],
            }
        )
    return out


def _evidence_count_by_project(evidence):
    out = {}
    for e in evidence or []:
        if not isinstance(e, dict):
            continue
        pid = str(e.get("project_id") or "").strip() or "__unknown__"
        out[pid] = int(out.get(pid, 0)) + 1
    return out


def _project_hit_ids_from_counts(counts):
    items = []
    for pid, cnt in (counts or {}).items():
        p = str(pid or "").strip()
        if not p:
            continue
        items.append((p, int(cnt or 0)))
    items.sort(key=lambda x: x[1], reverse=True)
    return [x[0] for x in items]


def _accurate_project_hit_counts(project_ids, query, top_k_per_project=0):
    """按项目独立检索统计命中，避免受跨项目聚合截断影响。"""
    out = {}
    for pid in (project_ids or []):
        pid_text = str(pid or "").strip()
        if not pid_text:
            continue
        try:
            rows = retrieve_project_kg(pid_text, query, top_k=top_k_per_project)
        except Exception:
            rows = []
        cnt = 0
        for e in rows or []:
            if not isinstance(e, dict):
                continue
            snippet = str(e.get("snippet") or "").strip()
            if not snippet:
                continue
            cnt += 1
        if cnt > 0:
            out[pid_text] = cnt
    return out


def _log_kg_retrieval_console(enabled, phase, evidence, extra_lines=None):
    """在后端终端打印检索摘要；默认由 KG_QA_LOG_RETRIEVAL=true 或 debug_retrieval 开启。"""
    if not enabled:
        return
    print(f"[KG-QA检索] --- {phase} --- evidence_count={len(evidence or [])}", flush=True)
    if extra_lines:
        for x in extra_lines:
            print(f"[KG-QA检索] {x}", flush=True)
    for i, e in enumerate((evidence or [])[:12]):
        if not isinstance(e, dict):
            continue
        sn = str(e.get("snippet") or "")[:160].replace("\n", " ")
        print(
            f"[KG-QA检索]   [{i + 1}] pid={e.get('project_id')} src={e.get('source')} "
            f"node_id={e.get('node_id')} {sn}",
            flush=True,
        )


def _run_kg_qa_core(data):
    """
    返回：
      {"kind": "error", "result": {...}}
      {"kind": "ok", "result": {"code":0,"data":{...}}}  # 无需 LLM 或缓存整包命中
      {"kind": "llm", ...}  # 需调用 LLM，含 finalize(answer_str)->data 及缓存字段
    """
    data = data or {}
    debug_retrieval = _parse_bool(data.get("debug_retrieval"), False) or _parse_bool(
        os.getenv("KG_QA_DEBUG_RETRIEVAL", ""), False
    )
    log_retrieval_console = _parse_bool(os.getenv("KG_QA_LOG_RETRIEVAL", "true"), True) or debug_retrieval
    user_id = data.get("user_id")
    query = (data.get("query") or "").strip()
    deep_think = _parse_bool(data.get("deep_think", False), False)
    detail_level = str(data.get("detail_level") or "brief").strip().lower()
    try:
        top_k_per_project = int(data.get("top_k_per_project") or 0)
    except Exception:
        top_k_per_project = 0
    intent_mode = str(data.get("intent_mode") or "auto").strip().lower()
    allow_general_fallback = _parse_bool(data.get("allow_general_fallback", True), True)
    enable_web_search = _parse_bool(data.get("enable_web_search", False), False)
    web_project_id = str(data.get("project_id") or "").strip()
    enable_function_calling = _parse_bool(
        data.get("enable_function_calling"),
        _parse_bool(os.getenv("KG_QA_FUNCTION_CALLING_ENABLED", "true"), True),
    )
    # 开启联网补强且未显式传模式时：默认「每次都尝试」合并网页摘要（旧默认 when_weak_evidence 在图谱证据充足时永远不会联网）
    _raw_ws = data.get("web_search_mode")
    if _raw_ws is None or (isinstance(_raw_ws, str) and not str(_raw_ws).strip()):
        web_search_mode = "always" if enable_web_search else "when_weak_evidence"
    else:
        web_search_mode = str(_raw_ws).strip().lower()

    if detail_level not in ("brief", "detailed"):
        detail_level = "brief"
    # 0 表示不限量：检索覆盖用户全部项目中的全部图谱证据。
    if intent_mode not in ("auto", "kg", "general"):
        intent_mode = "auto"
    if web_search_mode not in ("always", "when_weak_evidence", "never"):
        web_search_mode = "always" if enable_web_search else "when_weak_evidence"
    # 未开启联网补强时一律不检索网页，忽略客户端误传的 web_search_mode
    if not enable_web_search:
        web_search_mode = "never"

    if user_id is None or not str(user_id).strip():
        return {"kind": "error", "result": {"code": 1, "msg": "fail", "data": "user_id is required"}}
    if not query:
        return {"kind": "error", "result": {"code": 1, "msg": "fail", "data": "query is required"}}

    use_session_history = _parse_bool(data.get("use_session_history", True), True)
    prior_msgs = []
    if use_session_history and str(data.get("session_id") or "").strip():
        prior_msgs = load_prior_messages_for_session(
            data.get("session_id"),
            user_id,
            username=data.get("username"),
            uid=data.get("uid"),
        )
    history_text = _session_history_for_intent(prior_msgs)
    retrieval_query = _build_retrieval_query(query, prior_msgs)
    _anchor, _tokens = _merge_retrieval_tokens(
        retrieval_query,
        max_tokens=max(12, _env_int("KG_QA_RETRIEVAL_TOKEN_CAP", 20)),
    )
    web_query = _anchor or query
    prior_for_llm = prior_msgs if prior_msgs else None

    ctx = AgentContext(
        user_id=user_id,
        query=query,
        detail_level=detail_level,
        deep_think=deep_think,
        top_k_per_project=top_k_per_project,
        intent_mode=intent_mode,
        session_id=str(data.get("session_id") or "").strip() or None,
        username=data.get("username"),
        uid=data.get("uid"),
        use_session_history=use_session_history,
        prior_messages=prior_msgs,
        history_text=history_text or None,
        retrieval_query=retrieval_query,
        allow_general_fallback=allow_general_fallback,
        enable_web_search=enable_web_search,
        web_project_id=web_project_id,
        web_search_mode=web_search_mode,
    )

    planner = QueryPlannerAgent()
    plan = planner.plan(
        query=query,
        intent_mode=intent_mode,
        conversation_history=history_text or None,
    )
    ctx.set_plan(plan["intent"], plan["strategy"], plan["legacy_bucket"])
    detected_intent = ctx.detected_intent
    strategy = ctx.strategy
    legacy_bucket = ctx.legacy_bucket
    model_used = "deepseek-reasoner" if deep_think else "deepseek-chat"
    cache_enabled = _parse_bool(os.getenv("KG_QA_CACHE_ENABLED", "true"), True)
    # 调试检索时禁用缓存，避免命中旧结果影响问题定位。
    debug_bypass_cache = debug_retrieval
    if debug_bypass_cache:
        cache_enabled = False
    cache_ttl = max(30, _env_int("KG_QA_CACHE_TTL_SECONDS", 600))
    hist_sig = ""
    if prior_msgs:
        hist_sig = hashlib.md5(
            json.dumps(prior_msgs, ensure_ascii=False).encode("utf-8", errors="ignore")
        ).hexdigest()[:24]
    sess_part = str(data.get("session_id") or "").strip()
    cache_key = hashlib.md5(
        f"{str(user_id).strip()}|{query}|{deep_think}|{detail_level}|{top_k_per_project}|{detected_intent}|{strategy}|{legacy_bucket}|{allow_general_fallback}|{enable_web_search}|{web_project_id}|{web_search_mode}|{enable_function_calling}|{sess_part}|{hist_sig}".encode("utf-8")
    ).hexdigest()

    # --------- 全域图谱预检索：先于意图分流；任意项目在图谱中有命中则强制走图谱问答 ----------
    prefetch_enabled = _parse_bool(os.getenv("KG_QA_PREFETCH_BEFORE_INTENT", "true"), True)
    project_ids_early = list_user_projects(
        user_id,
        data.get("username"),
        data.get("uid"),
        is_admin=data.get("is_admin"),
    )
    evidence_prefetch = []
    retrieval_ttl_early = max(15, _env_int("KG_RETRIEVAL_CACHE_TTL_SECONDS", 120))
    retrieval_digest_early = None
    prefetch_cache_hit = None
    if prefetch_enabled and project_ids_early:
        retrieval_digest_early = hashlib.md5(
            json.dumps(
                {"p": sorted(project_ids_early), "q": retrieval_query, "k": top_k_per_project},
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        if debug_bypass_cache:
            prefetch_cache_hit = False
            evidence_prefetch = cross_project_retrieval_skill(
                project_ids=project_ids_early,
                query=retrieval_query,
                top_k_per_project=top_k_per_project,
            )
            if not evidence_prefetch:
                evidence_prefetch = []
        else:
            _cached_pref = tiered_cache_get(_QA_RETRIEVAL_CACHE_NS, retrieval_digest_early)
            if _cached_pref is not None:
                prefetch_cache_hit = True
                evidence_prefetch = _cached_pref
            else:
                prefetch_cache_hit = False
                evidence_prefetch = cross_project_retrieval_skill(
                    project_ids=project_ids_early,
                    query=retrieval_query,
                    top_k_per_project=top_k_per_project,
                )
                if evidence_prefetch:
                    tiered_cache_set(
                        _QA_RETRIEVAL_CACHE_NS,
                        retrieval_digest_early,
                        evidence_prefetch,
                        retrieval_ttl_early,
                    )
                else:
                    evidence_prefetch = []

    strategy_effective = strategy
    prefetch_can_override = strategy in ("use_general",)
    if (
        prefetch_enabled
        and prefetch_can_override
        and project_ids_early
        and evidence_prefetch
        and not _is_general_chat_query(query)
    ):
        strategy_effective = "use_kg_tools"

    kg_lookup_miss = bool(prefetch_enabled and project_ids_early and not evidence_prefetch)

    _log_kg_retrieval_console(
        log_retrieval_console,
        "预检索(prefetch)",
        evidence_prefetch,
        extra_lines=[
            f"prefetch_enabled={prefetch_enabled} projects={len(project_ids_early or [])} "
            f"cache_hit={prefetch_cache_hit} kg_lookup_miss={kg_lookup_miss}",
            f"prefetch_project_hits={_evidence_count_by_project(evidence_prefetch)}",
            f"retrieval_query_preview={(retrieval_query or '')[:200]!r}",
            f"anchor_preview={(_anchor or '')[:120]!r} tokens={(_tokens or [])[:12]}",
        ],
    )

    def _make_retrieval_debug(extra=None):
        if not debug_retrieval:
            return None
        prefetch_hits = _evidence_count_by_project(evidence_prefetch)
        accurate_hits = _accurate_project_hit_counts(
            project_ids_early,
            query,
            top_k_per_project=0,
        )
        d = {
            "retrieval_query_preview": (retrieval_query or "")[:8000],
            "anchor": (_anchor or "")[:2000],
            "tokens": (_tokens or [])[:50],
            "token_count": len(_tokens or []),
            "prefetch_enabled": prefetch_enabled,
            "prefetch_cache_hit": prefetch_cache_hit,
            "retrieval_digest": retrieval_digest_early,
            "intent_strategy": strategy,
            "strategy_effective": strategy_effective,
            "kg_lookup_miss": kg_lookup_miss,
            "function_calling_enabled": enable_function_calling,
            "debug_bypass_cache": debug_bypass_cache,
            "projects_searched": list(project_ids_early or []),
            "prefetch_evidence_count": len(evidence_prefetch or []),
            "prefetch_project_hits": prefetch_hits,
            "prefetch_project_hit_ids": _project_hit_ids_from_counts(prefetch_hits),
            "accurate_project_hits": accurate_hits,
            "accurate_project_hit_ids": _project_hit_ids_from_counts(accurate_hits),
            "prefetch_evidence": _evidence_snippets_for_debug(evidence_prefetch),
        }
        if extra:
            d.update(extra)
        return d

    # 通用知识路径（LLM）—— 开放域事实查询强制联网搜索
    if strategy_effective == "use_general":
        web_evidence_general = []
        web_meta_general: dict = {}
        # 开放域事实查询（open_domain）且开启联网时，强制搜索网页获取准确信息
        if enable_web_search and detected_intent == INTENT_OPEN_DOMAIN and project_ids_early:
            web_evidence_general, web_meta_general = run_constrained_web_search_multi(
                sorted(project_ids_early),
                web_query,
            )

        msgs, mn, te = _build_general_messages(query, deep_think, detail_level, prior_for_llm)

        # 如果有网页证据，在 system prompt 中提示模型参考
        if web_evidence_general:
            web_refs = []
            for i, ev in enumerate(web_evidence_general[:6], 1):
                snippet = str(ev.get("snippet") or "")[:200]
                url = str(ev.get("url") or "").strip()
                web_refs.append(f"[网页{i}] {snippet}{' 来源: ' + url if url else ''}")
            web_context = "\n".join(web_refs)
            msgs[0]["content"] += (
                f"\n\n【重要】以下网页摘要供你参考，回答时必须结合这些信息，并在引用处标注来源链接：\n{web_context}"
            )

        def _fin_general(ans):
            qh = ["当前回答来源为通用知识，不基于用户图谱证据。"]
            kg_lookup_status = None
            if prefetch_enabled:
                if project_ids_early and kg_lookup_miss:
                    qh.insert(
                        0,
                        "已在您账号下全部项目的知识图谱中检索，未发现与当前问题直接相关的节点或关系证据，已转为通用知识回答。",
                    )
                    kg_lookup_status = "miss"
                elif not project_ids_early:
                    qh.insert(
                        0,
                        "当前账号下无可检索的图谱项目，直接采用通用知识回答。",
                    )
                    kg_lookup_status = "no_projects"
            # 开放域查询有网页证据时更新提示
            if web_evidence_general:
                qh.append(f"部分信息来自网页搜索（共{len(web_evidence_general)}条），已融合到回答中。")
            payload = {
                "answer": ans,
                "style": detail_level,
                "model_used": model_used,
                "intent": detected_intent or INTENT_GENERAL,
                "intent_coarse": legacy_bucket,
                "projects_searched": project_ids_early if project_ids_early else [],
                "evidence": evidence_citation_skill(web_evidence_general) if web_evidence_general else [],
                "confidence": 0.0,
                "stats": {
                    "project_count": len(project_ids_early),
                    "evidence_count": len(web_evidence_general),
                    "top_k_per_project": top_k_per_project,
                },
                "quality_hints": qh,
                "web_search_meta": web_meta_general if web_evidence_general else None,
                "web_search_attempted": bool(web_evidence_general),
            }
            if kg_lookup_status is not None:
                payload["kg_lookup_status"] = kg_lookup_status
            rd = _make_retrieval_debug()
            if rd is not None:
                payload["retrieval_debug"] = rd
            return payload

        return {
            "kind": "llm",
            "messages": msgs,
            "model_name": mn,
            "temperature": te,
            "finalize": _fin_general,
            "cache_key": None,
            "cache_enabled": False,
            "cache_ttl": cache_ttl,
            "should_cache": False,
            "fallback_on_error": "通用问答暂时不可用，请稍后重试。",
        }

    # 平台构建 / 导入 / 项目管理等引导（不检索 Neo4j）
    if strategy_effective == "use_platform_guidance":
        msgs, mn, te = _build_platform_guidance_messages(
            query, detected_intent, deep_think, detail_level, prior_for_llm
        )

        def _fin_platform(ans):
            qh = ["当前为平台能力与流程引导说明。"]
            if prefetch_enabled and project_ids_early and kg_lookup_miss:
                qh.insert(
                    0,
                    "已在全部项目的知识图谱中检索，未发现与问题相关的图谱证据；以下为平台操作说明。",
                )
            elif prefetch_enabled and not project_ids_early:
                qh.insert(0, "当前无可检索项目；以下为平台操作说明。")
            payload = {
                "answer": ans,
                "style": detail_level,
                "model_used": model_used,
                "intent": detected_intent,
                "intent_coarse": legacy_bucket,
                "projects_searched": project_ids_early if project_ids_early else [],
                "evidence": [],
                "confidence": 0.0,
                "stats": {
                    "project_count": len(project_ids_early),
                    "evidence_count": 0,
                    "top_k_per_project": top_k_per_project,
                },
                "quality_hints": qh,
            }
            if prefetch_enabled:
                payload["kg_lookup_status"] = "no_projects" if not project_ids_early else "miss"
            rd = _make_retrieval_debug()
            if rd is not None:
                payload["retrieval_debug"] = rd
            return payload

        return {
            "kind": "llm",
            "messages": msgs,
            "model_name": mn,
            "temperature": te,
            "finalize": _fin_platform,
            "cache_key": None,
            "cache_enabled": False,
            "cache_ttl": cache_ttl,
            "should_cache": False,
            "fallback_on_error": "平台引导暂时不可用，请稍后重试。",
        }

    project_ids = project_ids_early

    if not project_ids:
        if allow_general_fallback:
            msgs, mn, te = _build_general_messages(
                query, deep_think, detail_level, prior_for_llm, no_kg_evidence_prefix=True
            )

            def _fin_noproj(ans):
                pl = {
                    "answer": ans,
                    "style": detail_level,
                    "model_used": model_used,
                    "intent": "kg_fallback_general",
                    "intent_coarse": "general",
                    "projects_searched": [],
                    "evidence": [],
                    "confidence": 0.0,
                    "stats": {
                        "project_count": 0,
                        "evidence_count": 0,
                        "top_k_per_project": top_k_per_project,
                    },
                    "quality_hints": ["未找到当前用户可用项目，已自动回退到通用问答。"],
                }
                rd = _make_retrieval_debug({"note": "no_projects_for_user"})
                if rd is not None:
                    pl["retrieval_debug"] = rd
                return pl

            return {
                "kind": "llm",
                "messages": msgs,
                "model_name": mn,
                "temperature": te,
                "finalize": _fin_noproj,
                "cache_key": None,
                "cache_enabled": False,
                "cache_ttl": cache_ttl,
                "should_cache": False,
                "fallback_on_error": "通用问答暂时不可用，请稍后重试。",
            }
        _nodata = {
            "answer": "当前项目库无相关证据，建议先构建图谱或调整关键词后再提问。",
            "style": detail_level,
            "model_used": model_used,
            "intent": INTENT_KG_QUERY,
            "intent_coarse": "kg",
            "projects_searched": [],
            "evidence": [],
            "confidence": 0.0,
            "stats": {
                "project_count": 0,
                "evidence_count": 0,
                "top_k_per_project": top_k_per_project,
            },
            "quality_hints": [],
        }
        rd = _make_retrieval_debug({"note": "no_projects_ok_payload"})
        if rd is not None:
            _nodata["retrieval_debug"] = rd
        return {
            "kind": "ok",
            "result": {
                "code": 0,
                "msg": "ok",
                "data": _nodata,
            },
        }

    if cache_enabled:
        cached = _cache_get(cache_key)
        if cached is not None:
            return {"kind": "ok", "result": {"code": 0, "msg": "ok", "data": cached}}

    retrieval_ttl = max(15, _env_int("KG_RETRIEVAL_CACHE_TTL_SECONDS", 120))
    retrieval_digest = hashlib.md5(
        json.dumps(
            {"p": sorted(project_ids), "q": retrieval_query, "k": top_k_per_project},
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    # 预检索与主路径 digest 一致：有项目且已预检则直接复用结果（含空列表），避免重复查 Neo4j
    if prefetch_enabled and project_ids_early:
        evidence = evidence_prefetch
    else:
        if debug_bypass_cache:
            evidence = cross_project_retrieval_skill(
                project_ids=project_ids,
                query=retrieval_query,
                top_k_per_project=top_k_per_project,
            )
        else:
            evidence = tiered_cache_get(_QA_RETRIEVAL_CACHE_NS, retrieval_digest)
            if evidence is None:
                evidence = cross_project_retrieval_skill(
                    project_ids=project_ids,
                    query=retrieval_query,
                    top_k_per_project=top_k_per_project,
                )
                # 不把「空检索结果」写入缓存：否则用户入库新节点后仍会长期命中空证据并误走 kg 回退
                if evidence:
                    tiered_cache_set(_QA_RETRIEVAL_CACHE_NS, retrieval_digest, evidence, retrieval_ttl)
    confidence = estimate_confidence(evidence)

    fc_meta = {"enabled": enable_function_calling, "executed": False}
    if strategy_effective == "use_kg_tools" and enable_function_calling:
        weak_for_fc = (
            len(evidence) < max(1, _env_int("KG_QA_FUNCTION_CALLING_TRIGGER_MIN_EVIDENCE", 4))
            or confidence < float(os.getenv("KG_QA_FUNCTION_CALLING_TRIGGER_MAX_CONF", "0.55") or 0.55)
        )
        force_fc = _parse_bool(data.get("force_function_calling"), False)
        if weak_for_fc or force_fc:
            evidence, fc_meta = _function_call_retrieve_enhance(
                enabled=True,
                query=query,
                retrieval_query=retrieval_query,
                user_id=user_id,
                username=data.get("username"),
                project_ids=project_ids,
                base_evidence=evidence,
                top_k_per_project=top_k_per_project,
            )
            confidence = estimate_confidence(evidence)

    web_meta: dict = {}
    web_attempted = False
    if enable_web_search and web_search_mode != "never" and strategy_effective == "use_kg_tools":
        allowed_projects = list(project_ids or [])
        weak = (
            len(evidence) < max(1, _env_int("KG_WEB_SEARCH_TRIGGER_MIN_EVIDENCE", 2))
            or confidence < float(os.getenv("KG_WEB_SEARCH_TRIGGER_MAX_CONF", "0.42") or 0.42)
        )
        do_web = web_search_mode == "always" or (
            web_search_mode == "when_weak_evidence" and weak
        )
        if do_web and allowed_projects:
            web_attempted = True
            wp = str(web_project_id or "").strip()
            allowed_set = set(allowed_projects)
            if wp and wp in allowed_set:
                web_evidence, web_meta = run_constrained_web_search(wp, web_query)
            else:
                web_evidence, web_meta = run_constrained_web_search_multi(
                    sorted(allowed_set),
                    web_query,
                )
            if web_evidence:
                evidence = merge_kg_and_web_evidence(
                    evidence,
                    web_evidence,
                    max_total=max(8, _env_int("KG_QA_MERGED_EVIDENCE_MAX", 14)),
                )
                evidence = _prioritize_web_for_definition_query(evidence, query)
                merged_web_count = sum(
                    1
                    for e in (evidence or [])
                    if isinstance(e, dict) and str(e.get("source") or "") == "constrained_web"
                )
                if isinstance(web_meta, dict):
                    web_meta["merged_into_final"] = int(merged_web_count)
                    web_meta["merged_result_count"] = int(merged_web_count)
                confidence = estimate_confidence(evidence)

    _log_kg_retrieval_console(
        log_retrieval_console,
        "主路径(合并联网后)",
        evidence,
        extra_lines=[
            f"strategy_effective={strategy_effective} projects_searched={len(project_ids or [])} "
            f"confidence={confidence:.3f} web_attempted={web_attempted}",
            f"final_project_hits={_evidence_count_by_project(evidence)}",
            f"web_meta_keys={list((web_meta or {}).keys())}",
        ],
    )

    if not evidence:
        if allow_general_fallback:
            msgs, mn, te = _build_general_messages(
                query, deep_think, detail_level, prior_for_llm, no_kg_evidence_prefix=True
            )

            def _fin_weak(ans):
                qh_miss = [
                    "已在您账号下全部项目的知识图谱中检索，未发现与当前问题匹配的节点或关系证据，已转为通用知识回答。"
                ]
                pl = {
                    "answer": ans,
                    "style": detail_level,
                    "model_used": model_used,
                    "intent": "kg_fallback_general",
                    "intent_coarse": "general",
                    "projects_searched": project_ids,
                    "evidence": [],
                    "confidence": 0.0,
                    "stats": {
                        "project_count": len(project_ids),
                        "evidence_count": 0,
                        "top_k_per_project": top_k_per_project,
                    },
                    "quality_hints": qh_miss,
                    "kg_lookup_status": "miss",
                }
                rd = _make_retrieval_debug(
                    {
                        "note": "kg_path_after_web_merge_still_empty",
                        "final_evidence_count": 0,
                        "final_evidence": [],
                    }
                )
                if rd is not None:
                    pl["retrieval_debug"] = rd
                return pl

            return {
                "kind": "llm",
                "messages": msgs,
                "model_name": mn,
                "temperature": te,
                "finalize": _fin_weak,
                "cache_key": cache_key,
                "cache_enabled": cache_enabled,
                "cache_ttl": cache_ttl,
                "should_cache": False,
                "fallback_on_error": "通用问答暂时不可用，请稍后重试。",
            }
        payload_no_evidence = {
            "answer": "当前项目库无相关证据，建议先构建图谱或调整关键词后再提问。",
            "style": detail_level,
            "model_used": model_used,
            "intent": INTENT_KG_QUERY,
            "intent_coarse": "kg",
            "projects_searched": project_ids,
            "evidence": [],
            "confidence": 0.0,
            "stats": {
                "project_count": len(project_ids),
                "evidence_count": 0,
                "top_k_per_project": top_k_per_project,
            },
            "quality_hints": [],
        }
        rd = _make_retrieval_debug(
            {"note": "allow_general_fallback_false_no_evidence", "final_evidence_count": 0}
        )
        if rd is not None:
            payload_no_evidence["retrieval_debug"] = rd
        # 无证据结果不入缓存，避免图谱更新后仍命中旧 miss。
        return {"kind": "ok", "result": {"code": 0, "msg": "ok", "data": payload_no_evidence}}

    msgs, mn, te = _build_evidence_messages(
        query, evidence, deep_think, detail_level, prior_for_llm
    )

    def _fin_kg(ans):
        citations = evidence_citation_skill(evidence)
        qh = list(conflict_awareness_skill(evidence))
        final_hits = _evidence_count_by_project(evidence)
        qh.insert(
            0,
            "图谱类与网页摘要类证据已在 evidence 中标注类型；正文为无前缀段落的综合叙述，附录为「参考与证据」一节（网页须含可点击链接）。",
        )
        if fc_meta.get("executed"):
            if int(fc_meta.get("added_evidence") or 0) > 0:
                qh.append(
                    f"本轮已启用 function-calling 检索增强，新增候选证据 {int(fc_meta.get('added_evidence') or 0)} 条。"
                )
            else:
                qh.append("本轮已启用 function-calling 检索增强，但未检出新增有效证据。")
        _rc = (web_meta or {}).get("result_count")
        n_web = int(_rc) if _rc is not None else 0
        if n_web > 0:
            qh.append(
                "部分证据来自网页摘要（检索查询已由本项目已选公告样本锚定约束）；请勿等同于上市公司公告原文。"
            )
        elif enable_web_search and web_attempted:
            qh.append(
                "已开启联网补强：本次未合并网页摘要（常见原因：项目未选取公告样本导致无法锚定检索词；或服务端未安装 ddgs / 外网检索失败）。详见 web_search_meta。"
            )
        out_kg = {
            "answer": ans,
            "style": detail_level,
            "model_used": model_used,
            "intent": INTENT_KG_QUERY,
            "intent_coarse": "kg",
            "projects_searched": project_ids,
            "evidence": citations,
            "confidence": confidence,
            "stats": {
                "project_count": len(project_ids),
                "evidence_count": len(evidence),
                "top_k_per_project": top_k_per_project,
            },
            "quality_hints": qh,
            "web_search_meta": web_meta if web_meta else None,
            "web_search_attempted": web_attempted,
            "function_calling": fc_meta,
        }
        if prefetch_enabled:
            out_kg["kg_lookup_status"] = "hit"
        rd = _make_retrieval_debug(
            {
                "final_evidence_count": len(evidence),
                "final_project_hits": final_hits,
                "final_project_hit_ids": _project_hit_ids_from_counts(final_hits),
                "final_evidence": _evidence_snippets_for_debug(evidence),
                "web_search_attempted": web_attempted,
                "web_search_meta": web_meta if web_meta else None,
                "function_calling": fc_meta,
            }
        )
        if rd is not None:
            out_kg["retrieval_debug"] = rd
        return out_kg

    return {
        "kind": "llm",
        "messages": msgs,
        "model_name": mn,
        "temperature": te,
        "finalize": _fin_kg,
        "cache_key": cache_key,
        "cache_enabled": cache_enabled,
        "cache_ttl": cache_ttl,
        "should_cache": cache_enabled,
        "fallback_on_error": _fallback_text_from_evidence(evidence),
    }


def run_kg_qa(payload):
    """
    统一的 AI-Chat Agent 流程（供 /kg-qa 和兼容接口 /askAI 共用）。
    可选：enable_web_search + project_id；未传 web_search_mode 且 enable_web_search=true 时默认 always，
    按「项目已选样本」锚定追加网页摘要（非公告原文）。显式 web_search_mode=when_weak_evidence 则仅在图谱证据偏弱时联网。
    调试：请求体 debug_retrieval=true 或环境变量 KG_QA_DEBUG_RETRIEVAL=true 时，data 中附带 retrieval_debug（检索串、分词、预检索证据摘要等）。
    """
    core = _run_kg_qa_core(payload or {})
    if core.get("kind") == "error":
        return core["result"]
    if core.get("kind") == "ok":
        return core["result"]
    if core.get("kind") == "llm":
        try:
            answer_text = _call_chat_completion(
                messages=core["messages"],
                model_name=core["model_name"],
                temperature=core["temperature"],
            )
        except Exception:
            traceback.print_exc()
            answer_text = core.get("fallback_on_error") or "回答生成失败，请稍后重试。"
        data_payload = core["finalize"](answer_text)
        if core.get("should_cache") and core.get("cache_key") and core.get("cache_enabled"):
            _cache_set(core["cache_key"], data_payload, core["cache_ttl"])
        return {"code": 0, "msg": "ok", "data": data_payload}
    return {"code": 1, "msg": "fail", "data": "internal routing error"}


def _attach_session_after_persist(req_data, data_payload):
    """写入 chat 历史并在 data 中附带 session_id（与 /kg-qa 一致）。"""
    if not _parse_bool((req_data or {}).get("save_history", True), True):
        return data_payload
    uid = (req_data or {}).get("user_id")
    q = ((req_data or {}).get("query") or "").strip()
    if not uid or not q:
        return data_payload
    sid = persist_chat_turn(
        user_id=uid,
        session_id=(req_data or {}).get("session_id"),
        user_query=q,
        result_payload={"code": 0, "data": data_payload},
    )
    out = dict(data_payload) if isinstance(data_payload, dict) else {"answer": str(data_payload)}
    out["session_id"] = sid
    return out


def _ndjson(obj):
    return json.dumps(obj, ensure_ascii=False) + "\n"


def iter_kg_qa_stream_lines(req_data):
    """
    NDJSON 流：若干行 {"type":"delta","text":"..."}，深度模型另含 {"type":"reasoning_delta","text":"..."}；
    最后一行 {"type":"done","code":0,"data":{...}}（data 可含 reasoning 全文）；
    错误：单行 {"type":"error","code":1,...}
    """
    data = req_data or {}
    core = _run_kg_qa_core(data)
    if core.get("kind") == "error":
        r = core["result"]
        yield _ndjson(
            {
                "type": "error",
                "code": r.get("code", 1),
                "msg": r.get("msg", "fail"),
                "data": r.get("data"),
            }
        )
        return
    if core.get("kind") == "ok":
        dp = core["result"]["data"]
        text = str((dp or {}).get("answer") or "")
        if text:
            yield _ndjson({"type": "delta", "text": text})
        dp2 = _attach_session_after_persist(data, dp)
        yield _ndjson({"type": "done", "code": 0, "data": dp2})
        return
    if core.get("kind") == "llm":
        reasoning_parts = []
        content_parts = []
        try:
            for piece in _stream_chat_completion_chunks(
                core["messages"],
                core["model_name"],
                core["temperature"],
            ):
                if not isinstance(piece, dict):
                    continue
                rp = piece.get("reasoning") or ""
                cp = piece.get("content") or ""
                if rp:
                    reasoning_parts.append(rp)
                    yield _ndjson({"type": "reasoning_delta", "text": rp})
                if cp:
                    content_parts.append(cp)
                    yield _ndjson({"type": "delta", "text": cp})
        except Exception:
            traceback.print_exc()
            fb = core.get("fallback_on_error") or "回答生成失败，请稍后重试。"
            content_parts = [fb]
            yield _ndjson({"type": "delta", "text": fb})
        answer_text = "".join(content_parts)
        data_payload = core["finalize"](answer_text)
        if core.get("should_cache") and core.get("cache_key") and core.get("cache_enabled"):
            _cache_set(core["cache_key"], data_payload, core["cache_ttl"])
        rs = "".join(reasoning_parts).strip()
        if rs and isinstance(data_payload, dict):
            data_payload["reasoning"] = rs
        data_payload = _attach_session_after_persist(data, data_payload)
        yield _ndjson({"type": "done", "code": 0, "data": data_payload})
        return
    yield _ndjson({"type": "error", "code": 1, "msg": "fail", "data": "stream internal error"})


@askAI_bp.route("/tools/constrained-web-search", methods=["POST"])
def constrained_web_search_tool():
    """
    Tool：基于项目已选样本锚定的受限网页检索（不放飞查询词）。
    请求体：user_id, project_id, query（可选 max_results）
    """
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id")
        project_id = str(data.get("project_id") or "").strip()
        query = str(data.get("query") or "").strip()
        if not user_id or not str(user_id).strip():
            return jsonify({"code": 1, "msg": "fail", "data": "user_id is required"})
        if not project_id or not query:
            return jsonify({"code": 1, "msg": "fail", "data": "project_id and query are required"})
        allowed = get_user_project_ids(
            user_id,
            data.get("username"),
            data.get("uid"),
            is_admin=data.get("is_admin"),
        )
        if project_id not in set(allowed or []):
            return jsonify({"code": 1, "msg": "fail", "data": "project not found or access denied"})
        max_r = data.get("max_results")
        mr = int(max_r) if max_r is not None else None
        evidence, meta = run_constrained_web_search(project_id, query, max_results=mr)
        return jsonify({"code": 0, "msg": "ok", "data": {"evidence": evidence, "meta": meta}})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"code": 1, "msg": "fail", "data": str(e)})


@askAI_bp.route("/kg-qa", methods=['POST'])
def kg_qa():
    """
    Step-2: kg-qa 固定契约接口（先保证前后端字段稳定，复杂检索后续增强）。
    Step-3: 使用 Tool-1 对 user_id 执行项目范围过滤，避免越权。
    """
    try:
        data = request.get_json() or {}
        result = run_kg_qa(data)
        if result.get("code") == 0 and _parse_bool(data.get("save_history", True), True):
            user_id = data.get("user_id")
            query = (data.get("query") or "").strip()
            if user_id and query:
                sid = persist_chat_turn(
                    user_id=user_id,
                    session_id=data.get("session_id"),
                    user_query=query,
                    result_payload=result
                )
                result["data"]["session_id"] = sid
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"code": 1, "msg": "fail", "data": str(e)})


@askAI_bp.route("/chat/kg-qa-stream", methods=["POST"])
@askAI_bp.route("/kg-qa-stream", methods=["POST"])
def kg_qa_stream():
    """NDJSON 流式问答（与 run_kg_qa 同一套逻辑，末段 LLM 按 token 增量输出）。

    主路径与 /chat/get/history 同级，便于网关与 /old-api/chat/* 一致转发；
    /kg-qa-stream 为兼容别名。
    """
    try:
        data = request.get_json() or {}

        def generate():
            for line in iter_kg_qa_stream_lines(data):
                yield line

        return Response(
            stream_with_context(generate()),
            mimetype="application/x-ndjson; charset=utf-8",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        traceback.print_exc()
        return jsonify({"code": 1, "msg": "fail", "data": str(e)})


@askAI_bp.route("/askAI", methods = ['POST'])
def getAIResponse():
    """
    旧接口兼容层：统一转发到当前 Agent 版流程。
    - 旧参数：id/query
    - 新流程参数：user_id/query
    """
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id") or data.get("creator") or data.get("username")
        project_id = data.get("id")
        query = data.get("query")
        deep_think = _parse_bool(data.get("deep_think"), False)
        detail_level = data.get("detail_level", "brief")
        top_k_per_project = int(data.get("top_k_per_project", 3))

        if user_id:
            mapped = {
                "user_id": user_id,
                "username": data.get("username"),
                "uid": data.get("uid"),
                "query": query,
                "deep_think": deep_think,
                "detail_level": detail_level,
                "top_k_per_project": top_k_per_project,
                "session_id": data.get("session_id"),
                "use_session_history": data.get("use_session_history", True),
                "save_history": data.get("save_history", True),
                "intent_mode": data.get("intent_mode", "auto"),
                "allow_general_fallback": data.get("allow_general_fallback", True),
                "enable_web_search": data.get("enable_web_search", False),
                "project_id": data.get("project_id") or project_id,
                "web_search_mode": data.get("web_search_mode"),
            }
            result = run_kg_qa(mapped)
            if result.get("code") != 0:
                return jsonify({"status": 500, "answer": result.get("data", "问答失败"), "raw": result})
            data_payload = result.get("data") or {}
            data_payload = _attach_session_after_persist(mapped, data_payload)
            return jsonify({"status": 200, "answer": data_payload.get("answer", ""), "data": data_payload})

        # 仅传 project_id 的旧调用：执行单项目问答兼容逻辑（不依赖旧 GraphRAG）。
        if not project_id or not str(project_id).strip():
            return jsonify({"status": 500, "answer": "问答失败: 缺少 user_id 或 id(project_id)"})
        if not query or not str(query).strip():
            return jsonify({"status": 500, "answer": "问答失败: query 不能为空"})
        evidence = retrieve_project_kg(project_id, query, top_k=top_k_per_project)
        answer = generate_answer_from_evidence(
            query=query,
            evidence=evidence,
            deep_think=deep_think,
            detail_level=detail_level if str(detail_level).strip().lower() in ("brief", "detailed") else "brief",
        )
        payload = {
            "answer": answer,
            "style": detail_level,
            "model_used": "deepseek-reasoner" if deep_think else "deepseek-chat",
            "projects_searched": [str(project_id)],
            "evidence": evidence,
            "confidence": estimate_confidence(evidence),
            "stats": {
                "project_count": 1,
                "evidence_count": len(evidence),
                "top_k_per_project": top_k_per_project
            },
            "quality_hints": detect_conflict_hints(evidence),
        }
        return jsonify({"status": 200, "answer": answer, "data": payload})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": 500, "answer": f"问答失败: {e}"})


@askAI_bp.route("/chat/get/historyList", methods=['GET', 'POST'])
def get_chat_history_list():
    """
    历史会话列表：
    返回结构兼容前端 ChatHistoryListResponse：{session_id: [{role, content}, ...]}
    """
    try:
        params = request.get_json(silent=True) or {}
        user_id = params.get("user_id") or request.args.get("user_id")
        username = params.get("username") or request.args.get("username")
        uid = params.get("uid") or request.args.get("uid")
        limit = int(params.get("limit") or request.args.get("limit") or 50)
        candidates = []
        for raw in (user_id, username, uid):
            if raw is None:
                continue
            t = str(raw).strip()
            if t and t not in candidates:
                candidates.append(t)
        if not candidates:
            return jsonify({"code": 1, "msg": "fail", "data": "user_id is required"})

        client = get_client()
        try:
            with client.cursor() as cursor:
                placeholders = ",".join(["%s"] * len(candidates))
                cursor.execute(
                    f"""
                    SELECT session_id, title
                    FROM finkg1.chat_session
                    WHERE is_deleted = 0
                      AND TRIM(user_id) IN ({placeholders})
                    ORDER BY COALESCE(last_message_at, updated_at, created_at) DESC
                    LIMIT %s
                    """,
                    tuple(candidates + [max(1, limit)])
                )
                sessions = cursor.fetchall() or []

                result = {}
                session_titles = {}
                for s in sessions:
                    sid = s.get("session_id")
                    if not sid:
                        continue
                    raw_title = (s.get("title") or "").strip()
                    if raw_title:
                        session_titles[str(sid)] = raw_title
                    cursor.execute(
                        """
                        SELECT role, content, extra_json
                        FROM finkg1.chat_message
                        WHERE session_id = %s
                        ORDER BY id ASC
                        LIMIT 6
                        """,
                        (sid,)
                    )
                    msgs = cursor.fetchall() or []
                    result[str(sid)] = [_serialize_chat_history_row(m) for m in msgs]
            return jsonify({"code": 0, "msg": "ok", "data": result, "session_titles": session_titles})
        finally:
            client.close()
    except Exception as e:
        traceback.print_exc()
        return jsonify({"code": 1, "msg": "fail", "data": str(e)})


@askAI_bp.route("/chat/delete/session", methods=['POST'])
def delete_chat_session():
    """
    软删除会话：chat_session.is_deleted = 1
    """
    try:
        params = request.get_json() or {}
        session_id = str(params.get("session_id") or "").strip()
        user_id = params.get("user_id")
        username = params.get("username")
        uid = params.get("uid")
        if not session_id:
            return jsonify({"code": 1, "msg": "fail", "data": "session_id is required"})
        candidates = []
        for raw in (user_id, username, uid):
            if raw is None:
                continue
            t = str(raw).strip()
            if t and t not in candidates:
                candidates.append(t)
        if not candidates:
            return jsonify({"code": 1, "msg": "fail", "data": "user_id is required"})

        client = get_client()
        try:
            with client.cursor() as cursor:
                placeholders = ",".join(["%s"] * len(candidates))
                cursor.execute(
                    f"""
                    UPDATE finkg1.chat_session
                    SET is_deleted = 1, updated_at = %s
                    WHERE session_id = %s
                      AND TRIM(user_id) IN ({placeholders})
                    """,
                    tuple([_now_sql(), session_id] + candidates)
                )
                affected = cursor.rowcount or 0
            client.commit()
            if affected <= 0:
                return jsonify({"code": 1, "msg": "fail", "data": "session not found or no permission"})
            return jsonify({"code": 0, "msg": "ok", "data": {"session_id": session_id, "deleted": True}})
        finally:
            client.close()
    except Exception as e:
        traceback.print_exc()
        return jsonify({"code": 1, "msg": "fail", "data": str(e)})


@askAI_bp.route("/chat/rename/session", methods=["POST"])
def rename_chat_session():
    """更新会话自定义标题（chat_session.title）。"""
    try:
        params = request.get_json() or {}
        session_id = str(params.get("session_id") or "").strip()
        title = str(params.get("title") or "").strip()
        user_id = params.get("user_id")
        username = params.get("username")
        uid = params.get("uid")
        if not session_id:
            return jsonify({"code": 1, "msg": "fail", "data": "session_id is required"})
        if not title:
            return jsonify({"code": 1, "msg": "fail", "data": "title is required"})
        title = title[:500]
        candidates = []
        for raw in (user_id, username, uid):
            if raw is None:
                continue
            t = str(raw).strip()
            if t and t not in candidates:
                candidates.append(t)
        if not candidates:
            return jsonify({"code": 1, "msg": "fail", "data": "user_id is required"})

        client = get_client()
        try:
            with client.cursor() as cursor:
                placeholders = ",".join(["%s"] * len(candidates))
                cursor.execute(
                    f"""
                    UPDATE finkg1.chat_session
                    SET title = %s, updated_at = %s
                    WHERE session_id = %s
                      AND is_deleted = 0
                      AND TRIM(user_id) IN ({placeholders})
                    """,
                    tuple([title, _now_sql(), session_id] + candidates),
                )
                affected = cursor.rowcount or 0
            client.commit()
            if affected <= 0:
                return jsonify({"code": 1, "msg": "fail", "data": "session not found or no permission"})
            return jsonify({"code": 0, "msg": "ok", "data": {"session_id": session_id, "title": title}})
        finally:
            client.close()
    except Exception as e:
        traceback.print_exc()
        return jsonify({"code": 1, "msg": "fail", "data": str(e)})


@askAI_bp.route("/chat/get/history", methods=['POST'])
def get_chat_history():
    """
    获取单个会话完整历史。
    """
    try:
        params = request.get_json() or {}
        session_id = str(params.get("session_id") or "").strip()
        if not session_id:
            return jsonify({"code": 1, "msg": "fail", "data": "session_id is required"})

        client = get_client()
        try:
            with client.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT role, content, extra_json
                    FROM finkg1.chat_message
                    WHERE session_id = %s
                    ORDER BY id ASC
                    """,
                    (session_id,)
                )
                rows = cursor.fetchall() or []
                history = [_serialize_chat_history_row(r) for r in rows]
            return jsonify({"code": 0, "msg": "ok", "data": history})
        finally:
            client.close()
    except Exception as e:
        traceback.print_exc()
        return jsonify({"code": 1, "msg": "fail", "data": str(e)})


@askAI_bp.route('/kg_quality_analysis', methods=['POST'])
def kg_quality_analysis():
    """意图识别到“KG 构建质量分析”后，调用质量分析 Agent 生成简报。"""
    try:
        data = request.get_json() or {}
        query = str(data.get('query') or '').strip()
        project_id = str(data.get('project_id') or '').strip()
        run_id = str(data.get('run_id') or '').strip()
        workflow_meta = data.get('workflow_meta') if isinstance(data.get('workflow_meta'), dict) else None
        conflicts = data.get('conflicts') if isinstance(data.get('conflicts'), list) else []
        user_hint = str(data.get('user_hint') or '').strip()

        if not query:
            return jsonify({'code': 1, 'msg': 'fail', 'data': 'query is required'}), 400

        if not is_kg_quality_report_analysis_query(query):
            return jsonify({
                'code': 0,
                'msg': 'ok',
                'data': {
                    'intent_hit': False,
                    'answer': '当前问题未命中“KG 构建质量分析”意图，请补充如“质量报告分析/构建效果分析”等关键词。',
                },
            })

        if not workflow_meta and project_id and run_id:
            try:
                from routes.llmGenKG_api import _load_extraction_snapshot

                snap = _load_extraction_snapshot(project_id, run_id)
                wm = snap.get('workflow_meta')
                if isinstance(wm, dict):
                    workflow_meta = wm
            except Exception:
                workflow_meta = workflow_meta or {}

        if not workflow_meta:
            return jsonify({'code': 1, 'msg': 'fail', 'data': 'workflow_meta is required'}), 400

        report_text, metrics = generate_kg_quality_analysis_report(
            workflow_meta=workflow_meta,
            conflict_details=conflicts,
            user_hint=user_hint,
        )

        return jsonify({
            'code': 0,
            'msg': 'ok',
            'data': {
                'intent_hit': True,
                'intent': 'kg_build',
                'run_id': run_id or str(workflow_meta.get('run_id') or ''),
                'answer': report_text,
                'metrics': metrics,
            },
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'code': 1, 'msg': 'fail', 'data': str(e)}), 500
