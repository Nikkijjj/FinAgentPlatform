<template>
  <div class="ai-assistant-container">
    <!-- 对话框区域 -->
    <div class="chat-container">
      <div class="chat-header">
        <div class="chat-title">
          <span>智能分析助手</span>
        </div>
        <div class="chat-actions">
          <n-button quaternary circle @click="createNewChat" title="新建对话">
            <template #icon>
              <n-icon>
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" />
                </svg>
              </n-icon>
            </template>
          </n-button>
          <n-button quaternary circle @click="clearAllMessages" title="清空消息">
            <template #icon>
              <n-icon>
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path
                    d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"
                  />
                </svg>
              </n-icon>
            </template>
          </n-button>
        </div>
      </div>

      <div class="chat-messages" ref="messagesContainer">
        <div v-for="(m, index) in messages" :key="index" class="message" :class="m.type">
          <div class="message-avatar">
            <n-avatar
              round
              size="small"
              :src="m.type === 'ai-message' ? aiAvatar : userAvatar"
              :fallback-src="m.type === 'ai-message' ? aiAvatarFallback : userAvatarFallback"
            />
          </div>
          <div class="message-content">
            <div class="message-text">
              <pre v-if="m.isTemplate">{{ m.content }}</pre>
              <div
                v-else-if="m.type === 'ai-message'"
                v-html="purifyMarkdown(renderMarkdown(m.content))"
                class="markdown-content"
              ></div>
              <span v-else>{{ m.content }}</span>
            </div>
            <div class="message-actions">
              <n-button text size="tiny" @click="deleteMessage(index)" class="delete-btn">
                <template #icon>
                  <n-icon size="14">
                    <svg viewBox="0 0 24 24" fill="currentColor">
                      <path
                        d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"
                      />
                    </svg>
                  </n-icon>
                </template>
              </n-button>
            </div>
          </div>
        </div>

        <!-- 加载状态 -->
        <div v-if="isLoading" class="message ai-message">
          <div class="message-avatar">
            <n-avatar round size="small" :src="aiAvatar" :fallback-src="aiAvatarFallback" />
          </div>
          <div class="message-content">
            <div class="message-text">
              <n-spin size="small" />
              <span style="margin-left: 8px">AI正在思考中...</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 可调整大小的输入框区域 -->
      <div class="chat-input-area">
        <div class="input-container">
          <n-input
            v-model:value="userInput"
            type="textarea"
            placeholder="请选择下方的Agent类型或直接输入您的问题..."
            :autosize="{ minRows: 1 }"
            @keydown.enter.prevent="handleSendMessage"
            class="message-input"
            ref="inputRef"
            :disabled="isLoading"
          />
          <n-button
            type="primary"
            class="send-button"
            :disabled="!userInput || isLoading"
            @click="handleSendMessage"
            :loading="isLoading"
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

    <!-- Agent卡片区域 -->
    <div class="agents-section">
      <div class="agents-grid">
        <n-card
          class="agent-card"
          :class="{ active: activeAgent === 'market' }"
          @click="selectAgent('market')"
        >
          <div class="card-content">
            <div class="card-icon market">
              <n-icon size="32">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <!-- 折线图表 -->
                  <path
                    d="M3 17l5-5 4 4 6-8 4 4"
                    stroke="currentColor"
                    stroke-width="1.5"
                    fill="none"
                  />
                  <!-- 数据点 -->
                  <circle cx="3" cy="17" r="1.5" fill="currentColor" />
                  <circle cx="8" cy="12" r="1.5" fill="currentColor" />
                  <circle cx="12" cy="16" r="1.5" fill="currentColor" />
                  <circle cx="18" cy="8" r="1.5" fill="currentColor" />
                  <circle cx="22" cy="12" r="1.5" fill="currentColor" />
                </svg>
              </n-icon>
            </div>
            <h3 class="card-title">市场分析助手</h3>
          </div>
        </n-card>

        <n-card
          class="agent-card"
          :class="{ active: activeAgent === 'fundamental' }"
          @click="selectAgent('fundamental')"
        >
          <div class="card-content">
            <div class="card-icon fundamental">
              <n-icon size="32">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M14 12h1.5v5H14zm-3 2.5h1.5V17H11zm6-5h1.5v7.5H17z" />
                  <path
                    d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zM6 18H4V6h2v12zm4 0H8V6h2v12zm4 0h-2V6h2v12zm4 0h-2V6h2v12zm4 0h-2V6h2v12z"
                  />
                </svg>
              </n-icon>
            </div>
            <h3 class="card-title">基本面分析助手</h3>
          </div>
        </n-card>

        <n-card
          class="agent-card"
          :class="{ active: activeAgent === 'media' }"
          @click="selectAgent('media')"
        >
          <div class="card-content">
            <div class="card-icon media">
              <n-icon size="32">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path
                    d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-8 12.5v-9l6 4.5-6 4.5z"
                  />
                </svg>
              </n-icon>
            </div>
            <h3 class="card-title">盘中分析助手</h3>
          </div>
        </n-card>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { nextTick, onMounted, ref, watch } from 'vue';
  import { NAvatar, NButton, NCard, NIcon, NInput, NSpin, useMessage } from 'naive-ui';
  import { marked } from 'marked';
  import DOMPurify from 'dompurify';
  import { useRoute, useRouter } from 'vue-router';
  import { useUserStore } from '@/store/modules/user';
  import {
    getChatReply,
    getChatHistory,
    ChatMessage,
    getMarketReply,
    getFundamentalReply,
    getWorkReply,
  } from '@/api/chat/chat';
  import aiAvatarImage from '@/assets/images/AI_asis.jpg';

  const message = useMessage();
  const route = useRoute();
  const router = useRouter();
  const userStore = useUserStore();

  // 响应式数据
  const activeAgent = ref<string>('');
  const userInput = ref<string>('');
  const messages = ref<Array<{ type: string; content: string; isTemplate?: boolean }>>([]);
  const inputHeight = ref<number>(120);
  const isResizing = ref<boolean>(false);
  const messagesContainer = ref<HTMLElement>();
  const inputRef = ref<any>();
  const isLoading = ref<boolean>(false);
  const currentSessionId = ref<string>('');

  // 使用您提供的机器人图片作为AI头像
  // const aiAvatar = ref<string>('https://tse3.mm.bing.net/th/id/OIP.BaX2gxcUogd-XwXjJGUb7AHaHa?w=996&h=996&rs=1&pid=ImgDetMain&o=7&rm=3');
  const aiAvatar = ref<string>(aiAvatarImage);
  const aiAvatarFallback = ref<string>(
    'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgdmlld0JveD0iMCAwIDEwMCAxMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIiByeD0iNTAiIGZpbGw9IiM0NTc2RjEiLz4KPGNpcmNsZSBjeD0iNTAiIGN5PSIzNSIgcj0iMTUiIGZpbGw9IndoaXRlIi8+CjxyZWN0IHg9IjMwIiB5PSI1NSIgd2lkdGg9IjQwIiBoZWlnaHQ9IjMwIiByeD0iOCIgZmlsbD0id2hpdGUiLz4KPGNpcmNsZSBjeD0iNDAiIGN5PSIzNSIgcj0iMyIgZmlsbD0iIzMzMzMzMyIvPgo8Y2lyY2xlIGN4PSI2MCIgY3k9IjM1IiByPSIzIiBmaWxsPSIjMzMzMzMzIi8+Cjwvc3ZnPgo='
  );

  const userAvatar = ref<string>(
    'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop&crop=face&q=80'
  );
  const userAvatarFallback = ref<string>(
    'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgdmlld0JveD0iMCAwIDEwMCAxMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIiByeD0iNTAiIGZpbGw9IiNENUVEQ0VFIi8+CjxjaXJjbGUgY3g9IjUwIiBjeT0iMzUiIHI9IjE1IiBmaWxsPSIjNkM3NzhBIi8+CjxwYXRoIGQ9Ik0yMCA3MEMyMCA1NSA0MCA0MCA1MCA0MEM2MCA0MCA4MCA1NSA4MCA3MEg4MkM4MiA1NCA2MiAzOCA1MCAzOEMzOCAzOCAxOCA1NCAxOCA3MEgyMFoiIGZpbGw9IiM2Qzc3OEEiLz4KPC9zdmc+'
  );

  // Agent提示词模板
  const agentTemplates = {
    market: `请分析以下市场情况并提供投资建议：

【股票代码】: [请在此处填写股票代码，如AAPL、TSLA、00700.HK、000001等 - 必需]
【输入问题】: [请在此处输入您的具体问题或关注点]

请基于以上信息，提供详细的市场分析和投资建议。`,

    fundamental: `请分析以下基本面情况并提供财务分析：

【股票代码】: [请在此处填写股票代码，如AAPL、TSLA、00700.HK、000001等 - 必需]
【输入问题】: [请在此处输入您的具体问题或关注点]

请基于以上信息，提供基本面分析和财务评估。`,

    media: `请协助分析或优化以下盘中分析内容：

【股票代码】: [请在此处填写股票代码，如AAPL、TSLA、00700.HK、000001等 - 必需]
【输入问题】: [请在此处输入您的具体问题或关注点]

请基于以上信息，提供专业、及时、客观的盘中分析。`,
  };

  // 配置marked选项
  marked.setOptions({
    breaks: true,
    gfm: true,
  });

  // Markdown渲染函数
  const renderMarkdown = (content: string) => {
    if (!content) return '';
    return marked(content);
  };

  //渲染markdown
  const purifyMarkdown = (markdown: string): string => {
    return DOMPurify.sanitize(markdown);
  };

  // 生成新的 session_id
  const generateSessionId = (): string => {
    return `session_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
  };

  // 选择Agent
  const selectAgent = (agent: string) => {
    activeAgent.value = agent;
    userInput.value = agentTemplates[agent as keyof typeof agentTemplates];

    message.success(`已切换到${getAgentName(agent)}模式`);

    // 滚动到对话框底部并聚焦输入框
    nextTick(() => {
      scrollToBottom();
      if (inputRef.value) {
        inputRef.value.focus();
      }
    });
  };

  // 获取Agent名称
  const getAgentName = (agent: string): string => {
    const names: Record<string, string> = {
      market: 'Market Agent',
      fundamental: 'Fundamental Agent',
      media: 'Media Agent',
    };
    return names[agent] || 'Unknown Agent';
  };

  // 发送消息
  const handleSendMessage = async () => {
    if (!userInput.value.trim() || isLoading.value) return;

    // 如果没有当前 session，创建一个新的
    if (!currentSessionId.value) {
      currentSessionId.value = generateSessionId();
    }

    // 添加用户消息
    messages.value.push({
      type: 'user-message',
      content: userInput.value,
    });

    const currentInput = userInput.value;
    userInput.value = '';
    isLoading.value = true;

    try {
      // 调用聊天接口
      const normal_params = {
        session_id: currentSessionId.value,
        user_input: currentInput,
      };

      const util_params = {
        company_of_interest: getStockCode(currentInput),
        messages: [currentInput],
      };

      const response = await callAgent(normal_params, util_params);
      if (response.code === 0) {
        // 添加AI响应消息
        messages.value.push({
          type: 'ai-message',
          content: response.data.reply || response.data,
        });
      } else {
        throw new Error(response.msg || '请求失败');
      }
    } catch (error) {
      console.error('API调用失败:', error);
      message.error('请求失败，请稍后重试');

      // 添加错误响应消息
      messages.value.push({
        type: 'ai-message',
        content: '抱歉，服务暂时不可用，请稍后重试。',
      });
    } finally {
      isLoading.value = false;
      scrollToBottom();
    }
  };

  // 调用Agent
  const callAgent = async (normal_params, util_params) => {
    switch (activeAgent.value) {
      case 'market':
        return await getMarketReply(userStore.getToken, util_params);
      case 'fundamental':
        return await getFundamentalReply(userStore.getToken, util_params);
      case 'media':
        return await getWorkReply(userStore.getToken, util_params);
      default:
        return await getChatReply(userStore.getToken, normal_params);
    }
  };

  // 删除消息
  const deleteMessage = (index: number) => {
    messages.value.splice(index, 1);
    message.info('消息已删除');
  };

  // 清空所有消息
  const clearAllMessages = () => {
    if (messages.value.length === 0) {
      message.info('没有可清除的消息');
      return;
    }

    messages.value = [];
    currentSessionId.value = '';
    message.success('所有消息已清除');
  };

  // 创建新对话
  const createNewChat = () => {
    // 清空 URL 参数
    router.replace({ name: 'agent_index' });
    currentSessionId.value = '';
    messages.value = [];
    messages.value.push({
      type: 'ai-message',
      content:
        '您好！我是AI助手。请选择上方的Agent类型开始对话，记得在查询中填写股票代码（必需）。支持6位数字代码（如000001）或字母数字组合（如AAPL）。',
    });
    message.success('已创建新对话');
  };

  // 加载特定会话的历史记录
  const loadChatHistory = async (sessionId: string) => {
    try {
      const response = await getChatHistory(userStore.getToken, { session_id: sessionId });
      if (response.code === 0) {
        currentSessionId.value = sessionId;

        // 清空当前消息
        messages.value = [];

        // 加载历史消息
        const history: ChatMessage[] = response.data;
        history.forEach((msg) => {
          messages.value.push({
            type: msg.role === 'user' ? 'user-message' : 'ai-message',
            content: msg.content,
          });
        });

        message.success('历史对话已加载');
        scrollToBottom();
      } else {
        message.error('加载历史对话失败');
      }
    } catch (error) {
      console.error('加载历史对话失败:', error);
      message.error('加载历史对话失败');
    }
  };

  // 滚动到对话框底部
  const scrollToBottom = () => {
    if (messagesContainer.value) {
      nextTick(() => {
        if (messagesContainer.value)
          messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
      });
    }
  };

  // 调整输入框大小功能
  const startResize = (e: MouseEvent) => {
    isResizing.value = true;
    const startY = e.clientY;
    const startHeight = inputHeight.value;

    const onMouseMove = (moveEvent: MouseEvent) => {
      if (!isResizing.value) return;
      const deltaY = startY - moveEvent.clientY;
      const newHeight = Math.max(80, Math.min(400, startHeight + deltaY));
      inputHeight.value = newHeight;
    };

    const onMouseUp = () => {
      isResizing.value = false;
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  };

  // 监听用户输入变化，自动调整高度
  watch(userInput, () => {
    nextTick(() => {
      scrollToBottom();
    });
  });

  // 监听路由参数变化
  watch(
    () => route.query.session,
    (sessionId) => {
      if (sessionId && typeof sessionId === 'string') {
        loadChatHistory(sessionId);
      }
    },
    { immediate: true }
  );

  // 获取股票代码子字符串
  const getStockCode = (input: string) => {
    const stockCodeRegex = /【股票代码】\s*:\s*\[(.*?)(?=\s*-|\])/i;
    const stockCodeMatch = input.match(stockCodeRegex);
    if (stockCodeMatch && stockCodeMatch[1])
      return stockCodeMatch[1].replace(/请在此处填写股票代码，如.*?必须/gi, '').trim();
    return '输入不合规范';
  };

  onMounted(() => {
    // 如果URL中没有session参数，显示初始消息
    if (!route.query.session) {
      messages.value.push({
        type: 'ai-message',
        content:
          '您好！我是AI助手。请选择上方的Agent类型开始对话，记得在查询中填写股票代码（必需）。支持6位数字代码（如000001）或字母数字组合（如AAPL）。',
      });
    }
  });
</script>

<style scoped lang="scss">
  .ai-assistant-container {
    max-width: 1050px;
    margin: 0 auto;
    padding: 24px 20px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
      sans-serif;
    color: #333;
  }

  .header {
    text-align: center;
    margin-bottom: 32px;

    .title {
      font-size: 32px;
      font-weight: 700;
      margin: 0 0 8px;
      color: #1a1a1a;
    }

    .subtitle {
      font-size: 16px;
      color: #666;
      margin: 0;
    }
  }

  .chat-container {
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    margin-bottom: 40px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    height: 600px;
  }

  .chat-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    border-bottom: 1px solid #f0f0f0;
    background: #fafafa;
    flex-shrink: 0;

    .chat-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
      font-size: 16px;
    }

    .chat-actions {
      display: flex;
      gap: 8px;
    }
  }

  .chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .message {
    display: flex;
    gap: 12px;

    &.ai-message {
      .message-content {
        background: #f7f7f8;
        border-radius: 12px 12px 12px 0;
      }
    }

    &.user-message {
      flex-direction: row-reverse;

      .message-content {
        background: #4576f1;
        color: white;
        border-radius: 12px 12px 0 12px;
      }

      .delete-btn {
        color: rgba(255, 255, 255, 0.7);

        &:hover {
          color: white;
        }
      }
    }

    .message-avatar {
      :deep(.n-avatar) {
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
        border: 2px solid rgba(255, 255, 255, 0.9);
      }
    }

    .message-content {
      padding: 12px 16px;
      max-width: 80%;
      position: relative;
      display: flex;
      align-items: flex-start;
      gap: 8px;

      .message-text {
        white-space: pre-wrap;
        line-height: 1.5;
        flex: 1;

        pre {
          margin: 0;
          white-space: pre-wrap;
          font-family: inherit;
        }

        .markdown-content {
          line-height: 1.6;

          h1,
          h2,
          h3,
          h4,
          h5,
          h6 {
            margin: 16px 0 8px 0;
            font-weight: 600;
          }

          h1 {
            font-size: 1.4em;
          }
          h2 {
            font-size: 1.3em;
          }
          h3 {
            font-size: 1.2em;
          }
          h4 {
            font-size: 1.1em;
          }

          p {
            margin: 8px 0;
          }

          ul,
          ol {
            margin: 8px 0;
            padding-left: 24px;
          }

          li {
            margin: 4px 0;
          }

          blockquote {
            margin: 12px 0;
            padding: 8px 16px;
            background: #f0f0f0;
            border-left: 4px solid #4576f1;
            border-radius: 4px;
          }

          code {
            background: #f0f0f0;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 0.9em;
          }

          pre code {
            background: transparent;
            padding: 0;
          }

          table {
            width: 100%;
            border-collapse: collapse;
            margin: 12px 0;
          }

          th,
          td {
            padding: 8px 12px;
            border: 1px solid #e0e0e0;
            text-align: left;
          }

          th {
            background: #f5f5f5;
            font-weight: 600;
          }

          strong {
            font-weight: 600;
          }

          em {
            font-style: italic;
          }
        }
      }

      .message-actions {
        opacity: 0;
        transition: opacity 0.2s ease;
        flex-shrink: 0;
      }

      &:hover .message-actions {
        opacity: 1;
      }
    }
  }

  .chat-input-area {
    position: relative;
    border-top: 1px solid #f0f0f0;
    background: #fff;
    flex-shrink: 0;

    .resize-handle {
      position: absolute;
      top: -4px;
      left: 0;
      right: 0;
      height: 8px;
      cursor: ns-resize;
      z-index: 10;

      &:hover {
        background: rgba(0, 0, 0, 0.1);
      }
    }

    .input-container {
      display: flex;
      gap: 12px;
      align-items: flex-end;
      padding: 16px 20px;
      height: 100%;

      .message-input {
        flex: 1;

        :deep(.n-input__textarea-el) {
          resize: none;
          max-height: calc(v-bind(inputHeight) - 40px);
        }
      }

      .send-button {
        background: #4c44d7;
        border: none;
        flex-shrink: 0;

        &:hover {
          background: #665cf2;
        }

        &:disabled {
          background: #d0d0d0;
          cursor: not-allowed;
        }
      }
    }
  }

  .agents-section {
    .section-title {
      font-size: 20px;
      font-weight: 600;
      margin-bottom: 20px;
      text-align: center;
      color: #1a1a1a;
    }

    .agents-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 20px;
    }
  }

  .agent-card {
    cursor: pointer;
    transition: all 0.3s ease;
    border-radius: 12px;

    &:hover {
      transform: translateY(-4px);
      box-shadow: 0 8px 20px rgba(0, 0, 0, 0.12);
    }

    &.active {
      border: 2px solid #10a37f;
    }

    .card-content {
      text-align: center;
      padding: 20px 16px;

      .card-icon {
        margin-bottom: 12px;
        display: inline-flex;
        justify-content: center;
        align-items: center;
        width: 60px;
        height: 60px;
        border-radius: 12px;

        &.market {
          background: rgba(16, 163, 127, 0.1);
          color: #10a37f;
        }

        &.fundamental {
          background: rgba(59, 130, 246, 0.1);
          color: #3b82f6;
        }

        &.media {
          background: rgba(168, 85, 247, 0.1);
          color: #a855f7;
        }
      }

      .card-title {
        font-size: 18px;
        font-weight: 600;
        margin: 0 0 8px;
        color: #1a1a1a;
      }

      .card-description {
        font-size: 14px;
        color: #666;
        margin: 0;
      }
    }
  }

  // 响应式设计
  @media (max-width: 768px) {
    .ai-assistant-container {
      padding: 16px;
    }

    .header .title {
      font-size: 24px;
    }

    .chat-container {
      height: 500px;
    }

    .agents-grid {
      grid-template-columns: 1fr;
    }

    .message .message-content {
      max-width: 90%;
    }
  }
</style>
