<template>
  <div class="ai-assistant-container">
    <!-- 标题区域 -->
    <div class="header">
      <h1 class="title">AI Assistant</h1>
      <p class="subtitle">选择适合的Agent，获取专业AI协助</p>
    </div>

    <!-- 对话框区域 -->
    <div class="chat-container">
      <div class="chat-header">
        <div class="chat-title">
          <n-icon size="24" color="#4576F1">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path
                d="M20.5 14.5V16H19v-1.5h1.5zm-13 0H9V16H5.5v-1.5h2zM16 9c0-2.21-1.79-4-4-4S8 6.79 8 9s1.79 4 4 4 4-1.79 4-4zM3.5 18c0-3.5 6-5.5 9-5.5s9 2 9 5.5V20H3.5v-2z"
              />
            </svg>
          </n-icon>
          <span>AI Assistant</span>
        </div>
        <div class="chat-actions">
          <n-button quaternary circle @click="clearAllMessages">
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
              :style="{ backgroundColor: m.type === 'ai-message' ? '#4576F1' : '#D5DCEE' }"
            >
              <n-icon>
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path
                    v-if="m.type === 'ai-message'"
                    d="M20.5 14.5V16H19v-1.5h1.5zm-13 0H9V16H5.5v-1.5h2zM16 9c0-2.21-1.79-4-4-4S8 6.79 8 9s1.79 4 4 4 4-1.79 4-4zM3.5 18c0-3.5 6-5.5 9-5.5s9 2 9 5.5V20H3.5v-2z"
                  />
                  <path
                    v-else
                    d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"
                  />
                </svg>
              </n-icon>
            </n-avatar>
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
            <n-avatar round size="small" :style="{ backgroundColor: '#4576F1' }">
              <n-icon>
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path
                    d="M20.5 14.5V16H19v-1.5h1.5zm-13 0H9V16H5.5v-1.5h2zM16 9c0-2.21-1.79-4-4-4S8 6.79 8 9s1.79 4 4 4 4-1.79 4-4zM3.5 18c0-3.5 6-5.5 9-5.5s9 2 9 5.5V20H3.5v-2z"
                  />
                </svg>
              </n-icon>
            </n-avatar>
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
      <div class="chat-input-area" :style="{ height: inputHeight + 'px' }">
        <div class="resize-handle" @mousedown="startResize"></div>
        <div class="input-container">
          <n-input
            v-model:value="userInput"
            type="textarea"
            placeholder="请选择上方的Agent类型或直接输入您的问题..."
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
      <h2 class="section-title">选择Agent类型</h2>
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
                  <path
                    d="M12 6.5c2.76 0 5 2.24 5 5 0 1.64-.8 3.09-2.03 4 .03.25.03.5.03.75 0 2.9-2.35 5.25-5.25 5.25S4.5 19.4 4.5 16.5c0-2.9 2.35-5.25 5.25-5.25.46 0 .91.06 1.34.17C10.5 10.62 10 9.11 10 7.5c0-.83.17-1.62.47-2.34.3.05.6.08.91.08.26 0 .51-.03.75-.08.25.05.5.08.76.08.26 0 .51-.03.75-.08.24.05.49.08.75.08.31 0 .61-.03.9-.08.3.72.47 1.51.47 2.34 0 .26-.02.51-.05.75.41-.11.85-.17 1.31-.17.26 0 .51.03.75.08.24-.72.4-1.48.4-2.28 0-2.76-2.24-5-5-5z"
                  />
                </svg>
              </n-icon>
            </div>
            <h3 class="card-title">Market Agent</h3>
            <p class="card-description">市场分析与投资建议</p>
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
            <h3 class="card-title">Fundamental Agent</h3>
            <p class="card-description">基本面分析与财务数据</p>
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
            <h3 class="card-title">Media Agent</h3>
            <p class="card-description">媒体内容创作与优化</p>
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

  const message = useMessage();

  // 响应式数据
  const activeAgent = ref<string>('');
  const userInput = ref<string>('');
  const messages = ref<Array<{ type: string; content: string; isTemplate?: boolean }>>([]);
  const inputHeight = ref<number>(120);
  const isResizing = ref<boolean>(false);
  const messagesContainer = ref<HTMLElement>();
  const inputRef = ref<any>();
  const isLoading = ref<boolean>(false);

  // Agent提示词模板
  const agentTemplates = {
    market: `请分析以下市场情况并提供投资建议：

【股票代码】: [请在此处填写股票代码，如AAPL、TSLA、00700.HK、000001等 - 必需]
【市场领域】: [请在此处填写您关注的市场领域，如科技、医疗、能源等]
【时间范围】: [请在此处填写关注的时间范围，如近期、未来3个月、未来1年等]
【投资偏好】: [请在此处填写您的投资偏好，如稳健型、成长型、高风险高回报等]
【关注指标】: [请在此处填写您关注的指标，如市盈率、增长率、市场份额等]

请基于以上信息，提供详细的市场分析和投资建议。`,

    fundamental: `请分析以下基本面情况并提供财务分析：

【股票代码】: [请在此处填写股票代码，如AAPL、TSLA、00700.HK、000001等 - 必需]
【分析维度】: [请在此处填写分析维度，如财务健康度、盈利能力、成长性等]
【时间范围】: [请在此处填写分析时间范围，如最近季度、年度、三年期等]
【关注指标】: [请在此处填写您关注的财务指标，如营收、净利润、ROE、负债率等]
【比较基准】: [请在此处填写比较基准，如同行业公司、市场平均等]

请基于以上信息，提供基本面分析和财务评估。`,

    media: `请协助创作或优化以下媒体内容：

【股票代码】: [请在此处填写股票代码，如AAPL、TSLA、00700.HK、000001等 - 必需]
【内容类型】: [请在此处填写内容类型，如文章、视频脚本、社交媒体帖子等]
【目标受众】: [请在此处填写目标受众，如年轻人、专业人士、特定兴趣群体等]
【核心信息】: [请在此处填写核心信息或关键点]
【风格要求】: [请在此处填写风格要求，如正式、轻松幽默、专业严谨等]

请基于以上信息，提供内容创作建议或优化方案。`,
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

  // 获取当前时间字符串
  const getCurrentTimeString = (): string => {
    const now = new Date();
    return now.toISOString().split('T')[0]; // 返回 YYYY-MM-DD 格式
  };

  // 解析股票代码
  const parseStockCode = (input: string): string => {
    const stockCodeMatch = input.match(/【股票代码】:\s*([^\n\r\[\]]+)/);
    if (stockCodeMatch && stockCodeMatch[1]) {
      const code = stockCodeMatch[1].trim();

      // 检查是否是占位符
      if (code.includes('请在此处填写股票代码')) {
        return '';
      }

      // 验证股票代码格式
      if (isValidStockCode(code)) {
        return code;
      }
    }
    return '';
  };

  // 验证股票代码格式
  const isValidStockCode = (code: string): boolean => {
    // 1. 6位纯数字（A股代码）
    const sixDigitPattern = /^\d{6}$/;

    // 2. 字母数字组合（美股、港股等）
    const alphaNumericPattern = /^[A-Za-z0-9.]{1,10}$/;

    return sixDigitPattern.test(code) || alphaNumericPattern.test(code);
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

    // 解析股票代码
    const stockCode = parseStockCode(userInput.value);
    if (!stockCode) {
      message.error('请填写有效的股票代码（6位数字或字母数字组合）');
      return;
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
      // 根据选择的Agent调用不同的后端接口
      let response;
      switch (activeAgent.value) {
        case 'market':
          response = await callMarketAgent(currentInput, stockCode);
          break;
        case 'fundamental':
          response = await callFundamentalAgent(currentInput, stockCode);
          break;
        case 'media':
          response = await callMediaAgent(currentInput, stockCode);
          break;
        default:
          throw new Error('请先选择Agent类型');
      }

      // 添加AI响应消息
      messages.value.push({
        type: 'ai-message',
        content: response,
      });
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

  // 调用Market Agent API
  const callMarketAgent = async (userMessage: string, stockCode: string): Promise<string> => {
    const requestData = {
      company_of_interest: stockCode,
      trade_date: getCurrentTimeString(),
      messages: [userMessage],
    };

    const response = await fetch('/api/market/get/report', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestData),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data.data || '收到市场分析数据，正在生成报告...';
  };

  // 调用Fundamental Agent API
  const callFundamentalAgent = async (userMessage: string, stockCode: string): Promise<string> => {
    const requestData = {
      company_of_interest: stockCode,
      trade_date: getCurrentTimeString(),
      messages: [userMessage],
    };

    const response = await fetch('/api/fundamentals/get/report', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestData),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: s${response.status}`);
    }

    const data = await response.json();
    return data.data || '收到基本面数据，正在生成分析报告...';
  };

  // 调用Media Agent API
  const callMediaAgent = async (userMessage: string, stockCode: string): Promise<string> => {
    const requestData = {
      company_of_interest: stockCode,
      trade_date: getCurrentTimeString(),
      messages: [userMessage],
    };

    const response = await fetch('/api/social_media/get/report', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestData),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data.data || '收到媒体数据，正在生成内容建议...';
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
    message.success('所有消息已清除');
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

  onMounted(() => {
    // 初始示例消息
    messages.value.push({
      type: 'ai-message',
      content:
        '您好！我是AI助手。请选择上方的Agent类型开始对话，记得在查询中填写股票代码（必需）。支持6位数字代码（如000001）或字母数字组合（如AAPL）。',
    });
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
