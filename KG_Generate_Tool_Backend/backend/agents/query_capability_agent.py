from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

if __package__ in (None, ""):
    _BACKEND_ROOT = Path(__file__).resolve().parents[1]
    if str(_BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(_BACKEND_ROOT))

from agents.cache_layers import cache_clear_namespace, cache_get, cache_set, cache_stats
from agents.intent_taxonomy import (
    INTENT_DATA_IMPORT,
    INTENT_GENERAL,
    INTENT_KG_BUILD,
    INTENT_KG_QUERY,
    INTENT_OPEN_DOMAIN,
    INTENT_PLATFORM_HELP,
    INTENT_PROJECT_MGMT,
    INTENT_TOOL_CALL,
)

_INTENT_CACHE_NS = "intent"
_INTENT_CACHE_TTL_SECONDS = int(os.getenv("KG_INTENT_CACHE_TTL_SECONDS", "300"))


def _make_intent_cache_key(query: str, history: str) -> str:
    normalized = f"{query.strip().lower()}|{history.strip()[-200:]}"
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


# ---------------------------
# 关键词库配置
# ---------------------------

_KG_KEYWORDS = {
    "图谱",
    "知识图谱",
    "知识地图",
    "抽取项目",
    "抽取类",
    "跨项目",
    "各项目",
    "多项目",
    "全项目",
    "全部项目数据",
    "项目图谱",
    "图谱数据",
    "KG",
    "knowledge graph",
    "节点",
    "实体",
    "对象",
    "概念",
    "主体",
    "客体",
    "关系",
    "边",
    "联系",
    "关联",
    "连接",
    "指向",
    "指向性",
    "项目",
    "我的项目",
    "我构建",
    "我的数据",
    "私有数据",
    "自建数据",
    "证据",
    "事件",
    "事件库",
    "事实",
    "资讯",
    "公告",
    "样本",
    "查询",
    "检索",
    "查找",
    "搜索",
    "定位",
    "匹配",
    "分析",
    "挖掘",
    "洞察",
    "发现",
    "探索",
    "梳理",
    "总结",
    "公司",
    "企业",
    "股票",
    "风险",
    "关联",
    "股东",
    "高管",
    "投资",
    "并购",
    "收购",
    "合并",
    "成立",
    "注册",
    "资本",
    "财报",
    "年报",
}

_GENERAL_KEYWORDS = {
    "你好",
    "您好",
    "hi",
    "hello",
    "hey",
    "嗨",
    "哈喽",
    "hello there",
    "在吗",
    "在不在",
    "谢谢",
    "感谢",
    "再见",
    "拜拜",
    "什么是",
    "什么叫",
    "介绍一下",
    "解释一下",
    "说明一下",
    "给我讲讲",
    "跟我说说",
    "你能",
    "你可以",
    "支持",
    "有没有",
    "是否有",
    "能否",
    "今天",
    "明天",
    "昨天",
    "天气",
    "温度",
    "时间",
    "日期",
    "星期",
    "多少钱",
    "价格",
    "费用",
    "成本",
}

_SMALL_TALK_EXACT_PATTERNS = {
    "hi",
    "hello",
    "hey",
    "hey there",
    "hello there",
    "你好",
    "您好",
    "嗨",
    "哈喽",
    "在吗",
    "在不在",
    "忙吗",
    "谢谢",
    "感谢",
    "拜拜",
    "再见",
}

_ASSISTANT_CAPABILITY_PATTERNS = {
    "你是谁",
    "你是",
    "你叫什么",
    "你叫啥",
    "你能做什么",
    "你可以做什么",
    "你会什么",
    "你会做什么",
    "你能帮我什么",
    "你有什么功能",
    "你有哪些功能",
    "你支持什么",
    "你都能做什么",
    "你是做什么的",
    "怎么用你",
    "如何使用你",
}

_PLATFORM_HELP_PATTERNS = {
    "平台怎么用",
    "这个平台怎么用",
    "系统怎么用",
    "这个系统怎么用",
    "平台如何使用",
    "系统如何使用",
    "怎么使用这个平台",
    "如何使用这个平台",
    "怎么使用这个系统",
    "如何使用这个系统",
    "平台如何操作",
    "系统如何操作",
    "平台操作流程",
    "系统操作流程",
    "平台使用说明",
    "系统使用说明",
    "平台使用指南",
    "系统使用指南",
    "怎么开始使用",
    "如何开始使用",
    "从哪里开始",
    "从哪开始",
    "先做什么",
    "入门",
    "上手",
    "功能介绍",
    "平台介绍",
    "系统介绍",
    "平台功能",
    "系统功能",
    "平台能做什么",
    "系统能做什么",
    "这个平台能做什么",
    "这个系统能做什么",
    "支持哪些功能",
    "有哪些功能",
    "支持什么功能",
    "怎么使用你",
    "如何使用你",
    "你能做什么",
    "你可以做什么",
    "你会做什么",
    "你能帮我什么",
    "你有什么功能",
    "你有哪些功能",
    "你支持什么",
    "你都能做什么",
    "你是做什么的",
    "管理图谱",
    "图谱管理",
    "管理知识图谱",
    "知识图谱管理",
    "维护图谱",
    "维护知识图谱",
    "图谱维护",
    "图谱运维",
    "管理员如何管理图谱",
    "管理员怎么管理图谱",
    "管理员如何管理知识图谱",
    "管理员怎么管理知识图谱",
    "管理员权限",
    "平台管理",
    "系统管理",
}

_PLATFORM_ADMIN_ROLE_HINTS = {
    "管理员",
    "admin",
}

_PLATFORM_ADMIN_OBJECT_HINTS = {
    "图谱",
    "知识图谱",
    "平台",
    "系统",
    "项目",
}

_PLATFORM_ADMIN_ACTION_HINTS = {
    "管理",
    "维护",
    "运维",
    "配置",
    "权限",
    "审核",
    "监控",
}

_DAILY_LIFE_PATTERNS = {
    "今天天气怎么样",
    "今天天气如何",
    "天气怎么样",
    "天气如何",
    "会下雨吗",
    "冷不冷",
    "热不热",
    "现在几点",
    "几点了",
    "今天星期几",
    "今天周几",
    "明天星期几",
    "明天周几",
    "今天几号",
    "今天日期",
    "现在是什么时间",
}


def _normalize_short_query(text: str) -> str:
    s = str(text or "").strip().lower()
    s = re.sub(r"[\s\.,，。!！?？~～]+", " ", s)
    return s.strip()


def _is_small_talk_query(text: str) -> bool:
    s = _normalize_short_query(text)
    if not s:
        return False
    if s in _SMALL_TALK_EXACT_PATTERNS:
        return True
    # 极短问候或礼貌语，优先视为闲聊而非检索请求。
    if len(s) <= 12 and re.fullmatch(r"(hi|hello|hey|你好|您好|嗨|哈喽|在吗|在不在|谢谢|感谢|再见|拜拜)+", s):
        return True
    return False


def _is_assistant_capability_query(text: str) -> bool:
    s = _normalize_short_query(text)
    if not s:
        return False
    return any(p in s for p in _ASSISTANT_CAPABILITY_PATTERNS)


def _is_platform_help_query(text: str) -> bool:
    s = _normalize_short_query(text)
    if not s:
        return False
    if any(p in s for p in _PLATFORM_HELP_PATTERNS) or _is_assistant_capability_query(s):
        return True
    return (
        any(p in s for p in _PLATFORM_ADMIN_ROLE_HINTS)
        and any(p in s for p in _PLATFORM_ADMIN_OBJECT_HINTS)
        and any(p in s for p in _PLATFORM_ADMIN_ACTION_HINTS)
    )


def _is_daily_life_query(text: str) -> bool:
    s = _normalize_short_query(text)
    if not s:
        return False
    if any(p in s for p in _DAILY_LIFE_PATTERNS):
        return True
    # 极短时间/天气类问句优先按 general 处理，避免误进 KG 或强制联网开放域。
    if len(s) <= 16 and (
        ("天气" in s)
        or ("几点" in s)
        or ("星期" in s)
        or ("周几" in s)
        or ("日期" in s)
    ):
        return True
    return False


def _is_general_chat_query(text: str) -> bool:
    return (
        _is_small_talk_query(text)
        or _is_daily_life_query(text)
    )


def _markdown_presentation_hint() -> str:
    return (
        "请使用清晰、现代的 Markdown 排版提升可读性："
        "开头先给一个简短的 `###` 小标题（不要写‘回答’）；"
        "关键信息可分成 2 到 4 个小节或列表；"
        "对关键词、结论、步骤名、按钮名使用 **加粗**；"
        "正文中必须自然使用 1 到 3 个贴切 emoji，可放在小标题或关键结论前，但不要堆砌；"
        "整体保持专业、克制、像成熟大模型产品的回答风格。"
    )


def build_general_answer_prompt_parts(query: str, detail_level: str, deep_think: bool = False) -> Tuple[str, str, str]:
    """
    返回 (system_prompt, style_hint, extra_guidance)，用于让通用回答在不同轻问句场景下更自然。
    不改变普通 general 问答主行为，只增强明显的闲聊/能力问句/日常短问句。
    """
    q = str(query or "").strip()
    style_hint = (
        "请用自然、直接、像正常助手对话的方式回答，简洁但不生硬。"
        if detail_level == "brief"
        else "请用自然、清晰、完整的方式回答，可适当展开细节，但不要模板化分段。"
    )

    if deep_think:
        system_prompt = (
            "你是专业的金融分析助手。请以已知证据为锚点进行分析，不停留在复述；"
            "允许结合金融常识、行业机制和市场传导路径做合理推演。"
            "回答要自然、专业、连贯，不强制固定报告模板。"
        )
        extra_guidance = (
            "请严格遵守以下原则："
            "1）以图谱检索到的事实作为锚点展开分析，不可脱离事实背景空泛发散；"
            "2）每个核心判断尽量区分为“事实依据”与“推断结论”，但用自然段表达，不要僵硬套模板；"
            "3）当证据不足时不要拒答，给出条件化判断，并明确还需要补充哪些数据才能提高结论可靠性；"
            "4）可给出风险传导链条、行业联动和可能情景，但需说明触发条件与不确定性；"
            "5）不要编造具体数值、公告原文或未提供的实体事实；"
            "6）输出结构必须与普通模式区分：先给出正常回答，再追加一个以“【延展分析】”开头的独立部分，"
            "该部分可更深入展开行业机制、风险传导与情景推演；"
            "7）作为软控制，建议“【延展分析】”不少于2到3段，每段尽量有完整观点与解释。"
            + _markdown_presentation_hint()
        )
    else:
        system_prompt = "你是一个通用智能助手。当前未开启深度思考且未能从知识图谱中检索到直接相关证据。请直接明确告知用户“未在所选图谱中找到与之相关的实体或事实”，再根据自己的常识给予简单、常规的答复，切勿长篇大论。"
        extra_guidance = "简明扼要地回答。不要求涉及深度金融分析或发散预测。" + _markdown_presentation_hint()

    if _is_small_talk_query(q):
        system_prompt = (
            "你是自然、友好的中文助手。面对问候、寒暄、感谢或告别时，"
            "先用一句自然口语化的话回应，再顺势询问对方想聊什么或需要什么帮助。"
        )
        extra_guidance = (
            "如果用户只是打招呼或寒暄，请直接自然回应，不要硬讲知识图谱、平台能力或证据来源。"
            "通常 1 到 2 句即可。"
            + _markdown_presentation_hint()
        )
    elif _is_assistant_capability_query(q):
        system_prompt = (
            "你是 FinAgentGraph 平台内的智能分析助手。"
            "当用户问你是谁、能做什么时，请用第一人称简洁说明身份和能力，语气自然，不要营销化。"
        )
        extra_guidance = (
            "可自然说明你能帮助做知识图谱问答、概念解释、平台操作引导等；"
            "不要编造未实现的功能，不要写成产品宣传稿。"
            + _markdown_presentation_hint()
        )
    elif _is_daily_life_query(q):
        system_prompt = (
            "你是自然、诚实的中文助手。面对天气、时间、日期这类日常短问句时，"
            "优先给出自然回答；如果涉及实时信息且当前无实时工具，请明确说明这一点。"
        )
        extra_guidance = (
            "若问题需要实时数据（如天气、当前精确时间），不要假装联网或掌握实时信息；"
            "可以礼貌说明限制，并给出用户下一步可查看的方式。"
            + _markdown_presentation_hint()
        )

    if _markdown_presentation_hint() not in extra_guidance:
        extra_guidance = f"{extra_guidance}{_markdown_presentation_hint()}"

    return system_prompt, style_hint, extra_guidance

# 开放域事实查询：历史事件、科学知识、地理事实等（需要联网搜索获取准确信息）
_OPEN_DOMAIN_FACT_PATTERNS = {
    "什么时候",
    "何时",
    "哪一年",
    "哪一年开始",
    "发生于",
    "始于",
    "开始于",
    "爆发于",
    "结束于",
    "诞生于",
    "成立于",
    "创建于",
    "发明于",
    "发现于",
    "谁发明了",
    "谁发现了",
    "谁是",
    "谁是第一个",
    "历史上",
    "世界第",
    "全球第",
    "首个",
    "第一次",
    "首次",
    "最早",
    "最晚",
    "最大",
    "最小",
    "最高",
    "最低",
    "最长",
    "最短",
    "源于",
    "起源于",
    "来自",
    "位于",
    "坐落在",
    "地处",
    "面积多少",
    "人口多少",
    "有多少人口",
    " GDP ",
    "国内生产总值",
}
_OPEN_DOMAIN_SUBJECT_HINTS = {
    "战争",
    "冲突",
    "革命",
    "起义",
    "条约",
    "协议",
    "宣言",
    "战役",
    " battle ",
    "发明",
    "发现",
    "定理",
    "定律",
    "公式",
    "元素",
    "国家",
    "城市",
    "首都",
    "地区",
    "省份",
    "山脉",
    "河流",
    "湖泊",
    "海洋",
    "岛屿",
    "星球",
    "行星",
    "恒星",
    "科学家",
    "艺术家",
    "政治家",
    "领导人",
    "总统",
    "首相",
    "主席",
    "总理",
    "国王",
    "皇帝",
}

_NEGATIVE_KG_PATTERNS = {
    "不要用图谱",
    "不用图谱",
    "别用图谱",
    "不要查图谱",
    "不用查图谱",
    "别查图谱",
    "不使用图谱",
    "不走图谱",
    "别走图谱",
    "通用回答",
    "通用知识",
    "常识回答",
    "直接回答",
    "正常回答",
    "直接告诉我",
    "直接说",
    "简单说",
    "简要回答",
    "不用查数据",
    "不要查数据",
    "别查数据",
    "不用检索",
    "不要检索",
    "陪我聊天",
    "聊聊天",
    "闲聊",
    "唠唠",
    "说说闲话",
}

_POSITIVE_KG_PATTERNS = {
    "用图谱查",
    "查一下图谱",
    "看看图谱",
    "从图谱查",
    "在图谱里查",
    "查我的数据",
    "用我的数据",
    "看我的项目",
    "看我所有项目",
    "分析我的数据",
    "从知识图谱",
    "在知识图谱",
    "检索图谱",
    "查询图谱数据",
    "基于知识图谱",
    "结合知识图谱",
    "根据知识图谱",
    "用知识图谱",
    "图谱来回答",
    "按图谱",
    "跨项目检索",
    "跨项目查询",
    "跨项目分析",
}

# 用户明确要求「账号下多项目 / 抽取项目 / 全量图谱证据」→ 优先 kg_query（少走 LLM、少被通用词误判）
_SCOPE_USER_KG_PATTERNS = {
    "所有抽取项目",
    "全部抽取项目",
    "各抽取项目",
    "抽取项目形成",
    "抽取项目对应",
    "抽取项目构建",
    "抽取类项目",
    "在我创建的项目",
    "我创建的全部项目",
    "我创建的所有项目",
    "根据我创建的",
    "根据我账号",
    "账号下全部项目",
    "账号里全部项目",
    "名下全部项目",
    "名下所有项目",
    "整合各项目",
    "汇总各项目",
    "合并各项目",
    "多个项目一起",
    "私有图谱",
    "自建图谱",
    "平台里的图谱",
    "构建好的图谱",
    "已构建的图谱",
}

_KG_BUILD_PATTERNS = {
    "一键构建",
    "master agent",
    "图谱构建",
    "构建图谱",
    "构建知识图谱",
    "知识图谱构建",
    "怎么建知识图谱",
    "如何建知识图谱",
    "怎么构建知识图谱",
    "如何构建知识图谱",
    "平台里建知识图谱",
    "平台里面建知识图谱",
    "在平台里建知识图谱",
    "在平台里面建知识图谱",
    "怎么在平台里建",
    "怎么在平台里面建",
    "如何在平台里建",
    "如何在平台里面建",
    "怎么在平台里构建",
    "如何在平台里构建",
    "怎么生成知识图谱",
    "如何生成知识图谱",
    "生成图谱",
    "抽取节点",
    "抽取关系",
    "增量构建",
    "增量更新",
    "更新图谱",
    "重新构建",
    "重建图谱",
    "langgraph",
    "运行构建",
}

_DATA_IMPORT_PATTERNS = {
    "导入样本",
    "导入数据",
    "导入公告",
    "怎么导入样本",
    "如何导入样本",
    "怎么上传样本",
    "如何上传样本",
    "怎么导入公告",
    "如何导入公告",
    "样本怎么导入",
    "公告怎么导入",
    "怎么添加样本",
    "如何添加样本",
    "怎么同步数据",
    "如何同步数据",
    "上传样本",
    "上传数据",
    "上传文件",
    "添加样本",
    "同步数据",
    "接入数据",
    "批量导入",
}

_PROJECT_MGMT_PATTERNS = {
    "新建项目",
    "创建项目",
    "怎么新建项目",
    "如何新建项目",
    "怎么创建项目",
    "如何创建项目",
    "项目怎么建",
    "怎么建项目",
    "如何建项目",
    "怎么切换项目",
    "如何切换项目",
    "删除项目",
    "复制项目",
    "项目列表",
    "我的项目在哪",
    "重命名项目",
    "切换项目",
    "导出项目",
}

_TOOL_CALL_PATTERNS = {
    "调用工具",
    "调用接口",
    "执行脚本",
    "openapi",
    "api 调用",
}

_KG_BUILD_RESULT_PATTERNS = {
    "怎么看构建结果",
    "如何看构建结果",
    "哪里看构建结果",
    "怎么看图谱结果",
    "如何看图谱结果",
    "构建结果在哪看",
    "图谱结果在哪看",
    "怎么看回放",
    "如何看回放",
    "回放历史",
    "抽取历史",
    "构建历史",
    "结果回放",
    "历史回放",
    "怎么看抽取历史",
    "如何看抽取历史",
    "怎么看构建历史",
    "如何看构建历史",
}

_KG_QUALITY_ANALYSIS_PATTERNS = {
    "质量报告分析",
    "质量报告ai分析",
    "质量构建报告",
    "图谱质量构建报告",
    "图谱质量报告",
    "质量报告怎么看",
    "如何看质量报告",
    "怎么看质量报告",
    "哪里看质量报告",
    "查看质量报告",
    "图谱质量报告怎么看",
    "如何查看图谱质量报告",
    "怎么看图谱质量报告",
    "图谱质量报告在哪里看",
    "图谱质量报告在哪看",
    "质量报告有什么内容",
    "图谱质量报告有什么内容",
    "质量报告包含什么",
    "图谱质量报告包含什么",
    "质量报告包括什么",
    "图谱质量报告包括什么",
    "质量报告里有什么",
    "图谱质量报告里有什么",
    "图谱质量分析",
    "构建效果分析",
    "构建质量分析",
    "kg构建质量分析",
    "冲突分析报告",
    "智能分析报告",
    "quality report analysis",
    "kg quality analysis",
}

_QUALITY_REPORT_CORE_HINTS = {
    "质量",
    "报告",
}

_QUALITY_REPORT_GUIDANCE_HINTS = {
    "查看",
    "怎么看",
    "如何看",
    "在哪看",
    "在哪里看",
    "哪里看",
    "内容",
    "里面",
    "包括",
    "包含",
    "有什么",
    "有哪些",
    "构建",
}


def _match_keywords(text: str, keywords: set, min_match: int = 1) -> bool:
    text_lower = text.lower()
    match_count = sum(1 for kw in keywords if kw.lower() in text_lower)
    return match_count >= min_match


def _match_patterns(text: str, patterns: set) -> bool:
    text_lower = text.lower()
    return any(p.lower() in text_lower for p in patterns)


def is_kg_quality_report_analysis_query(text: str) -> bool:
    return _match_patterns(str(text or ""), _KG_QUALITY_ANALYSIS_PATTERNS)


def _is_kg_quality_report_guidance_query(text: str) -> bool:
    s = str(text or "").strip().lower()
    if not s:
        return False
    if _match_patterns(s, _KG_QUALITY_ANALYSIS_PATTERNS):
        return True
    return all(x in s for x in _QUALITY_REPORT_CORE_HINTS) and any(
        x in s for x in _QUALITY_REPORT_GUIDANCE_HINTS
    )


def _cache_intent(key: str, intent: str) -> None:
    cache_set(_INTENT_CACHE_NS, key, intent, _INTENT_CACHE_TTL_SECONDS)


def _parse_llm_intent_token(intent_part: str) -> str:
    s = (intent_part or "").strip().lower()
    compact = s.replace("_", "").replace(" ", "")
    if "kgquery" in compact or "kg_query" in s:
        return INTENT_KG_QUERY
    if "platformhelp" in compact or "platform_help" in s:
        return INTENT_PLATFORM_HELP
    if "kgbuild" in compact or "kg_build" in s:
        return INTENT_KG_BUILD
    if "dataimport" in compact or "data_import" in s:
        return INTENT_DATA_IMPORT
    if "projectmgmt" in compact or "project_mgmt" in s:
        return INTENT_PROJECT_MGMT
    if "toolcall" in compact or "tool_call" in s:
        return INTENT_TOOL_CALL
    if "general" in s:
        return INTENT_GENERAL
    if re.search(r"\bkg\b", s) and "build" not in s:
        return INTENT_KG_QUERY
    return INTENT_GENERAL


def classify_query_intent(
    query,
    call_chat_completion_fn,
    conversation_history=None,
    use_cache: bool = True,
    return_confidence: bool = False,
):
    """
    细粒度意图：
    - kg_query：需检索用户图谱证据
    - general：通用知识 / 闲聊
    - platform_help：平台定位、能力说明、入门与总体使用引导
    - kg_build / data_import / project_mgmt / tool_call：平台操作引导（走合成路径，不直接查 Neo4j）
    """
    q = (query or "").strip()
    if not q:
        return (INTENT_GENERAL, 1.0) if return_confidence else INTENT_GENERAL

    hist = (conversation_history or "").strip()
    combined_for_rule = f"{hist}\n{q}" if hist else q

    if _is_platform_help_query(q):
        if use_cache:
            _cache_intent(_make_intent_cache_key(q, hist), INTENT_PLATFORM_HELP)
        return (INTENT_PLATFORM_HELP, 0.97) if return_confidence else INTENT_PLATFORM_HELP

    if _is_general_chat_query(q):
        if use_cache:
            _cache_intent(_make_intent_cache_key(q, hist), INTENT_GENERAL)
        return (INTENT_GENERAL, 0.98) if return_confidence else INTENT_GENERAL

    # 短句阳性 + 上文里已出现「用图谱」等（仅查 query 会漏跟踪问法）
    if _match_patterns(combined_for_rule, _POSITIVE_KG_PATTERNS):
        if use_cache:
            _cache_intent(_make_intent_cache_key(q, hist), INTENT_KG_QUERY)
        return (INTENT_KG_QUERY, 0.95) if return_confidence else INTENT_KG_QUERY

    if _match_patterns(q, _NEGATIVE_KG_PATTERNS):
        if use_cache:
            _cache_intent(_make_intent_cache_key(q, hist), INTENT_GENERAL)
        return (INTENT_GENERAL, 0.95) if return_confidence else INTENT_GENERAL

    # 显式要求调用接口/脚本/工具链时，优先视为 tool_call，避免被导入/构建字样覆盖。
    if _match_patterns(q, _TOOL_CALL_PATTERNS):
        if use_cache:
            _cache_intent(_make_intent_cache_key(q, hist), INTENT_TOOL_CALL)
        return (INTENT_TOOL_CALL, 0.9) if return_confidence else INTENT_TOOL_CALL

    if _match_patterns(q, _KG_BUILD_PATTERNS):
        if use_cache:
            _cache_intent(_make_intent_cache_key(q, hist), INTENT_KG_BUILD)
        return (INTENT_KG_BUILD, 0.88) if return_confidence else INTENT_KG_BUILD

    if _is_kg_quality_report_guidance_query(q):
        if use_cache:
            _cache_intent(_make_intent_cache_key(q, hist), INTENT_KG_BUILD)
        return (INTENT_KG_BUILD, 0.93) if return_confidence else INTENT_KG_BUILD

    if _match_patterns(q, _DATA_IMPORT_PATTERNS):
        if use_cache:
            _cache_intent(_make_intent_cache_key(q, hist), INTENT_DATA_IMPORT)
        return (INTENT_DATA_IMPORT, 0.88) if return_confidence else INTENT_DATA_IMPORT

    if _match_patterns(q, _PROJECT_MGMT_PATTERNS):
        if use_cache:
            _cache_intent(_make_intent_cache_key(q, hist), INTENT_PROJECT_MGMT)
        return (INTENT_PROJECT_MGMT, 0.88) if return_confidence else INTENT_PROJECT_MGMT

    # 必须在 _GENERAL_KEYWORDS 之前：否则「介绍一下…根据我全部抽取项目…」会先落 general
    if _match_patterns(combined_for_rule, _SCOPE_USER_KG_PATTERNS):
        if use_cache:
            _cache_intent(_make_intent_cache_key(q, hist), INTENT_KG_QUERY)
        return (INTENT_KG_QUERY, 0.92) if return_confidence else INTENT_KG_QUERY

    # 开放域事实查询：含时间/地点/人物疑问 + 不含图谱关键词 → 强制联网搜索获取准确信息
    if (
        _match_patterns(q, _OPEN_DOMAIN_FACT_PATTERNS)
        or _match_keywords(q, _OPEN_DOMAIN_SUBJECT_HINTS, min_match=1)
    ) and not _match_keywords(combined_for_rule, _KG_KEYWORDS, min_match=1):
        if use_cache:
            _cache_intent(_make_intent_cache_key(q, hist), INTENT_OPEN_DOMAIN)
        return (INTENT_OPEN_DOMAIN, 0.88) if return_confidence else INTENT_OPEN_DOMAIN

    if _match_keywords(q, _GENERAL_KEYWORDS, min_match=1):
        if not _match_keywords(combined_for_rule, _KG_KEYWORDS, min_match=1):
            if use_cache:
                _cache_intent(_make_intent_cache_key(q, hist), INTENT_GENERAL)
            return (INTENT_GENERAL, 0.85) if return_confidence else INTENT_GENERAL

    if _match_keywords(combined_for_rule, _KG_KEYWORDS, min_match=1):
        if use_cache:
            _cache_intent(_make_intent_cache_key(q, hist), INTENT_KG_QUERY)
        return (INTENT_KG_QUERY, 0.75) if return_confidence else INTENT_KG_QUERY

    cache_key = _make_intent_cache_key(q, hist)
    if use_cache:
        cached = cache_get(_INTENT_CACHE_NS, cache_key)
        if cached:
            return (cached, 0.9) if return_confidence else cached

    ctx_block = f"对话上文摘要（可省略）：\n{hist[:3500]}\n\n" if hist else ""

    prompt = f'''请判断用户「当前问题」属于哪一类意图。先分析，后给出结论。

可选意图（必须择一）：
- kg_query：需要检索用户私有知识图谱中的节点/关系/证据才能回答
- general：通用知识、常识、闲聊、与平台数据无关的概念解释
- platform_help：平台是什么、能做什么、怎么开始使用、总体流程与能力引导
- kg_build：一键构建、增量更新、节点/关系抽取、图谱生成或重建等平台构建能力
- data_import：导入/上传样本、公告、文件或批量数据接入
- project_mgmt：创建/删除/列表/切换/导出等项目管理操作
- tool_call：明确希望调用外部接口、脚本或开发者向工具链

判断步骤：
1. 是否在询问平台定位、能力说明、入门方式或总体使用流程？若是优先判为 platform_help。
2. 否则是否明确要操作平台功能（构建、导入、项目管理）？
3. 否则是否需要查用户图谱证据回答问题？（含：跨多个/全部抽取项目、账号下已有项目图谱、整合各项目数据等，一律算 kg_query）
4. 否则是否通用知识或闲聊？
5. 有指代词时请结合上文。

示例：
Q: "把我刚上传的公告跑一键构建" -> kg_build
Q: "股东有哪些关联风险" -> kg_query
Q: "请根据我账号里全部抽取项目对应的知识图谱分析某公司风险" -> kg_query
Q: "在我创建的所有项目图谱里检索关联交易" -> kg_query
Q: "什么是知识图谱" -> general
Q: "这个平台能做什么，应该怎么开始用？" -> platform_help
Q: "作为管理员我如何管理图谱？" -> platform_help
Q: "新建一个叫测试的项目" -> project_mgmt

请严格按一行输出：
意图: <kg_query|general|platform_help|kg_build|data_import|project_mgmt|tool_call> | 置信度: <0.0-1.0> | 理由: <一句话>

{ctx_block}用户当前问题：{q}

分析后输出：'''

    try:
        raw = (
            call_chat_completion_fn(
                messages=[
                    {
                        "role": "system",
                        "content": "你是意图分类专家。仅输出一行：意图: ... | 置信度: ... | 理由: ...",
                    },
                    {"role": "user", "content": prompt},
                ],
                model_name="deepseek-chat",
                temperature=0,
            )
            .strip()
            .lower()
        )

        intent = INTENT_GENERAL
        confidence = 0.7

        if "意图:" in raw:
            intent_part = raw.split("意图:")[1].split("|")[0].strip()
            intent = _parse_llm_intent_token(intent_part)
            if "置信度:" in raw:
                try:
                    conf_part = raw.split("置信度:")[1].split("|")[0].strip()
                    confidence = float(conf_part)
                except (ValueError, IndexError):
                    confidence = 0.72 if intent == INTENT_KG_QUERY else 0.78
        else:
            intent = _parse_llm_intent_token(raw)
            confidence = 0.72

        if use_cache:
            cache_set(_INTENT_CACHE_NS, cache_key, intent, _INTENT_CACHE_TTL_SECONDS)

        return (intent, confidence) if return_confidence else intent

    except Exception:
        return (INTENT_GENERAL, 0.5) if return_confidence else INTENT_GENERAL


def clear_intent_cache():
    cache_clear_namespace(_INTENT_CACHE_NS)


def get_intent_cache_stats() -> Dict:
    base = cache_stats()
    return {
        **base,
        "intent_ttl_seconds": _INTENT_CACHE_TTL_SECONDS,
        "intent_namespace": _INTENT_CACHE_NS,
    }


def _truncate_turn_text(s, max_len=2400):
    t = str(s or "").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def platform_guidance_system_prompt(fine_intent: str) -> str:
    """平台引导路径的系统提示（与 tool_registry 轻量对齐，避免虚构具体 UI 文案）。"""
    try:
        from agents.tool_registry import tool_specs_as_prompt_block
    except ImportError:
        catalog = ""
    else:
        catalog = tool_specs_as_prompt_block(max_tools=12)

    focus = {
        INTENT_PLATFORM_HELP: "侧重说明：平台定位、核心能力、适合处理的问题类型，以及用户通常从项目创建、数据导入、图谱构建开始上手。",
        INTENT_KG_BUILD: "侧重说明：在项目内发起一键构建/增量更新、观察阶段进度与断点恢复等。",
        INTENT_DATA_IMPORT: "侧重说明：样本/公告导入、与项目绑定的数据准备流程。",
        INTENT_PROJECT_MGMT: "侧重说明：创建、切换、管理知识图谱项目。",
        INTENT_TOOL_CALL: "侧重说明：平台 API/工具能力与使用前提（鉴权、项目归属），不要编造不存在的服务器地址。",
    }.get(fine_intent, "综合说明用户应使用的平台能力路径。")

    cat_block = f"\n可供引用能力名（勿杜撰细节）：\n{catalog}\n" if catalog else ""

    return (
        "你是 FinKG 知识图谱平台的中文助手。"
        + focus
        + cat_block
        + "回答须自然、可执行；若不确知界面细节，请用「通常在项目/构建/数据」等描述，避免虚构按钮名称。"
        + _markdown_presentation_hint()
    )


def _build_platform_guidance_extra_hint(query: str, fine_intent: str) -> str:
    q = str(query or "").strip()
    if fine_intent == INTENT_PLATFORM_HELP:
        if any(x in q for x in ("你是谁", "你能", "你可以", "功能", "支持什么", "做什么")):
            return (
                "请优先回答平台/助手的定位与能力边界：自然说明能帮助做哪些事，适合回答哪些平台相关问题，"
                "不要写成营销文案，也不要编造未实现功能。"
            )
        if any(x in q for x in ("怎么用", "如何用", "如何使用", "怎么开始", "从哪开始", "入门", "上手")):
            return (
                "请优先给出平台入门路径：建议用自然语言说明 3 到 5 步操作顺序。"
                "优先覆盖：创建或进入项目/准备并导入样本/发起图谱构建/查看结果与后续问答分析。"
                "若界面按钮名称不确定，可写‘通常在项目页、数据页或构建页中’。"
            )
        return "请优先说明平台是什么、能做什么，以及用户通常如何开始使用。"
    if fine_intent == INTENT_KG_BUILD:
        if _is_kg_quality_report_guidance_query(q):
            return (
                "请优先回答图谱质量报告的查看位置和报告内容。"
                "可覆盖：通常在哪里进入质量报告、报告会展示哪些维度、用户如何根据报告继续优化图谱构建。"
                "若界面名称不确定，可用‘通常在构建结果页、分析页或质量报告页中’表达。"
            )
        if any(x in q for x in _KG_BUILD_RESULT_PATTERNS):
            return (
                "请优先回答‘怎么看结果/历史/回放’：自然说明通常可在图谱预览、构建结果页、抽取历史或回放页查看。"
                "可覆盖：查看当前图谱结果、按 run 查看历史、回看旧版本、对比多轮构建结果。"
                "若界面名称不确定，可用‘通常在结果页或历史页中’表达。"
            )
        if any(x in q for x in ("怎么", "如何", "怎样", "步骤", "流程", "入口")):
            return (
                "请优先直接回答用户‘在平台里怎么做’：建议用自然语言给出 3 到 5 步的操作顺序。"
                "优先覆盖：进入项目/确认样本/发起一键构建或增量构建/查看结果与回放。"
                "若界面按钮名称不确定，可写‘通常在项目页或构建页中’。"
            )
        return (
            "请围绕平台中的知识图谱构建能力回答，优先解释构建入口、构建方式、运行后能看到什么结果。"
        )
    if fine_intent == INTENT_DATA_IMPORT:
        if any(x in q for x in ("怎么", "如何", "怎样", "步骤", "流程", "入口")):
            return (
                "请优先直接回答‘怎么导入样本/公告’：建议给出 3 到 5 步操作顺序。"
                "优先覆盖：进入项目或样本页/选择上传或同步方式/确认样本进入项目/为后续构建做准备。"
                "若界面按钮名称不确定，可写‘通常在项目页、样本页或导入入口中’。"
            )
        return "请优先说明数据准备、样本导入、与项目绑定这三件事。"
    if fine_intent == INTENT_PROJECT_MGMT:
        if any(x in q for x in ("新建", "创建", "怎么", "如何", "步骤", "入口")):
            return (
                "请优先回答‘怎么新建项目/管理项目’：建议用自然语言说明 3 到 4 步。"
                "优先覆盖：进入项目管理区域/新建项目并填写基本信息/进入项目后继续导入样本或发起构建。"
                "若界面名称不确定，可写‘通常在项目管理或项目列表页中’。"
            )
        return "请优先说明项目创建、切换、管理的常见操作路径。"
    return "请给出可执行、贴近平台使用场景的说明。"


def generate_platform_guidance_answer(
    query,
    fine_intent: str,
    deep_think,
    detail_level,
    parse_bool_fn,
    call_chat_completion_fn,
    prior_messages=None,
):
    """细粒度「平台类」意图：不走图谱检索，生成操作引导说明。"""
    model_name = "deepseek-reasoner" if parse_bool_fn(deep_think, False) else "deepseek-chat"
    style_hint = (
        "回答尽量短，步骤用自然段或少量分点即可。"
        if detail_level == "brief"
        else "回答可稍长，条理清楚，但不要套固定八股模板。"
    )
    extra_hint = _build_platform_guidance_extra_hint(query, fine_intent)
    prompt = (
        f"{style_hint}\n"
        f"{extra_hint}\n"
        f"当前识别意图标签：{fine_intent}\n"
        "请结合上文理解指代，只针对「当前问题」作答。\n"
        f"用户问题：{query}"
    )
    messages = [
        {"role": "system", "content": platform_guidance_system_prompt(fine_intent)},
    ]
    if prior_messages:
        for m in prior_messages:
            role = m.get("role") if isinstance(m, dict) else None
            if role not in ("user", "assistant"):
                continue
            content = _truncate_turn_text(m.get("content") if isinstance(m, dict) else None)
            if content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": prompt})
    try:
        return call_chat_completion_fn(
            messages=messages,
            model_name=model_name,
            temperature=0.25,
        )
    except Exception:
        return "平台引导暂时不可用，请稍后重试或直接在界面中使用「一键构建 / 导入数据 / 项目管理」相关菜单。"


def generate_general_answer(
    query,
    deep_think,
    detail_level,
    parse_bool_fn,
    call_chat_completion_fn,
    prior_messages=None,
):
    model_name = "deepseek-reasoner" if parse_bool_fn(deep_think, False) else "deepseek-chat"
    system_prompt, style_hint, extra_guidance = build_general_answer_prompt_parts(query, detail_level, deep_think=parse_bool_fn(deep_think, False))
    prompt = (
        f"{style_hint}\n"
        f"{extra_guidance}\n"
        "请结合上文理解指代，只针对「当前问题」作答。\n"
        f"当前问题：{query}"
    )
    messages = [{"role": "system", "content": system_prompt}]
    if prior_messages:
        for m in prior_messages:
            role = m.get("role") if isinstance(m, dict) else None
            if role not in ("user", "assistant"):
                continue
            content = _truncate_turn_text(m.get("content") if isinstance(m, dict) else None)
            if content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": prompt})
    try:
        return call_chat_completion_fn(
            messages=messages,
            model_name=model_name,
            temperature=0.3,
        )
    except Exception:
        return "通用问答暂时不可用，请稍后重试。"
