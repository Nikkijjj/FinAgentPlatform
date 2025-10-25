import request from '@/utils/axios/index';

//单条数据
export interface MessageData {
  company_of_interest: string;
  messages: {
    content: string;
    role: string;
  }[];
  report: string;
  trade_date: string;
  _id: string;
}

//请求响应结果
export interface MessageResponse {
  code: number;
  data: {
    current_data: MessageData[];
    pagination: {
      page: number;
      pages: number;
      size: number;
      total: number;
    };
  };
  msg: string;
}

/**
 *  获取所有消息列表
 *  @returns type:MessageData[]
 */
export const fetchMessages: (time, page_num, page_count) => Promise<MessageResponse> = async (
  time: [],
  page_num: number,
  page_count: number
) => {
  try {
    const result = await request.post('/api/scheduler/list', {
      time: time,
      page_num: page_num,
      page_count: page_count,
    });
    return result.data;
  } catch (error) {
    console.log(error);
  }
};

// 从content中提取标题
const extractTitleFromContent = (content: string): string => {
  try {
    if (!content) return '无标题';

    // 确保content是字符串
    const contentStr = String(content);

    // 按优先级查找标题
    const patterns = [
      /^#\s+(.+?)(?:\n|$)/m, // 行首一级标题 (# 标题)
      /(?:^|\n)#\s+(.+?)(?:\n|$)/, // 任意位置一级标题
      /^##\s+(.+?)(?:\n|$)/m, // 行首二级标题 (## 标题)
      /(?:^|\n)##\s+(.+?)(?:\n|$)/, // 任意位置二级标题
    ];

    for (const pattern of patterns) {
      const match = contentStr.match(pattern);
      if (match && match[1]) {
        const title = match[1].trim();
        // 过滤掉过短的标题
        if (title.length >= 2) {
          return title;
        }
      }
    }

    // 备选方案：使用第一行文本
    const firstLine = contentStr.split('\n').find((line) => line.trim().length > 0);
    if (firstLine) {
      const result = firstLine
        .trim()
        .replace(/^[#\s]*/, '')
        .trim();
      return result || '无标题';
    }

    return '无标题';
  } catch (error) {
    console.error('解析标题时出错:', error);
    return '无标题';
  }
};

// 截断标题
const truncateTitle = (title: string, maxLength = 13): string => {
  try {
    if (!title || title === '无标题') return '无标题';
    const safeTitle = String(title);
    if (safeTitle.length <= maxLength) return safeTitle;
    return safeTitle.substring(0, maxLength) + '...';
  } catch (error) {
    console.error('截断标题时出错:', error);
    return '无标题';
  }
};

const cleanMarkdown = (content: string) => {
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

export const extractTruncatedTitle = (content: string, maxLength = 13) => {
  const title = extractTitleFromContent(content);
  return truncateTitle(title, maxLength);
};
