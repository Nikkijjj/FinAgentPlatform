<template>
  <div class="history-container">
    <n-card title="历史对话管理" :bordered="false">
      <n-spin :show="loadingHistory">
        <div class="history-grid">
          <n-card
            v-for="([sessionId, session]) in sortedChatHistoryEntries"
            :key="sessionId"
            hoverable
            class="history-card"
            @click="goToChat(sessionId as string)"
          >
            <div class="history-card-content">
              <div class="history-actions">
                <n-button
                  text
                  type="error"
                  size="tiny"
                  @click.stop="removeSession(sessionId as string)"
                >
                  删除会话
                </n-button>
              </div>
              <div class="history-title">
                {{ getSessionTitle(sessionId as string, session) }}
              </div>
              <div class="history-time">
                {{ formatSessionTime(sessionId as string) }}
              </div>
              <div class="history-preview">
                {{ getSessionPreview(session) }}
              </div>
            </div>
          </n-card>

          <n-empty
            v-if="sortedChatHistoryEntries.length === 0"
            description="暂无历史对话"
            style="margin-top: 60px"
          >
            <template #extra>
              <n-button type="primary" @click="goToNewChat">开始新对话</n-button>
            </template>
          </n-empty>
        </div>
      </n-spin>
    </n-card>
  </div>
</template>

<script lang="ts" setup>
  import { computed, onMounted, ref } from 'vue';
  import { NCard, NSpin, NEmpty, NButton, useMessage } from 'naive-ui';
  import { useRouter } from 'vue-router';
  import { useUserStore } from '@/store/modules/user';
  import {
    deleteChatSession,
    getChatHistoryList,
    ChatMessage,
    ChatHistoryListResponse,
  } from '@/api/chat/chat';

  const message = useMessage();
  const router = useRouter();
  const userStore = useUserStore();

  const chatHistoryList = ref<ChatHistoryListResponse>({});
  const chatSessionTitles = ref<Record<string, string>>({});
  const loadingHistory = ref<boolean>(false);

  const parseSessionTimestamp = (sessionId: string): number => {
    const sid = String(sessionId || '');
    const m = sid.match(/^session_(\d+)_/);
    if (!m) return 0;
    const ts = Number(m[1]);
    return Number.isFinite(ts) ? ts : 0;
  };

  const sortedChatHistoryEntries = computed(() => {
    const entries = Object.entries(chatHistoryList.value || {}) as [string, ChatMessage[]][];
    return entries.sort((a, b) => {
      const ta = parseSessionTimestamp(a[0]);
      const tb = parseSessionTimestamp(b[0]);
      if (tb !== ta) return tb - ta;
      return String(b[0]).localeCompare(String(a[0]));
    });
  });

  // 获取历史对话列表
  const fetchChatHistoryList = async () => {
    loadingHistory.value = true;
    try {
      const userId = userStore.getUserId || userStore.getUsername || userStore.getName || '';
      const username = userStore.getUsername || userStore.getName || '';
      if (!userId && !username) {
        message.warning('缺少用户信息，无法加载历史对话');
        chatHistoryList.value = {};
        return;
      }
      const response = await getChatHistoryList(userStore.getToken, {
        user_id: userId,
        username,
        uid: userId,
        limit: 50,
      });
      if (response.code === 0) {
        chatHistoryList.value = response.data || {};
        const st = (response as { session_titles?: Record<string, string> }).session_titles;
        chatSessionTitles.value =
          st && typeof st === 'object' ? { ...st } : {};
      } else {
        console.error('获取历史对话失败:', response.msg);
        message.error('获取历史对话失败');
      }
    } catch (error) {
      console.error('获取历史对话失败:', error);
      message.error('获取历史对话失败');
    } finally {
      loadingHistory.value = false;
    }
  };

  // 获取会话标题（优先数据库自定义标题）
  const getSessionTitle = (sessionId: string, session: ChatMessage[]): string => {
    const custom = (chatSessionTitles.value[sessionId] || '').trim();
    if (custom) {
      return custom;
    }
    const firstUserMsg = session.find((msg) => msg.role === 'user');
    if (firstUserMsg) {
      return firstUserMsg.content;
    }
    return '新对话';
  };

  // 获取会话预览
  const getSessionPreview = (session: ChatMessage[]): string => {
    const firstAssistantMsg = session.find((msg) => msg.role === 'assistant');
    if (firstAssistantMsg) {
      const content = firstAssistantMsg.content;
      return content.length > 100 ? content.substring(0, 100) + '...' : content;
    }
    return '';
  };

  // 格式化会话时间
  const formatSessionTime = (sessionId: string): string => {
    try {
      const timestamp = parseInt(sessionId.split('_')[1]);
      const date = new Date(timestamp);
      const now = new Date();

      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);

      if (diffMins < 60) {
        return `${diffMins}分钟前`;
      } else if (diffHours < 24) {
        return `${diffHours}小时前`;
      } else if (diffDays < 7) {
        return `${diffDays}天前`;
      } else {
        return date.toLocaleDateString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
        });
      }
    } catch (e) {
      return '未知时间';
    }
  };

  // 跳转到聊天页面
  const goToChat = (sessionId: string) => {
    router.push({
      name: 'agent_index',
      query: { session: sessionId },
    });
  };

  const removeSession = async (sessionId: string) => {
    const userId = userStore.getUserId || '';
    const username = userStore.getUsername || userStore.getName || '';
    if (!userId && !username) {
      message.warning('缺少用户信息，无法删除会话');
      return;
    }
    try {
      const response = await deleteChatSession(userStore.getToken, {
        session_id: sessionId,
        user_id: userId || username,
        username,
        uid: userId,
      });
      if (response.code === 0) {
        message.success('会话已删除');
        await fetchChatHistoryList();
      } else {
        message.error(response.msg || '删除会话失败');
      }
    } catch (e) {
      console.error('删除会话失败:', e);
      message.error('删除会话失败');
    }
  };

  // 开始新对话
  const goToNewChat = () => {
    router.push({ name: 'agent_index' });
  };

  onMounted(() => {
    fetchChatHistoryList();
  });
</script>

<style scoped lang="scss">
  .history-container {
    padding: 20px;
  }

  .history-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 20px;
    margin-top: 20px;
  }

  .history-card {
    cursor: pointer;
    transition: all 0.3s ease;

    &:hover {
      transform: translateY(-4px);
      box-shadow: 0 8px 20px rgba(0, 0, 0, 0.12);
    }

    .history-card-content {
      .history-actions {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 4px;
      }

      .history-title {
        font-size: 16px;
        font-weight: 600;
        color: #333;
        margin-bottom: 8px;
        line-height: 1.4;
      }

      .history-time {
        font-size: 12px;
        color: #999;
        margin-bottom: 12px;
      }

      .history-preview {
        font-size: 14px;
        color: #666;
        line-height: 1.6;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
      }
    }
  }
</style>
