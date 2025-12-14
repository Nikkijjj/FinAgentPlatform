<script setup lang="ts">
  import { onMounted, ref, nextTick } from 'vue';
  import {
    cleanMarkdown,
    fetchMessage_Events,
    fetchMessage_Industry,
    fetchMessage_Mood, fetchMessage_Stock,
    StockNews,
  } from '@/api/message/message';
  import { getChatReply } from '@/api/chat/chat';
  import { useRouter } from 'vue-router';
  import { useUserStore } from '@/store/modules/user';
  import { NModal, useMessage } from 'naive-ui';
  import { marked } from 'marked';
  import { NIcon } from 'naive-ui';

  const router = useRouter();
  const userStore = useUserStore();
  const message = useMessage();

  marked.setOptions({
    breaks: true,
    gfm: true,
  });

  const pagination = { pageSize: 20 };

  const columns_industry = [
    {
      title: '排名',
      key: '排名',
    },
    {
      title: '上涨家数',
      key: '上涨家数',
    },
    {
      title: '下跌家数',
      key: '下跌家数',
    },
    {
      title: '总市值',
      key: '总市值',
    },
    {
      title: '换手率',
      key: '换手率',
    },
    {
      title: '最新价',
      key: '最新价',
    },
    {
      title: '板块代码',
      key: '板块代码',
    },
    {
      title: '板块名称',
      key: '板块名称',
    },
    {
      title: '涨跌幅',
      key: '涨跌幅',
    },
    {
      title: '涨跌额',
      key: '涨跌额',
    },
    {
      title: '领涨股票',
      key: '领涨股票',
    },
    {
      title: '领涨股票-涨跌幅',
      key: '领涨股票-涨跌幅',
    },
  ];

  const columns_mood = [
    {
      title: '关注',
      key: '关注',
    },
    {
      title: '最新价',
      key: '最新价',
    },
    {
      title: '股票代码',
      key: '股票代码',
    },
    {
      title: '股票简称',
      key: '股票简称',
    },
  ];

  const originalMessages_events = ref<[]>([]);
  const messages_events = ref<[]>([]);

  const originalMessages_industry = ref<[]>([]);
  const messages_industry = ref<[]>([]);

  const originalMessages_stock = ref<[]>([]);
  const messages_stock = ref<[]>([]);

  const originalMessages_mood = ref<[]>([]);
  const messages_mood = ref<[]>([]);

  const showModal = ref(false);
  const expandedMessageId = ref<number | null>(null);

  const userInput = ref('');
  const chatMessages = ref<Array<{ role: 'user' | 'assistant'; content: string }>>([]);
  const isLoadingChat = ref(false);
  const sessionId = ref<string>('');

  // 使用与参考代码相同的头像
  const aiAvatar = ref<string>(
    'https://tse3.mm.bing.net/th/id/OIP.BaX2gxcUogd-XwXjJGUb7AHaHa?w=996&h=996&rs=1&pid=ImgDetMain&o=7&rm=3'
  );
  const aiAvatarFallback = ref<string>(
    'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgdmlld0JveD0iMCAwIDEwMCAxMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIiByeD0iNTAiIGZpbGw9IiM0NTc2RjEiLz4KPGNpcmNsZSBjeD0iNTAiIGN5PSIzNSIgcj0iMTUiIGZpbGw9IndoaXRlIi8+CjxyZWN0IHg9IjMwIiB5PSI1NSIgd2lkdGg9IjQwIiBoZWlnaHQ9IjMwIiByeD0iOCIgZmlsbD0id2hpdGUiLz4KPGNpcmNsZSBjeD0iNDAiIGN5PSIzNSIgcj0iMyIgZmlsbD0iIzMzMzMzMyIvPgo8Y2lyY2xlIGN4PSI2MCIgY3k9IjM1IiByPSIzIiBmaWxsPSIjMzMzMzMzIi8+Cjwvc3ZnPgo='
  );

  const userAvatar = ref<string>(
    'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop&crop=face&q=80'
  );
  const userAvatarFallback = ref<string>(
    'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgdmlld0JveD0iMCAwIDEwMCAxMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIiByeD0iNTAiIGZpbGw9IiNENUVEQ0VFIi8+CjxjaXJjbGUgY3g9IjUwIiBjeT0iMzUiIHI9IjE1IiBmaWxsPSIjNkM3NzhBIi8+CjxwYXRoIGQ9Ik0yMCA3MEMyMCA1NSA0MCA0MCA1MCA0MEM2MCA0MCA4MCA1NSA4MCA3MEg4MkM4MiA1NCA2MiAzOCA1MCAzOEMzOCAzOCAxOCA1NCAxOCA3MEgyMFoiIGZpbGw9IiM2Qzc3OEEiLz4KPC9zdmc+'
  );

  // 生成会话ID
  const generateSessionId = () => {
    return `session_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
  };

  const renderedMarkdown = (text: string) => {
    return marked(text);
  };

  // 提取Markdown大纲
  const extractOutline = (markdown: string) => {
    const lines = markdown.split('\n');
    const outline: Array<{ level: number; text: string; id: string }> = [];

    lines.forEach((line, index) => {
      const match = line.match(/^(#{1,6})\s+(.+)$/);
      if (match) {
        const level = match[1].length;
        let text = match[2].trim();
        // 去掉中英文冒号
        text = text.replace(/[:：]$/, '');
        const id = `heading-${index}`;
        outline.push({ level, text, id });
      }
    });

    return outline;
  };

  // 为Markdown内容添加ID锚点
  const addHeadingIds = (markdown: string) => {
    const lines = markdown.split('\n');
    return lines
      .map((line, index) => {
        const match = line.match(/^(#{1,6})\s+(.+)$/);
        if (match) {
          return `${match[1]} <span id="heading-${index}">${match[2]}</span>`;
        }
        return line;
      })
      .join('\n');
  };

  // 展开/折叠消息
  const toggleExpand = (i) => {
    if (expandedMessageId.value === i) {
      // 折叠
      expandedMessageId.value = null;
      showModal.value = false;
    } else {
      // 记录当前滚动位置，用于折叠时返回
      const previousScrollY = window.scrollY;

      // 展开
      expandedMessageId.value = i;
      showModal.value = true;
      sessionId.value = generateSessionId();
      chatMessages.value = [];

      // 等待 DOM 更新后滚动到时间线项
      nextTick(() => {
        // 给一点延迟确保DOM完全渲染（展开动画完成）
        setTimeout(() => {
          // 找到对应的时间线项
          const timelineItem = document.querySelector(`[data-message-id="${i}"]`);
          if (timelineItem) {
            // 使用最简单直接的方法
            timelineItem.scrollIntoView({
              behavior: 'smooth',
              block: 'start', // 确保在视口顶部
              inline: 'nearest',
            });

            // 添加一些视觉反馈
            timelineItem.classList.add('timeline-item-highlight');
            setTimeout(() => {
              timelineItem.classList.remove('timeline-item-highlight');
            }, 1000);
          }
        }, 100); // 100ms延迟确保展开动画完成
      });
    }
  };

  // 滚动到指定标题
  const scrollToHeading = (id: string) => {
    const element = document.getElementById(id);
    const contentArea = document.querySelector('.content-area'); // 获取内容容器

    if (element && contentArea) {
      // 计算相对位置
      const elementRect = element.getBoundingClientRect();
      const contentRect = contentArea.getBoundingClientRect();

      // 计算相对偏移量
      const relativeTop = elementRect.top - contentRect.top + contentArea.scrollTop;

      // 使用内容容器的scrollTop进行滚动
      contentArea.scrollTop = relativeTop - 20; // 减去一点边距
    }
  };

  // 发送聊天消息
  const sendChatMessage = async (item: StockNews) => {
    if (!userInput.value.trim() || isLoadingChat.value) return;

    const userMessage = userInput.value.trim();
    chatMessages.value.push({ role: 'user', content: userMessage });
    userInput.value = '';
    isLoadingChat.value = true;

    try {
      const response = await getChatReply(userStore.getToken, {
        session_id: item.session_id,
        user_input: userMessage,
      });
      console.log('Chat response:', response);

      if (response.code == 0) {
        chatMessages.value.push({
          role: 'assistant',
          content: response.data || '抱歉，我没有理解您的问题。',
        });
      } else {
        message.error(response.msg || '获取回复失败');
        chatMessages.value.push({
          role: 'assistant',
          content: '抱歉，服务暂时不可用，请稍后再试。',
        });
      }
    } catch (error) {
      console.error('Chat error:', error);
      message.error('发送消息失败');
      chatMessages.value.push({
        role: 'assistant',
        content: '抱歉，发生了错误，请稍后再试。',
      });
    } finally {
      isLoadingChat.value = false;
      // 滚动到消息底部
      nextTick(() => {
        const messagesContainer = document.querySelector(`.chat-messages-${index}`);
        if (messagesContainer) {
          messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
      });
    }
  };

  const renderChatMarkdown = (text: string) => {
    // 可以添加一些预处理，比如确保换行符正确处理
    const processedText = text.replace(/\\n/g, '\n');
    const rawHtml = marked(processedText);
    return rawHtml;
  };

  onMounted(async () => {
    const eventsResponse = await fetchMessage_Events();
    const industryResponse = await fetchMessage_Industry();
    const moodResponse = await fetchMessage_Mood();
    const stockResponse = await fetchMessage_Stock();
    if (
      eventsResponse.code != 0 ||
      industryResponse.code != 0 ||
      moodResponse.code != 0 ||
      stockResponse != 0
    ) {
      message.error(eventsResponse.msg);
      return;
    }
    // events
    const data_events = eventsResponse.data.messages;
    originalMessages_events.value = [...data_events];
    messages_events.value = [...originalMessages_events.value];

    // industry
    const data_industry = industryResponse.data;
    originalMessages_industry.value = [...data_industry];
    messages_industry.value = [...originalMessages_industry.value];

    // stock
    const data_stock = stockResponse.data;
    originalMessages_stock.value = [...data_stock];
    messages_stock.value = [...originalMessages_stock.value];

    // mood
    const data_mood = moodResponse.data;
    originalMessages_mood.value = [...data_mood];
    messages_mood.value = [...originalMessages_mood.value];
  });
</script>

<template>
  <n-card class="large-card">
    <div class="container">
      <n-tabs
        type="line"
        animated
        size="large"
        justify-content="space-between"
        tab-style="background-color: ghostwhite; padding: 20px 80px 20px 80px;"
      >
        <n-tab-pane name="macro" tab="宏观">
          <n-timeline size="large">
            <n-timeline-item
              v-for="(m, index) in messages_events"
              :key="index"
              :time="m.时间"
              class="report-header"
              :data-message-id="index"
            >
              <!-- 自定义标题：显示标签和已读/未读状态 -->
              <template #header>
                <div class="title-row">
                  <span class="title-label"></span>
                </div>
              </template>

              <n-card
                class="report-card"
                :class="{ expanded: expandedMessageId === index }"
                content-class="report-card"
                header-class="report-header"
              >
                <!-- 折叠状态：显示简略内容 -->
                <div v-if="expandedMessageId !== index" @click="toggleExpand(index)">
                  <n-ellipsis class="ellipsis-text report-content" :line-clamp="3">
                    {{ cleanMarkdown(m.内容) }}
                    <template #tooltip>点击展开</template>
                  </n-ellipsis>
                </div>
              </n-card>
            </n-timeline-item>
          </n-timeline>
        </n-tab-pane>
        <n-tab-pane name="industry" tab="行业">
          <n-timeline size="large">
            <n-data-table
              :columns="columns_industry"
              :data="messages_industry"
              :pagination="pagination"
            />
          </n-timeline>
        </n-tab-pane>
        <n-tab-pane name="stock" tab="个股">
          <n-timeline size="large">
            <n-timeline-item
              v-for="(m, index) in messages_stock"
              :key="index"
              :time="m.发布时间"
              class="report-header"
              :data-message-id="index"
              :title="m.标题"
            >
              <!-- 自定义标题：显示标签和已读/未读状态 -->
              <template #header>
                <div class="title-row">
                  <span class="title-label"></span>
                </div>
              </template>

              <n-card
                class="report-card"
                :class="{ expanded: expandedMessageId === index }"
                content-class="report-card"
                header-class="report-header"
              >
                <!-- 折叠状态：显示简略内容 -->
                <div v-if="expandedMessageId !== index" @click="toggleExpand(index)">
                  <n-ellipsis class="ellipsis-text report-content" :line-clamp="3">
                    {{ cleanMarkdown(m.内容) }}
                    <template #tooltip>点击展开</template>
                  </n-ellipsis>
                </div>

                <!-- 展开状态：显示完整内容 + 大纲 + 聊天框 -->
                <div v-else :id="`expanded-${index}`" class="expanded-content">
                  <!-- 折叠按钮 -->
                  <div class="collapse-btn-wrapper">
                    <n-button text @click="toggleExpand(index)" class="collapse-btn">
                      <template #icon>
                        <n-icon>
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            viewBox="0 0 24 24"
                            fill="currentColor"
                          >
                            <path d="M7 10l5 5 5-5z" />
                          </svg>
                        </n-icon>
                      </template>
                      收起
                    </n-button>
                  </div>

                  <div class="expanded-layout">
                    <!-- 左侧：Markdown内容 -->
                    <div class="content-area">
                      <div
                        class="markdown-content"
                        v-html="renderedMarkdown(addHeadingIds(m.内容))"
                      ></div>
                    </div>
                  </div>
                </div>
              </n-card>
            </n-timeline-item>
          </n-timeline>
        </n-tab-pane>
        <n-tab-pane name="mood" tab="情绪">
          <n-data-table :columns="columns_mood" :data="messages_mood" :pagination="pagination" />
        </n-tab-pane>
      </n-tabs>
    </div>
  </n-card>
</template>

<style scoped lang="less">
  // 全局变量
  :root {
    --primary: #165dff;
    --secondary: #ff7d00;
    --text-main: #333333;
    --text-light: #666666;
    --bg-card: #ffffff;
    --bg-page: #f5f7fa;
    --border: #e5e7eb;
    --shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    --shadow-hover: 0 8px 16px rgba(0, 0, 0, 0.1);
    --transition: all 0.3s ease;
  }

  // 主容器
  .large-card {
    display: flex;
    position: relative;
    height: 100%;
    flex-direction: column;
    border-radius: 10px;
    overflow: hidden;
  }

  .container {
    display: flex;
    flex-direction: row;
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px;
  }

  // 导航栏
  .nav {
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: center;
    gap: 10px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-card);
    padding: 12px 24px;
  }

  .nav-item {
    width: 400px;
    height: 60px;
    padding: 8px 16px;
    border-radius: 4px;
    border: 2px solid #e5e7eb;
    cursor: pointer;
    transition: var(--transition);
    font-weight: 500;
  }

  .nav-item:disabled {
    color: #165dff;
    border: 3px solid #165dff;
  }

  // 标题行样式
  .title-row {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .title-label {
    font-weight: 600;
    font-size: 16px;
  }

  .read-status {
    font-size: 14px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 4px;

    &.unread {
      color: #ff3b30;
      background-color: rgba(255, 59, 48, 0.1);
    }

    &.read {
      color: #165dff;
      background-color: rgba(22, 93, 255, 0.1);
    }
  }

  // 报告卡片
  .report-card {
    background-color: #ffffff;
    border-radius: 8px;
    border: 1px solid #e5e7eb;
    padding: 24px;
    margin-bottom: 24px;
    box-shadow: var(--shadow);
    transition: var(--transition);

    &.read {
      background-color: ghostwhite;
    }

    &.expanded {
      max-width: 100%;
    }
  }

  .ellipsis-text {
    max-width: 100%;
    cursor: pointer;
    pointer-events: all;
  }

  // 展开内容布局
  .expanded-content {
    width: 100%;
  }

  .collapse-btn-wrapper {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 16px;
  }

  .collapse-btn {
    color: #165dff;
    font-size: 14px;
  }

  .expanded-layout {
    display: flex;
    gap: 24px;
    min-height: 600px;
  }

  // 内容区域
  .content-area {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    background: #fafafa;
    border-radius: 8px;
    max-height: 800px;
  }

  // 侧边栏
  .sidebar {
    width: 350px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  // 大纲样式
  .outline-section {
    background: white;
    border-radius: 8px;
    padding: 16px;
    border: 1px solid #e5e7eb;
    max-height: 350px;
    display: flex;
    flex-direction: column;
  }

  .section-title {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 12px;
    color: #333;
    text-align: center;
  }

  .outline-list {
    overflow-y: auto;
    flex: 1;
  }

  .outline-item {
    padding: 8px 12px;
    margin-bottom: 4px;
    cursor: pointer;
    border-radius: 4px;
    transition: all 0.2s;
    font-size: 14px;

    &:hover {
      background-color: #f5f7fa;
    }

    &.outline-level-1 {
      font-weight: 600;
      color: #333;
    }

    &.outline-level-2 {
      padding-left: 24px;
      color: #666;
    }

    &.outline-level-3 {
      padding-left: 36px;
      color: #888;
      font-size: 13px;
    }

    &.outline-level-4,
    &.outline-level-5,
    &.outline-level-6 {
      padding-left: 48px;
      color: #999;
      font-size: 12px;
    }
  }

  // 聊天框样式
  .chat-section {
    flex: 1;
    background: white;
    border-radius: 8px;
    padding: 16px;
    border: 1px solid #e5e7eb;
    display: flex;
    flex-direction: column;
    min-height: 400px;
    max-height: 500px; // 添加最大高度限制
  }

  .chat-messages {
    flex: 1;
    overflow-y: auto; // 确保有滚动条
    margin-bottom: 12px;
    padding: 12px;
    background: #f5f7fa;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    min-height: 200px; // 最小高度
    max-height: 300px; // 添加最大高度，确保滚动条出现
  }

  .chat-message {
    display: flex;
    gap: 12px;

    &.user {
      flex-direction: row-reverse;

      .message-bubble {
        background-color: #165dff;
        color: white;
        border-radius: 12px 12px 0 12px;
      }
    }

    &.assistant {
      .message-bubble {
        background-color: white;
        color: #333;
        border: 1px solid #e5e7eb;
        border-radius: 12px 12px 12px 0;
      }
    }

    .message-avatar {
      flex-shrink: 0;
      :deep(.n-avatar) {
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
        border: 2px solid rgba(255, 255, 255, 0.9);
      }
    }

    .message-content {
      display: flex;
      align-items: flex-start;
      max-width: 80%;
    }

    .message-bubble {
      padding: 10px 14px;
      border-radius: 12px;
      font-size: 14px;
      line-height: 1.5;
      word-wrap: break-word;
      width: 100%;

      &.loading {
        display: flex;
        align-items: center;
        min-height: 40px;
        padding: 8px 14px;
      }
    }
  }

  // 聊天框Markdown样式
  .chat-markdown {
    font-size: 14px;
    line-height: 1.5;

    :deep(h1),
    :deep(h2),
    :deep(h3) {
      margin: 0.8em 0 0.4em 0;
      font-weight: 600;
      color: #333;
      line-height: 1.3;
    }

    :deep(h1) {
      font-size: 1.2em;
    }

    :deep(h2) {
      font-size: 1.1em;
    }

    :deep(h3) {
      font-size: 1em;
    }

    :deep(p) {
      margin: 0.5em 0;
    }

    :deep(ul),
    :deep(ol) {
      margin: 0.5em 0;
      padding-left: 1.5em;
    }

    :deep(li) {
      margin: 0.25em 0;
    }

    :deep(code) {
      background: #f5f7fa;
      padding: 0.2em 0.4em;
      border-radius: 3px;
      font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
      font-size: 0.9em;
    }

    :deep(pre) {
      background: #f8f9fa;
      border: 1px solid #e5e7eb;
      border-radius: 6px;
      padding: 0.8em;
      overflow-x: auto;
      margin: 0.8em 0;

      code {
        background: none;
        padding: 0;
        border-radius: 0;
      }
    }

    :deep(blockquote) {
      border-left: 3px solid #165dff;
      padding-left: 1em;
      margin: 0.8em 0;
      color: #666;
    }

    :deep(table) {
      border-collapse: collapse;
      margin: 0.8em 0;
      width: 100%;
      font-size: 0.9em;

      th,
      td {
        border: 1px solid #e5e7eb;
        padding: 0.4em 0.8em;
      }

      th {
        background: #f8f9fa;
        font-weight: 600;
      }
    }

    :deep(a) {
      color: #165dff;
      text-decoration: none;

      &:hover {
        text-decoration: underline;
      }
    }

    :deep(hr) {
      border: none;
      border-top: 1px solid #e5e7eb;
      margin: 1em 0;
    }
  }

  // 用户消息保持纯文本样式
  .chat-message.user .message-bubble .plain-text {
    white-space: pre-wrap;
    word-wrap: break-word;
  }

  // 输入区域
  .chat-input-area {
    border-top: 1px solid #f0f0f0;
    background: #fff;
    flex-shrink: 0;
    padding: 16px 0 0 0;
  }

  .input-container {
    display: flex;
    gap: 8px;
    align-items: flex-end;

    .message-input {
      flex: 1;

      :deep(.n-input) {
        min-height: 40px;
      }

      :deep(.n-input__textarea-el) {
        resize: none;
        min-height: 40px;
        line-height: 1.4;
        padding: 10px 12px;
        font-size: 14px;
        text-align: left;
      }

      :deep(.n-input__textarea-el::placeholder) {
        color: #c2c2c2;
        text-align: left;
      }

      :deep(.n-input--focus .n-input__textarea-el) {
        padding-left: 12px;
      }
    }

    .send-button {
      background: #4c44d7;
      border: none;
      flex-shrink: 0;
      height: 40px;
      width: 40px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;

      :deep(.n-button__icon) {
        display: flex;
        align-items: center;
        justify-content: center;
      }

      &:hover {
        background: #665cf2;
      }

      &:disabled {
        background: #d0d0d0;
        cursor: not-allowed;
      }
    }
  }

  /* 添加高亮动画 */
  @keyframes highlight {
    0% {
      background-color: transparent;
    }
    50% {
      background-color: rgba(22, 93, 255, 0.1);
    }
    100% {
      background-color: transparent;
    }
  }

  /* 确保时间轴布局合理 */
  .n-timeline {
    position: relative;
  }

  /* 展开时的时间线项有更好的视觉区分 */
  .n-timeline-item:has(.expanded) {
    .report-card.expanded {
      border-color: #165dff;
      box-shadow: 0 0 0 2px rgba(22, 93, 255, 0.1), 0 4px 6px rgba(0, 0, 0, 0.05);
    }
  }

  // 主内容Markdown样式
  .markdown-content {
    line-height: 1.8;
    color: #333;

    :deep(h1),
    :deep(h2),
    :deep(h3),
    :deep(h4),
    :deep(h5),
    :deep(h6) {
      margin-top: 24px;
      margin-bottom: 16px;
      font-weight: 600;
      line-height: 1.4;
      scroll-margin-top: 20px;
    }

    :deep(h1) {
      font-size: 28px;
      border-bottom: 2px solid #e5e7eb;
      padding-bottom: 8px;
    }

    :deep(h2) {
      font-size: 24px;
      border-bottom: 1px solid #e5e7eb;
      padding-bottom: 6px;
    }

    :deep(h3) {
      font-size: 20px;
    }

    :deep(p) {
      margin-bottom: 16px;
    }

    :deep(ul),
    :deep(ol) {
      margin-bottom: 16px;
      padding-left: 24px;
    }

    :deep(li) {
      margin-bottom: 8px;
    }

    :deep(code) {
      background-color: #f5f7fa;
      padding: 2px 6px;
      border-radius: 4px;
      font-family: 'Monaco', 'Consolas', monospace;
      font-size: 13px;
    }

    :deep(pre) {
      background-color: #2d2d2d;
      color: #f8f8f2;
      padding: 16px;
      border-radius: 8px;
      overflow-x: auto;
      margin-bottom: 16px;

      code {
        background: none;
        padding: 0;
        color: inherit;
      }
    }

    :deep(blockquote) {
      border-left: 4px solid #165dff;
      padding-left: 16px;
      margin: 16px 0;
      color: #666;
    }

    :deep(table) {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 16px;
    }

    :deep(th),
    :deep(td) {
      border: 1px solid #e5e7eb;
      padding: 8px 12px;
      text-align: left;
    }

    :deep(th) {
      background-color: #f5f7fa;
      font-weight: 600;
    }
  }

  // 响应式适配
  @media (max-width: 768px) {
    .nav {
      flex-direction: column;
      padding: 12px;
    }

    .container {
      padding: 16px;
    }

    .report-card {
      padding: 16px;
    }

    .expanded-layout {
      flex-direction: column;
      gap: 16px;
    }

    .sidebar {
      width: 100%;
    }

    .content-area {
      max-height: 400px;
    }

    .chat-section {
      max-height: 450px;
    }

    .chat-messages {
      max-height: 250px;
    }

    .nav-item {
      width: 100%;
      height: 50px;
    }
  }

  /* 固定对话框样式 */
  .fixed-dialog {
    .n-dialog {
      height: 600px;
      max-height: 80vh;

      .n-dialog__content {
        display: flex;
        flex-direction: column;
        height: 100%;

        .n-dialog__action {
          margin-top: auto;
          flex-shrink: 0;
        }
      }
    }
  }

  .dialog-content {
    flex: 1;
    overflow-y: auto;
    padding-right: 8px; /* 为滚动条留出空间 */
    height: 500px;

    /* 自定义滚动条样式 */
    &::-webkit-scrollbar {
      width: 6px;
    }

    &::-webkit-scrollbar-track {
      background: #f1f1f1;
      border-radius: 3px;
    }

    &::-webkit-scrollbar-thumb {
      background: #c1c1c1;
      border-radius: 3px;

      &:hover {
        background: #a8a8a8;
      }
    }
  }
</style>
