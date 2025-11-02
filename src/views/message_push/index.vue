<template>
  <n-card class="large-card">
    <!-- 筛选器区域 -->
    <div class="filter-container">
      <n-space align="center">
        <span class="filter-label">发布时间范围：</span>
        <n-date-picker
          v-model:value="dateRange"
          type="daterange"
          clearable
          @update:value="handleDateFilter"
          placeholder="选择日期范围"
        />
        <n-button @click="resetFilter" type="primary" ghost size="small"> 重置 </n-button>
      </n-space>
    </div>

    <!-- 项目卡片网格 -->
    <n-grid :cols="24" :x-gap="20" :y-gap="10" class="scrollable-content">
      <n-gi v-for="(item, index) in filteredMessages" :key="index" :span="6">
        <n-card class="message-card" :class="{ read: item.is_read == 'yes' }">
          <template #header>
            <div class="header">
              <span class="header-label">{{ extractTruncatedTitle(item.report) }}</span>
              <div :class="{ 'red-circle': item.is_read != 'yes' }"></div>
            </div>
          </template>

          <div class="card-body">
            <div class="info-item">
              <n-icon class="info-icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16">
                  <path
                    fill="currentColor"
                    d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"
                  />
                </svg>
              </n-icon>
              <div>
                <div class="card-label">发布时间</div>
                <span class="card-value">{{ item.trade_date || '未设置' }}</span>
              </div>
            </div>
            <div class="info-item">
              <n-icon class="info-icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16">
                  <path
                    fill="currentColor"
                    d="M19 3h-4.18C14.4 1.84 13.3 1 12 1c-1.3 0-2.4.84-2.82 2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 0c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zm2 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"
                  />
                </svg>
              </n-icon>
              <div>
                <div class="card-label">消息内容</div>
                <span class="card-value">{{ truncateContent(item.report) }}</span>
              </div>
            </div>
          </div>

          <template #footer>
            <div class="card-footer">
              <n-button text class="action-btn" @click="showDetail(item)">
                <template #icon>
                  <n-icon>
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 24 24"
                      width="16"
                      height="16"
                    >
                      <path
                        fill="currentColor"
                        d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"
                      />
                    </svg>
                  </n-icon>
                </template>
                查看详情
              </n-button>
            </div>
          </template>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- 固定分页器 -->
    <div class="pagination-container">
      <n-pagination
        v-model:page="currentPage"
        :page-count="totalPages"
        @update:page="handlePageChange"
      />
    </div>
  </n-card>

  <!-- 详情对话框 -->
  <n-modal
    v-model:show="showModal"
    preset="dialog"
    title="项目详情"
    positive-text="关闭"
    @positive-click="closeModal"
    :style="{
      width: '800px',
      maxWidth: '90vw',
      height: '600px',
    }"
    class="fixed-dialog"
  >
    <div class="dialog-content">
      <div class="markdown-content" v-html="renderedMarkdown"></div>
    </div>
  </n-modal>
</template>

<script lang="ts" setup>
  import { ref, computed, onMounted } from 'vue';
  import { NCard, NGrid, NPagination, NButton, NIcon, NModal, NDatePicker, NSpace } from 'naive-ui';
  import { marked } from 'marked';
  import {
    extractTruncatedTitle,
    fetchMessages,
    MessageData,
    truncateContent,
  } from '@/api/message_push/message';
  import { mockMessageResponse } from '../../../mock/message_push';

  // 配置 marked 选项
  marked.setOptions({
    breaks: true,
    gfm: true,
  });

  // 原始数据
  const originalMessages = ref<MessageData[]>([]);

  // 响应式数据
  const messages = ref<MessageData[]>([]);
  let pageSize: number;
  let totalPages: number;
  const dateRange = ref<[number, number] | null>(null);
  const currentPage = ref(1);
  const showModal = ref(false);
  const currentItem = ref<any>(null);

  const filteredMessages = computed(() => {
    const startIndex = (currentPage.value - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    return messages.value.slice(startIndex, endIndex);
  });

  const renderedMarkdown = computed(() => {
    if (!currentItem.value) return '';
    return marked(currentItem.value.report);
  });

  // 方法
  const handleDateFilter = () => {
    if (!dateRange.value) {
      // 重置筛选
      messages.value = originalMessages.value;
      currentPage.value = 1;
      return;
    }

    console.log('未被Date处理的dateRange:', dateRange);

    const [startTimestamp, endTimestamp] = dateRange.value;
    const startDate = new Date(startTimestamp);
    const endDate = new Date(endTimestamp);
    endDate.setHours(23, 59, 59);
    console.log('Date转换后的startDate:', startDate);
    console.log('Date转换后的endDate:', endDate);

    messages.value = originalMessages.value.filter((item) => {
      const itemDate = new Date(item.trade_date);
      return itemDate >= startDate && itemDate <= endDate;
    });
    currentPage.value = 1;
  };

  const resetFilter = () => {
    dateRange.value = null;
    messages.value = originalMessages.value;
    currentPage.value = 1;
  };

  const handlePageChange = (page: number) => {
    currentPage.value = page;
  };

  const showDetail = (item: MessageData) => {
    currentItem.value = item;
    item.is_read = 'yes';
    showModal.value = true;
  };

  const closeModal = () => {
    showModal.value = false;
    currentItem.value = null;
  };

  // 生命周期
  onMounted(async () => {
    const messageResponse = await mockMessageResponse();
    const { current_data, pagination } = messageResponse.data;
    originalMessages.value = [...current_data];
    messages.value = [...originalMessages.value];
    pageSize = pagination.size;
    totalPages = pagination.total;
  });
</script>

<style scoped lang="scss">
  .large-card {
    position: relative;
    height: 100%;
    display: flex;
    flex-direction: column;
    border-radius: 10px;
    overflow: hidden;
  }

  .filter-container {
    padding: 10px 10px;
    border-bottom: 1px solid #f0f0f0;
    background-color: #fff;

    .filter-label {
      font-weight: 500;
      color: #1f2937;
    }
  }

  .scrollable-content {
    flex: 1;
    overflow-y: auto;
    padding: 0 20px;
    margin-top: 12px;
    max-height: calc(100% - 120px);
  }

  .pagination-container {
    position: sticky;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 16px 20px;
    background-color: #fff;
    border-top: 1px solid #f0f0f0;
    display: flex;
    justify-content: center;
    z-index: 10;
  }

  .n-grid {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
  }

  .n-grid .n-card {
    margin-top: 12px;
    min-width: 100%;
    height: 100%;
    margin-right: 20px;
    margin-left: 10px;
    transition: all 0.5s;
    border-radius: 5px;
  }

  /* 美化后的卡片样式 */
  .message-card {
    transition: all 0.3s ease;
    border-radius: 12px !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    border: 1px solid #f0f0f0;
    overflow: hidden;

    &:hover {
      transform: translateY(-4px);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
    }
  }

  .read {
    background-color: #e5dddd;
  }

  .red-circle {
    width: 20px;
    height: 20px;
    background-color: red;
    border-radius: 50%;
  }

  .header {
    display: flex;
    align-items: center;
    position: relative;
    padding-bottom: 12px;
    border-bottom: 1px solid #f0f0f0;

    .header-label {
      font-size: 16px;
      font-weight: 600;
      color: #1f2937;
      flex: 1;
    }
  }

  .card-body {
    padding: 16px 0;
    font-size: 14px;

    .info-item {
      display: flex;
      align-items: flex-start;
      margin-bottom: 16px;

      &:last-child {
        margin-bottom: 0;
      }

      .info-icon {
        margin-right: 10px;
        margin-top: 2px;
        color: #6b7280;
        flex-shrink: 0;
      }

      .card-label {
        color: #9ca3af;
        font-size: 12px;
        margin-bottom: 4px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }

      .card-value {
        color: #374151;
        font-weight: 500;
      }
    }
  }

  .card-footer {
    display: flex;
    justify-content: center;
    padding-top: 12px;
    border-top: 1px solid #f0f0f0;

    .action-btn {
      color: #4f46e5;
      font-size: 13px;
      font-weight: 500;

      &:hover {
        color: #3730a3;
        background-color: rgba(79, 70, 229, 0.04);
      }
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

<style>
  /* Markdown 内容样式 */
  .markdown-content {
    line-height: 1.6;
    padding-bottom: 16px; /* 为底部留出一些空间 */
  }

  .markdown-content h1 {
    font-size: 1.5em;
    font-weight: 600;
    margin-bottom: 16px;
    color: #1f2937;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 8px;
  }

  .markdown-content h2 {
    font-size: 1.25em;
    font-weight: 600;
    margin: 20px 0 12px 0;
    color: #374151;
  }

  .markdown-content h3 {
    font-size: 1.1em;
    font-weight: 600;
    margin: 16px 0 8px 0;
    color: #4b5563;
  }

  .markdown-content p {
    margin-bottom: 12px;
    color: #6b7280;
  }

  .markdown-content ul,
  .markdown-content ol {
    margin-bottom: 16px;
    padding-left: 24px;
  }

  .markdown-content li {
    margin-bottom: 6px;
    color: #6b7280;
  }

  .markdown-content strong {
    color: #374151;
    font-weight: 600;
  }

  .markdown-content code {
    background-color: #f3f4f6;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 0.9em;
    color: #dc2626;
  }
</style>
