<template>
  <n-card class="project-scroll-wrapper" :bordered="false">
    <n-card class="large-card">
      <n-grid :cols="24" :x-gap="20" :y-gap="12" style="margin-right: 15px; margin-left: -5px">
        <n-gi v-for="(item, index) in messages" :key="index" :span="6">
          <n-card class="message-card">
            <template #header>
              <div class="header">
                <span class="header-label">{{ item.title }}</span>
              </div>
            </template>

            <div class="card-body">
              <div class="info-item">
                <n-icon class="info-icon">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16">
                    <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/>
                  </svg>
                </n-icon>
                <div>
                  <div class="card-label">发布时间</div>
                  <span class="card-value">{{ item.publishTime || '未设置' }}</span>
                </div>
              </div>
              <div class="info-item">
                <n-icon class="info-icon">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16">
                    <path fill="currentColor" d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                  </svg>
                </n-icon>
                <div>
                  <div class="card-label">发布方</div>
                  <span class="card-value">{{ item.publisher || '未知' }}</span>
                </div>
              </div>
            </div>
            
            <template #footer>
              <div class="card-footer">
                <n-button 
                  text 
                  class="action-btn"
                  @click="showDetail(item)"
                >
                  <template #icon>
                    <n-icon>
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16">
                        <path fill="currentColor" d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/>
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
    </n-card>

    <!-- 详情对话框 -->
    <n-modal 
      v-model:show="showModal" 
      preset="dialog" 
      title="项目详情"
      positive-text="关闭"
      @positive-click="closeModal"
      style="width: 600px"
    >
      <div class="markdown-content" v-html="renderedMarkdown"></div>
    </n-modal>

    <!-- 分页组件 -->
    <div style="position: fixed; bottom: 20px; left: 60%; transform: translateX(-50%)">
      <n-pagination />
    </div>
  </n-card>
</template>

<script lang="ts" setup>
  import { ref, computed } from 'vue';
  import { NCard, NGrid, NGridItem, NPagination, NButton, NIcon, NModal } from 'naive-ui';
  import { marked } from 'marked';

  // 配置 marked 选项
  marked.setOptions({
    breaks: true,
    gfm: true,
  });

  const messages = ref([
    {
      title: '项目A发布',
      publishTime: '2025-10-10',
      publisher: '发布方A',
      status: '1',
      description: '这是一个重要的项目发布，涉及多个技术栈和团队协作。',
      content: `# 项目A详细信息
  
## 项目概述
项目A是一个基于现代Web技术的企业级应用，旨在提高工作效率和团队协作。

## 技术栈
- **前端**: Vue 3 + TypeScript + Naive UI
- **后端**: Node.js + Express
- **数据库**: MongoDB
- **部署**: Docker + Kubernetes

## 主要功能
1. 用户管理
2. 项目管理
3. 实时协作
4. 数据分析

## 项目周期
- **开始时间**: 2025-01-15
- **预计完成**: 2025-12-30
- **当前进度**: 75%

## 团队成员
- 项目经理: 张三
- 前端开发: 李四
- 后端开发: 王五
- UI设计: 赵六`
    },
    { 
      title: '项目B发布', 
      publishTime: '2025-10-08', 
      publisher: '发布方B', 
      status: '0',
      description: '这是一个创新性的技术项目，采用了最新的开发模式。',
      content: `# 项目B详细信息

## 项目简介
项目B专注于人工智能和机器学习的应用开发。

## 核心特性
- 智能推荐系统
- 自然语言处理
- 图像识别
- 预测分析

## 技术亮点
- 使用TensorFlow进行模型训练
- 采用微服务架构
- 支持大规模数据处理
- 实时推理能力

## 应用场景
1. 电商推荐
2. 智能客服
3. 内容审核
4. 风险控制`
    },
    { 
      title: '项目C发布', 
      publishTime: '2025-10-05', 
      publisher: '发布方C', 
      status: '1',
      description: '移动端应用开发项目，支持多平台运行。',
      content: `# 项目C详细信息

## 项目背景
开发一款跨平台的移动应用，满足现代用户的需求。

## 平台支持
- iOS
- Android
- Web
- 微信小程序

## 开发工具
- React Native
- TypeScript
- Redux状态管理
- Jest测试框架

## 版本历史
- v1.0: 基础功能 (2025-03-01)
- v1.5: 性能优化 (2025-06-15)
- v2.0: 新增功能 (2025-10-05)`
    },
    { 
      title: '项目D发布', 
      publishTime: '2025-10-03', 
      publisher: '发布方D', 
      status: '0',
      description: '后台管理系统项目，提供完整的数据管理解决方案。',
      content: `# 项目D详细信息

## 系统架构
采用前后端分离的架构设计，确保系统的高可用性和可扩展性。

## 功能模块
- **用户管理**: 角色权限控制
- **数据统计**: 可视化图表展示
- **系统监控**: 实时性能监控
- **日志管理**: 操作日志记录

## 安全特性
- JWT身份认证
- 数据加密传输
- 防SQL注入
- XSS攻击防护`
    },
    { 
      title: '项目E发布', 
      publishTime: '2025-10-01', 
      publisher: '发布方E', 
      status: '1',
      description: '大数据分析平台，支持海量数据处理。',
      content: `# 项目E详细信息

## 平台能力
- 日处理数据量: 10TB+
- 实时数据处理延迟: < 1秒
- 支持数据源: 20+种

## 核心技术
- Apache Spark
- Apache Flink
- Apache Kafka
- Elasticsearch

## 应用价值
1. 业务决策支持
2. 用户行为分析
3. 市场趋势预测
4. 风险预警`
    },
    { 
      title: '项目F发布', 
      publishTime: '2025-09-28', 
      publisher: '发布方F', 
      status: '1',
      description: '云原生应用部署平台，简化运维流程。',
      content: `# 项目F详细信息

## 平台特性
- 一键部署
- 自动扩缩容
- 健康检查
- 日志收集

## 支持环境
- 开发环境
- 测试环境
- 预生产环境
- 生产环境

## 集成工具
- Jenkins CI/CD
- Prometheus监控
- Grafana仪表板
- Alertmanager告警`
    },
  ]);

  const showModal = ref(false);
  const currentItem = ref<any>(null);

  const showDetail = (item: any) => {
    currentItem.value = item;
    showModal.value = true;
  };

  const closeModal = () => {
    showModal.value = false;
    currentItem.value = null;
  };

  const renderedMarkdown = computed(() => {
    if (!currentItem.value) return '';
    return marked(currentItem.value.content);
  });
</script>

<style scoped lang="scss">
  .project-scroll-wrapper {
    height: 90%;
    overflow-y: auto;
    border-radius: 10px;
    background-color: #f1f1f1;
    border: none;
    box-shadow: none;
  }

  .no-change-on-hover:hover,
  .no-change-on-hover:active {
    background-color: transparent !important;
    border-color: transparent !important;
    color: inherit !important;
  }

  .add-box-card {
    transition: background-color 0.3s ease;
  }

  .add-box-card:hover {
    background-color: rgba(0, 0, 0, 0.073);
  }

  .add-card-body {
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .n-grid {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    max-height: 730px;
    overflow-y: auto;
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
</style>

<style>
  /* Markdown 内容样式 */
  .markdown-content {
    padding: 16px 0;
    line-height: 1.6;
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

  .markdown-content ul, .markdown-content ol {
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