# -*- coding: utf-8 -*-
"""
KG 问答链路 Tool 声明（OpenAI-style JSON Schema），供动态发现、文档生成或与 LLM function-calling 对接。

实现函数仍在 routes/askAI_api.py；此处仅登记契约，避免循环 import。
"""
from __future__ import annotations

from typing import Any, Dict, List

ToolSpec = Dict[str, Any]


def list_kg_qa_tool_specs() -> List[ToolSpec]:
    """固定顺序的工具列表（名称与代码侧函数名对应）。"""
    return [
        {
            "name": "get_user_project_ids",
            "implementation": "backend.routes.askAI_api.get_user_project_ids",
            "description": "根据用户标识查询其可见的知识图谱项目 ID 列表（MySQL graph_project）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "当前用户 ID（与登录态一致）",
                    }
                },
                "required": ["user_id"],
            },
        },
        {
            "name": "retrieve_project_kg",
            "implementation": "backend.routes.askAI_api.retrieve_project_kg",
            "description": "在指定 Neo4j 项目中：先按 context 关键词匹配节点，再对命中节点做 1-hop 边邻接扩展，返回带 source（如 neo4j_neighbor）的证据列表。",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "图谱项目 ID"},
                    "query": {"type": "string", "description": "检索关键词或问句"},
                    "top_k": {
                        "type": "integer",
                        "description": "单项目返回的最大条数",
                        "default": 3,
                    },
                },
                "required": ["project_id", "query"],
            },
        },
        {
            "name": "aggregate_evidence",
            "implementation": "backend.routes.askAI_api.aggregate_evidence",
            "description": "合并多源证据、去重、按得分截断。",
            "parameters": {
                "type": "object",
                "properties": {
                    "chunks": {
                        "type": "object",
                        "description": "project_id -> evidence[] 映射",
                    },
                    "max_items": {"type": "integer", "default": 12},
                },
                "required": ["chunks"],
            },
        },
        {
            "name": "generate_answer_from_evidence",
            "implementation": "backend.routes.askAI_api.generate_answer_from_evidence",
            "description": "基于证据链与问句调用 LLM 生成自然语言答案。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "evidence": {"type": "array", "items": {"type": "object"}},
                    "deep_think": {"type": "boolean", "default": False},
                    "detail_level": {
                        "type": "string",
                        "enum": ["brief", "detailed"],
                        "default": "brief",
                    },
                    "prior_messages": {
                        "type": "array",
                        "description": "可选多轮对话 user/assistant 消息",
                    },
                },
                "required": ["query", "evidence"],
            },
        },
        {
            "name": "run_constrained_web_search",
            "implementation": "backend.agents.constrained_web_search.run_constrained_web_search",
            "description": "在项目已选样本锚定约束下执行网页检索，证据格式与图谱检索对齐。",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "query": {"type": "string"},
                },
                "required": ["project_id", "query"],
            },
        },
        {
            "name": "merge_kg_and_web_evidence",
            "implementation": "backend.agents.constrained_web_search.merge_kg_and_web_evidence",
            "description": "图谱证据优先合并网页摘要，控制总条数上限。",
            "parameters": {
                "type": "object",
                "properties": {
                    "kg_evidence": {"type": "array"},
                    "web_evidence": {"type": "array"},
                    "max_total": {"type": "integer"},
                },
                "required": ["kg_evidence", "web_evidence"],
            },
        },
    ]


def tool_specs_as_prompt_block(max_tools: int = 32) -> str:
    """生成可供 LLM 阅读的精简工具目录（非严格 JSON 模式）。"""
    lines = []
    for spec in list_kg_qa_tool_specs()[:max_tools]:
        name = spec.get("name")
        desc = spec.get("description") or ""
        lines.append(f"- {name}: {desc}")
    return "\n".join(lines)
