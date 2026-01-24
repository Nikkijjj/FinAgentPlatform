import { genRequestHeaders, requestAPI } from '@/api/response';

//单条数据
export interface StockNews {
  _id: string; // id
  user_id: string; // 用户id
  trade_date: string; // 股票分析时间
  company_of_interest: string; // 股票代码
  report: string; // 报告
  label: string; // 标签
  is_read: string; // 是否已读
  session_id: string; //会话ID
  date: string; // 落库时间
}

interface FetchNewsParams {
  page: number; //当前页
  size: number; //数量
  stock_code?: string;
  event_type?: string;
  report_type?: string;
  start_date?: string;
  end_date?: string;
}

/**
 *@description 获取所有消息列表
 */
export async function fetchNews(token: string, params: FetchNewsParams) {
  return await requestAPI('/api/message/list', 'post', genRequestHeaders(token), params);
}

interface UpdateReadStatusParams {
  id: string;
}

/**
 *@description 更新消息已读状态
 */
export async function updateReadStatus(token: string, params: UpdateReadStatusParams) {
  return await requestAPI('/api/message/update_read', 'post', genRequestHeaders(token), params);
}

interface FetchMessagesByDayParams {
  day: string;
}

/**
 *@description 获取今日消息
 */
export async function fetchMessageByDay(token: string, params: FetchMessagesByDayParams) {
  return await requestAPI('/api/message/by_day', 'post', genRequestHeaders(token), params);
}

/**
 *@description 获取宏观消息列表
 */
export async function fetchMessage_Events() {
  return await requestAPI('/api/message/macro', 'get');
}

/**
 *@description 获取行业消息列表
 */
export async function fetchMessage_Industry() {
  return await requestAPI('/api/message/industry', 'get');
}

export async function fetchMessage_Stock() {
  return await requestAPI('/api/message/company', 'get');
}

/**
 *@description 获取情绪消息列表
 */
export async function fetchMessage_Mood() {
  return await requestAPI('/api/message/trading', 'get');
}

// 新的统一查询接口
export interface FetchAllEventsParams {
  page: number; // 当前页
  size: number; // 每页数量
  stock_code?: string; // 相关个股/标的 模糊匹配 (symbol字段)
  keyword?: string; // 关键字 全局模糊搜索
  start_time?: string; // 事件开始时间 yyyy-MM-dd 或 yyyy-MM-dd HH:mm:ss
  end_time?: string; // 事件结束时间 yyyy-MM-dd 或 yyyy-MM-dd HH:mm:ss
  event_type?: string; // 事件类型精准筛选 (如macro，不传查所有类型)
  sort_field?: string; // 排序字段(任意列名)，默认:event_time
  sort_order?: 1 | -1; // 排序方式 1=正序  -1=倒序，默认:-1(最新在前)
}

/**
 *@description 查询全部事件类型的事件列表
 */
export async function fetchAllEvents(params: FetchAllEventsParams) {
  return await requestAPI('/api/message/list_all', 'post', {}, params);
}

export const cleanMarkdown = (content: string) => {
  if (!content) return '';

  return (
    content
      // 移除标题标记
      .replace(/^#{1,6}\s+/gm, '')
      // 移除粗体标记
      .replace(/\**(.*?)\*\*/g, '$1')
      .replace(/(.*?) /g, '$1')
      // 移除斜体标记
      .replace(/\*(.*?)\*/g, '$1')
      .replace(/(.*?) /g, '$1')
      // 移除代码标记
      .replace(/(.*?)`/g, '$1')
      // 移除链接标记
      .replace(/\[(.*?)]\(.*?\)/g, '$1')
      // 移除图片标记
      .replace(/!\[(.*?)]\(.*?\)/g, '$1')
      // 移除列表标记
      .replace(/^\s*[-*+]\s+/gm, '')
      .replace(/^\s*\d+\.\s+/gm, '')
      // 移除引用标记
      .replace(/^>\s+/gm, '')
      // 移除水平线
      .replace(/^[-* ]{3,}\s*$/gm, '')
      // 替换换行符为空格
      .replace(/\n/g, '')
      // 去除多余空格
      .replace(/\s+/g, '')
      .trim()
  );
};

export const truncateContent = (content: string, maxLength = 30) => {
  if (!content) return '';
  const cleanedContent = cleanMarkdown(content);
  if (cleanedContent.length <= maxLength) return cleanedContent;
  return cleanedContent.substring(0, maxLength) + '...';
};
