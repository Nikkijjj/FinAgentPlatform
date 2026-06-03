import { genRequestHeaders, requestAPI } from '@/api/response';

export interface ChatReplyParams {
  session_id: string;
  user_input: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  deep_think?: boolean;
  reasoning?: string;
  evidence?: any[];
  web_search_meta?: Record<string, unknown>;
  web_search_attempted?: boolean;
  quality_hints?: unknown;
  kg_lookup_status?: string;
  intent_coarse?: string;
  intent?: string;
}

export interface ChatHistoryListResponse {
  [session_id: string]: ChatMessage[];
}

export interface ChatHistoryParams {
  session_id: string;
}

export interface ChatHistoryListParams {
  user_id?: string | number;
  username?: string;
  uid?: string | number;
  limit?: number;
}

export interface KgQaParams {
  user_id: string | number;
  /** 与历史会话接口一致，便于后端校验 session 归属 */
  username?: string;
  uid?: string | number;
  is_admin?: boolean;
  query: string;
  session_id?: string;
  /** 默认 true：从 MySQL 拉取本会话历史并注入模型上下文 */
  use_session_history?: boolean;
  save_history?: boolean;
  intent_mode?: 'auto' | 'kg' | 'general';
  allow_general_fallback?: boolean;
  deep_think?: boolean;
  detail_level?: 'brief' | 'detailed';
  top_k_per_project?: number;
  /**
   * 受限联网检索：不传 project_id 时，后端在**当前用户全部可见项目**上分别做样本锚定检索后合并去重。
   * 若传 project_id，则仅在该项目上网搜（调试用或缩小范围）。
   */
  enable_web_search?: boolean;
  project_id?: string;
  /** 不传时：开启 enable_web_search 默认 always（每次都尝试）；关闭则为 when_weak_evidence */
  web_search_mode?: 'always' | 'when_weak_evidence' | 'never';
  /** 本地开发调试开关：返回 retrieval_debug（生产默认不要开启） */
  debug_retrieval?: boolean;
}

export interface DeleteChatSessionParams {
  session_id: string;
  user_id: string | number;
  username?: string;
  uid?: string | number;
}

export interface RenameChatSessionParams {
  session_id: string;
  title: string;
  user_id?: string | number;
  username?: string;
  uid?: string | number;
}

/**
 * @description 获取聊天回复
 */
export async function getChatReply(token: string, params: ChatReplyParams) {
  return await requestAPI('/api/chat/get/reply', 'post', genRequestHeaders(token), params);
}

/**
 * @description 获取历史对话列表
 */
export async function getChatHistoryList(token: string, params: ChatHistoryListParams) {
  return await requestAPI(
    '/old-api/chat/get/historyList',
    'post',
    genRequestHeaders(token),
    params
  );
}

/**
 * @description 获取指定会话的历史记录
 */
export async function getChatHistory(token: string, params: ChatHistoryParams) {
  return await requestAPI('/old-api/chat/get/history', 'post', genRequestHeaders(token), params);
}

export async function deleteChatSession(token: string, params: DeleteChatSessionParams) {
  return await requestAPI('/old-api/chat/delete/session', 'post', genRequestHeaders(token), params);
}

export async function renameChatSession(token: string, params: RenameChatSessionParams) {
  return await requestAPI('/old-api/chat/rename/session', 'post', genRequestHeaders(token), params);
}

export async function getMarketReply(token: string, params) {
  return await requestAPI('/api/market/get/report', 'post', genRequestHeaders(token), params);
}

export async function getFundamentalReply(token: string, params) {
  return await requestAPI('/api/fundamentals/get/report', 'post', genRequestHeaders(token), params);
}

export async function getWorkReply(token: string, params) {
  return await requestAPI('/api/work/get/report', 'post', genRequestHeaders(token), params);
}

export async function getKgQaReply(token: string, params: KgQaParams) {
  return await requestAPI('/old-api/kg-qa', 'post', genRequestHeaders(token), params);
}

/**
 * 流式问答 NDJSON：多行 {"type":"delta","text":"..."}，深度思考另有 {"type":"reasoning_delta","text":"..."}，
 * 最后一行 {"type":"done","code":0,"data":{...}}。
 * onDelta 收到正文增量；onReasoningDelta 收到思考链增量（可选）。
 */
export async function getKgQaReplyStream(
  token: string,
  params: KgQaParams,
  onDelta: (chunk: string) => void,
  onReasoningDelta?: (chunk: string) => void
): Promise<{ code: number; data?: any; msg?: string }> {
  const resp = await fetch('/old-api/chat/kg-qa-stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...genRequestHeaders(token),
    },
    body: JSON.stringify(params),
  });
  if (!resp.ok) {
    return { code: 1, msg: `请求失败 (${resp.status})` };
  }
  const reader = resp.body?.getReader();
  if (!reader) {
    return { code: 1, msg: '无法读取响应流' };
  }
  const decoder = new TextDecoder();
  let buffer = '';
  let finalData: any = null;
  let errPayload: { code: number; msg?: string; data?: any } | null = null;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      const t = line.trim();
      if (!t) continue;
      try {
        const j = JSON.parse(t) as {
          type?: string;
          text?: string;
          code?: number;
          data?: any;
          msg?: string;
        };
        if (j.type === 'delta' && j.text) {
          onDelta(j.text);
        }
        if (j.type === 'reasoning_delta' && j.text && onReasoningDelta) {
          onReasoningDelta(j.text);
        }
        if (j.type === 'done' && j.code === 0) {
          finalData = j.data;
        }
        if (j.type === 'error') {
          errPayload = { code: j.code ?? 1, msg: j.msg, data: j.data };
        }
      } catch {
        /* 单行非 JSON 忽略 */
      }
    }
  }
  if (buffer.trim()) {
    try {
      const j = JSON.parse(buffer.trim()) as {
        type?: string;
        text?: string;
        code?: number;
        data?: any;
        msg?: string;
      };
      if (j.type === 'delta' && j.text) {
        onDelta(j.text);
      }
      if (j.type === 'reasoning_delta' && j.text && onReasoningDelta) {
        onReasoningDelta(j.text);
      }
      if (j.type === 'done' && j.code === 0) {
        finalData = j.data;
      }
      if (j.type === 'error') {
        errPayload = { code: j.code ?? 1, msg: j.msg, data: j.data };
      }
    } catch {
      /* ignore */
    }
  }
  if (errPayload) {
    return errPayload;
  }
  if (finalData !== null) {
    return { code: 0, data: finalData };
  }
  return { code: 1, msg: '未收到完整响应' };
}
