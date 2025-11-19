import request from '@/utils/axios/index';
import { badResponse } from '@/api/response';

//单条数据
export interface StockNews {
  _id: string; // id
  user_id: string; // 用户id
  trade_date: string; // 股票分析时间
  company_of_interest: string; // 股票代码
  report: string; // 报告
  label: string; // 标签
  is_read: string; // 是否已读
  date: string; // 落库时间
}

interface FetchNewsParams {
  page: number; //当前页
  size: number; //数量
}

/**
 *  获取所有消息列表
 */
export async function fetchNews(token: string, params: FetchNewsParams) {
  try {
    const result = await request.post('/api/message/list', params, {
      headers: {
        Authorization: token,
      },
    });
    return result.data ?? badResponse;
  } catch (error) {
    console.log(error);
    return badResponse;
  }
}

interface UpdateReadStatusParams {
  id: string;
}

/**
 * 更新消息已读状态
 */
export async function updateReadStatus(token: string, params: UpdateReadStatusParams) {
  try {
    const result = await request.post('/api/message/update_read', params, {
      headers: {
        Authorization: token,
      },
    });
    return result.data ?? badResponse;
  } catch (error) {
    console.log(error);
    return badResponse;
  }
}

interface FetchMessagesByDayParams {
  day: string;
}

export async function fetchMessageByDay(token: string, params: FetchMessagesByDayParams) {
  try {
    console.log('fetchMessage:\n' + 'token=' + token + '\n' + 'date=' + params.day);
    const result = await request.post('/api/message/by_day', params, {
      headers: {
        Authorization: token,
      },
    });
    return result.data ?? badResponse;
  } catch (error) {
    console.log(error);
    return badResponse;
  }
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
