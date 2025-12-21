import { genRequestHeaders, requestAPI } from '@/api/response';

export interface ChatReplyParams {
  session_id: string;
  user_input: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatHistoryListResponse {
  [session_id: string]: ChatMessage[];
}

export interface ChatHistoryParams {
  session_id: string;
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
export async function getChatHistoryList(token: string) {
  return await requestAPI('/api/chat/get/historyList', 'get', genRequestHeaders(token), null);
}

/**
 * @description 获取指定会话的历史记录
 */
export async function getChatHistory(token: string, params: ChatHistoryParams) {
  return await requestAPI('/api/chat/get/history', 'post', genRequestHeaders(token), params);
}
