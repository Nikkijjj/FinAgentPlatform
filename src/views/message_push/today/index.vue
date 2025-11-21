<script setup lang="ts">
  import { onMounted, ref } from 'vue';
  import {
    cleanMarkdown,
    fetchMessageByDay,
    StockNews,
    updateReadStatus,
  } from '@/api/message/message';
  import { useRouter } from 'vue-router';
  import { useUserStore } from '@/store/modules/user';
  import { getLocalDate } from '@/api/time';
  import { useMessage } from 'naive-ui';
  import { marked } from 'marked';

  const router = useRouter();
  const userStore = useUserStore();
  const message = useMessage();

  marked.setOptions({
    breaks: true,
    gfm: true,
  });

  const originalMessages = ref<StockNews[]>([]);
  const messages = ref<StockNews[]>([]);

  const renderedMarkdown = (text: string) => {
    return marked(text);
  };

  const toHistory = () => {
    router.push('/message_push/history');
  };

  const updateRead = (item: StockNews) => {
    item.is_read = 'yes';
    const params = {
      id: item._id,
    };
    updateReadStatus(userStore.getToken, params);
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
          :title="m.label"
          class="report-header"
        >
          <template v-if="m.is_read != 'yes'" #icon>
            <n-icon>
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#FF3B30">
                <circle cx="12" cy="12" r="6" />
              </svg>
            </n-icon>
          </template>
          <n-card
            @click="updateRead(m)"
            class="report-card"
            :class="{ read: m.is_read == 'yes' }"
            content-class="report-card"
            header-class="report-header"
          >
            <div>
              <n-ellipsis
                class="ellipsis-text report-content"
                :line-clamp="3"
                expand-trigger="click"
              >
                <div class="markdown-content" v-html="renderedMarkdown(m.report)"></div>
                <template #tooltip>点击展开</template>
              </n-ellipsis>
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
    max-width: 120px;
    pointer-events: all;
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

  .markdown-content {

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
  }
</style>
