<script setup lang="ts">
  import { onMounted, ref, nextTick } from 'vue';
  import {
    cleanMarkdown,
    fetchMessageByDay,
    StockNews,
    updateReadStatus,
  } from '@/api/message/message';
  import { getChatReply } from '@/api/chat/chat';
  import { useRouter } from 'vue-router';
  import { useUserStore } from '@/store/modules/user';
  import { getLocalDate } from '@/api/time';
  import { useMessage } from 'naive-ui';
  import { marked } from 'marked';
  import { NAvatar, NIcon } from 'naive-ui';

  const router = useRouter();
  const userStore = useUserStore();
  const message = useMessage();

  marked.setOptions({
    breaks: true,
    gfm: true,
  });

  const originalMessages = ref<StockNews[]>([]);
  const messages = ref<StockNews[]>([]);
  const expandedMessageId = ref<string | null>(null);
  const userInput = ref('');
  const chatMessages = ref<Array<{ role: 'user' | 'assistant'; content: string }>>([]);
  const isLoadingChat = ref(false);
  const sessionId = ref<string>('');

  // 使用与参考代码相同的头像
  const aiAvatar = ref<string>('https://tse3.mm.bing.net/th/id/OIP.BaX2gxcUogd-XwXjJGUb7AHaHa?w=996&h=996&rs=1&pid=ImgDetMain&o=7&rm=3');
  const aiAvatarFallback = ref<string>('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgdmlld0JveD0iMCAwIDEwMCAxMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIiByeD0iNTAiIGZpbGw9IiM0NTc2RjEiLz4KPGNpcmNsZSBjeD0iNTAiIGN5PSIzNSIgcj0iMTUiIGZpbGw9IndoaXRlIi8+CjxyZWN0IHg9IjMwIiB5PSI1NSIgd2lkdGg9IjQwIiBoZWlnaHQ9IjMwIiByeD0iOCIgZmlsbD0id2hpdGUiLz4KPGNpcmNsZSBjeD0iNDAiIGN5PSIzNSIgcj0iMyIgZmlsbD0iIzMzMzMzMyIvPgo8Y2lyY2xlIGN4PSI2MCIgY3k9IjM1IiByPSIzIiBmaWxsPSIjMzMzMzMzIi8+Cjwvc3ZnPgo=');
  
  const userAvatar = ref<string>('https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop&crop=face&q=80');
  const userAvatarFallback = ref<string>('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgdmlld0JveD0iMCAwIDEwMCAxMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIiByeD0iNTAiIGZpbGw9IiNENUVEQ0VFIi8+CjxjaXJjbGUgY3g9IjUwIiBjeT0iMzUiIHI9IjE1IiBmaWxsPSIjNkM3NzhBIi8+CjxwYXRoIGQ9Ik0yMCA3MEMyMCA1NSA0MCA0MCA1MCA0MEM2MCA0MCA4MCA1NSA4MCA3MEg4MkM4MiA1NCA2MiAzOCA1MCAzOEMzOCAzOCAxOCA1NCAxOCA3MEgyMFoiIGZpbGw9IiM2Qzc3OEEiLz4KPC9zdmc+');

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
        const text = match[2];
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

  const toHistory = () => {
    router.push('/message_push/history');
  };

  const updateRead = (item: StockNews) => {
    if (item.is_read !== 'yes') {
      item.is_read = 'yes';
      const params = {
        id: item._id,
      };
      updateReadStatus(userStore.getToken, params);
    }
  };

  // 展开/折叠消息
  const toggleExpand = (item: StockNews) => {
    if (expandedMessageId.value === item._id) {
      // 折叠
      expandedMessageId.value = null;
    } else {
      // 展开
      expandedMessageId.value = item._id;
      sessionId.value = generateSessionId();
      chatMessages.value = [];
      updateRead(item);

      // 等待 DOM 更新后滚动到内容区域
      nextTick(() => {
        const expandedElement = document.getElementById(`expanded-${item._id}`);
        if (expandedElement) {
          expandedElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    }
  };

  // 滚动到指定标题
  const scrollToHeading = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
        const messagesContainer = document.querySelector('.chat-messages');
        if (messagesContainer) {
          messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
      });
    }
  };

  onMounted(async () => {
    const day = getLocalDate();
    const params = {
      day: day,
    };
    const messageResponse = await fetchMessageByDay(userStore.getToken, params);
    if (messageResponse.code == 0) {
      const current_data = messageResponse.data.messages;
      originalMessages.value = [...current_data];
      messages.value = [...originalMessages.value];
    } else message.error(messageResponse.msg);
  });
</script>

<template>
  <n-card class="large-card">
    <div class="nav">
      <n-button disabled class="nav-item">今日消息</n-button>
      <n-button class="nav-item" @click="toHistory">历史消息</n-button>
    </div>
    <div class="container">
      <n-timeline size="large">
        <n-timeline-item
          v-for="(m, index) in messages"
          :key="index"
          :time="m.trade_date"
          class="report-header"
        >
          <!-- 自定义标题：显示标签和已读/未读状态 -->
          <template #header>
            <div class="title-row">
              <span class="title-label">{{ m.label }}</span>
              <span v-if="m.is_read !== 'yes'" class="read-status unread">[未读]</span>
              <span v-else class="read-status read">[已读]</span>
            </div>
          </template>

          <template v-if="m.is_read != 'yes'" #icon>
            <n-icon>
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#FF3B30">
                <circle cx="12" cy="12" r="6" />
              </svg>
            </n-icon>
          </template>

          <n-card
            class="report-card"
            :class="{ read: m.is_read == 'yes', expanded: expandedMessageId === m._id }"
            content-class="report-card"
            header-class="report-header"
          >
            <!-- 折叠状态：显示简略内容 -->
            <div v-if="expandedMessageId !== m._id" @click="toggleExpand(m)">
              <n-ellipsis class="ellipsis-text report-content" :line-clamp="3">
                {{ cleanMarkdown(m.report) }}
                <template #tooltip>点击展开</template>
              </n-ellipsis>
            </div>

            <!-- 展开状态：显示完整内容 + 大纲 + 聊天框 -->
            <div v-else :id="`expanded-${m._id}`" class="expanded-content">
              <!-- 折叠按钮 -->
              <div class="collapse-btn-wrapper">
                <n-button text @click="toggleExpand(m)" class="collapse-btn">
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
                    v-html="renderedMarkdown(addHeadingIds(m.report))"
                  ></div>
                </div>

                <!-- 右侧：大纲和聊天框 -->
                <div class="sidebar">
                  <!-- 大纲 -->
                  <div class="outline-section">
                    <h3 class="section-title">大纲</h3>
                    <div class="outline-list">
                      <div
                        v-for="item in extractOutline(m.report)"
                        :key="item.id"
                        :class="['outline-item', `outline-level-${item.level}`]"
                        @click="scrollToHeading(item.id)"
                      >
                        {{ item.text }}
                      </div>
                    </div>
                  </div>

                  <!-- 聊天对话框 -->
                  <div class="chat-section">
                    <h3 class="section-title">对话框</h3>
                    <div class="chat-messages">
                      <div
                        v-for="(msg, idx) in chatMessages"
                        :key="idx"
                        :class="['chat-message', msg.role]"
                      >
                        <div class="message-avatar">
                          <n-avatar
                            round
                            size="small"
                            :src="msg.role === 'assistant' ? aiAvatar : userAvatar"
                            :fallback-src="msg.role === 'assistant' ? aiAvatarFallback : userAvatarFallback"
                          />
                        </div>
                        <div class="message-content">
                          <div class="message-bubble">
                            {{ msg.content }}
                          </div>
                        </div>
                      </div>
                      <div v-if="isLoadingChat" class="chat-message assistant">
                        <div class="message-avatar">
                          <n-avatar
                            round
                            size="small"
                            :src="aiAvatar"
                            :fallback-src="aiAvatarFallback"
                          />
                        </div>
                        <div class="message-content">
                          <div class="message-bubble loading">
                            <n-spin size="small" />
                            <span style="margin-left: 8px">思考中...</span>
                          </div>
                        </div>
                      </div>
                    </div>
                    <!-- 修改后的输入区域 -->
                    <!-- 修改后的输入区域 -->
                    <div class="chat-input-area">
                      <div class="input-container">
                        <n-input
                          v-model:value="userInput"
                          type="textarea"
                          placeholder="    输入您的问题..."
                          :autosize="{ minRows: 1, maxRows: 3 }"
                          @keydown.enter.prevent="sendChatMessage(m)"
                          class="message-input"
                          :disabled="isLoadingChat"
                        />
                        <n-button
                          type="primary"
                          class="send-button"
                          :disabled="!userInput.trim() || isLoadingChat"
                          @click="sendChatMessage(m)"
                          :loading="isLoadingChat"
                        >
                          <template #icon>
                            <n-icon>
                              <svg viewBox="0 0 24 24" fill="currentColor">
                                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                              </svg>
                            </n-icon>
                          </template>
                        </n-button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </n-card>
        </n-timeline-item>
      </n-timeline>
    </div>
  </n-card>
</template>

<style scoped lang="less">
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

  .ellipsis-text {
    max-width: 100%;
    cursor: pointer;
    pointer-events: all;
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

  // 展开状态的卡片
  .report-card.expanded {
    max-width: 100%;
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

  .content-area {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    background: #fafafa;
    border-radius: 8px;
    max-height: 800px;
  }

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
  }

  .chat-messages {
    flex: 1;
    overflow-y: auto;
    margin-bottom: 12px;
    padding: 12px;
    background: #f5f7fa;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    gap: 16px;
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

      &.loading {
        display: flex;
        align-items: center;
      }
    }
  }

  // 修改后的输入区域样式
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

      // 确保输入框高度与按钮对齐
      :deep(.n-input) {
        min-height: 40px;
      }

      :deep(.n-input__textarea-el) {
        resize: none;
        min-height: 40px;
        line-height: 1.4;
        // 修改内边距，让光标紧靠左侧
        padding: 10px 12px 10px 12px; // 确保左右内边距一致
        font-size: 14px;
        // 确保文本和光标从左侧开始
        text-align: left;
      }
      
      // 修复placeholder位置
      :deep(.n-input__textarea-el::placeholder) {
        color: #c2c2c2;
        text-align: left;
      }
      
      // 确保输入框聚焦时光标位置正确
      :deep(.n-input--focus .n-input__textarea-el) {
        padding-left: 12px; // 确保聚焦时内边距不变
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

      // 确保按钮内的图标垂直居中
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

  // 确保加载状态也对齐
  .chat-message .message-bubble.loading {
    display: flex;
    align-items: center;
    min-height: 40px;
    padding: 8px 14px;
  }

  // Markdown 内容样式
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

  // ai优化代码
  /* 全局变量与重置 */
  :root {
    --primary: #165dff; /* 主色：金融蓝，体现专业感 */
    --secondary: #ff7d00; /* 辅助色：橙色，突出关键数据 */
    --text-main: #333333; /* 正文文字色 */
    --text-light: #666666; /* 次要文字色 */
    --bg-card: #ffffff; /* 卡片背景 */
    --bg-page: #f5f7fa; /* 页面背景 */
    --border: #e5e7eb; /* 边框色 */
    --shadow: 0 4px 6px rgba(0, 0, 0, 0.05); /* 卡片阴影 */
    --shadow-hover: 0 8px 16px rgba(0, 0, 0, 0.1); /*  hover阴影 */
    --transition: all 0.3s ease; /* 通用过渡动画 */
  }

  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  }

  body {
    background-color: var(--bg-page);
    color: var(--text-main);
    line-height: 1.6;
  }

  /* 导航栏样式 */
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

  /* 报告卡片样式 */
  .report-card {
    background-color: #ffffff;
    border-radius: 8px;
    border: 1px solid #e5e7eb;
    padding: 24px;
    margin-bottom: 24px;
    box-shadow: var(--shadow);
    transition: var(--transition);
  }

  .read {
    background-color: ghostwhite;
  }

  .report-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }

  .report-content {
    font-size: 14px;
    color: var(--text-main);
  }

  /* 响应式适配 */
  @media (max-width: 768px) {
    .nav {
      flex-direction: column;
      padding: 12px;
    }

    .report-card {
      padding: 16px;
    }

    .report-header {
      flex-direction: column;
      align-items: flex-start;
      gap: 8px;
    }

    .expanded-layout {
      flex-direction: column;
    }

    .sidebar {
      width: 100%;
    }
  }
</style>
