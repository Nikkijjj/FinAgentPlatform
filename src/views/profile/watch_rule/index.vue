<template>
  <div class="monitoring-rules-container">
    <n-card :bordered="false" class="rules-card" size="large">
      <!-- 头部操作区 -->
      <div class="rules-header">
        <div class="header-title">
          <h2 class="title-text">盯盘规则管理</h2>
          <p class="title-subtext">实时监控市场动态，及时把握投资机会</p>
        </div>
        <div class="header-stats">
          <n-space>
            <n-statistic label="总规则数" :value="rulesData.length">
              <template #prefix>
                <n-icon size="20" color="#3b82f6">
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                    <line x1="16" y1="13" x2="8" y2="13" />
                    <line x1="16" y1="17" x2="8" y2="17" />
                    <polyline points="10 9 9 9 8 9" />
                  </svg>
                </n-icon>
              </template>
            </n-statistic>
            <n-statistic label="活跃规则" :value="activeRulesCount" class="statistic-item">
              <template #prefix>
                <n-icon size="20" color="#10b981">
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                    <polyline points="22 4 12 14.01 9 11.01" />
                  </svg>
                </n-icon>
              </template>
            </n-statistic>
          </n-space>
        </div>
      </div>

      <!-- 规则类型统计 -->
      <div class="rules-summary">
        <n-space :wrap="false" :size="[24, 16]">
          <n-card class="summary-card" size="small" hoverable v-for="(type, index) in ruleTypeStats" :key="index">
            <div class="summary-card-content">
              <div class="summary-icon" :style="{ backgroundColor: type.color + '20' }">
                <n-icon size="24" :color="type.color">
                  <component :is="type.icon" />
                </n-icon>
              </div>
              <div class="summary-info">
                <div class="summary-count">{{ type.count }}</div>
                <div class="summary-label">{{ type.label }}</div>
              </div>
            </div>
          </n-card>
        </n-space>
      </div>

      <!-- 规则列表 -->
      <div class="rules-list">
        <div class="list-header">
          <h3 class="list-title">所有盯盘规则</h3>
          <div class="list-filters">
            <n-select
              v-model:value="selectedType"
              placeholder="筛选规则类型"
              :options="typeOptions"
              clearable
              style="width: 200px"
            />
          </div>
        </div>

        <!-- 加载状态 -->
        <div v-if="loading" class="loading-state">
          <n-spin size="large" />
          <p class="loading-text">加载规则数据中...</p>
        </div>

        <!-- 规则网格 -->
        <div v-else class="rules-grid">
          <n-card
            v-for="(rule, index) in filteredRules"
            :key="index"
            class="rule-card"
            hoverable
            :class="getRuleCardClass(rule.event_type)"
          >
            <div class="rule-card-header">
              <div class="rule-type-badge">
                <n-tag :bordered="false" size="small" :color="getEventTypeColor(rule.event_type)" round>
                  {{ getEventTypeLabel(rule.event_type) }}
                </n-tag>
                <n-tag v-if="rule.event_subtype" size="small" :bordered="false" type="default" round>
                  {{ getEventSubtypeLabel(rule.event_subtype) }}
                </n-tag>
              </div>
              <div class="rule-actions">
                <n-button size="tiny" text @click="toggleRuleStatus(index)">
                  <template #icon>
                    <n-icon>
                      <svg v-if="rule.active" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M18 6 6 18" />
                        <path d="m6 6 12 12" />
                      </svg>
                      <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    </n-icon>
                  </template>
                  {{ rule.active ? '停用' : '启用' }}
                </n-button>
              </div>
            </div>

            <div class="rule-card-body">
              <h4 class="rule-title">{{ rule.event_description }}</h4>
              
              <div class="rule-details">
                <div class="detail-item">
                  <n-icon size="16" class="detail-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M12 2v20" />
                      <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                    </svg>
                  </n-icon>
                  <span class="detail-label">关联标的：</span>
                  <span class="detail-value">{{ rule.related_stock }}</span>
                </div>

                <div class="detail-item">
                  <n-icon size="16" class="detail-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                      <polyline points="22 4 12 14.01 9 11.01" />
                    </svg>
                  </n-icon>
                  <span class="detail-label">触发条件：</span>
                  <span class="detail-value">{{ rule.trigger_condition }}</span>
                </div>

                <div class="detail-item">
                  <n-icon size="16" class="detail-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <circle cx="12" cy="12" r="10" />
                      <polyline points="12 6 12 12 16 14" />
                    </svg>
                  </n-icon>
                  <span class="detail-label">最后触发：</span>
                  <span class="detail-value">{{ rule.last_triggered || '暂未触发' }}</span>
                </div>
              </div>

              <div class="rule-progress">
                <div class="progress-info">
                  <span>触发频率</span>
                  <span>{{ rule.trigger_count || 0 }}次</span>
                </div>
                <n-progress
                  :percentage="Math.min((rule.trigger_count || 0) * 10, 100)"
                  :height="4"
                  :show-indicator="false"
                  :border-radius="2"
                  status="success"
                />
              </div>
            </div>

            <div class="rule-card-footer">
              <div class="rule-status">
                <n-badge dot :type="rule.active ? 'success' : 'default'" :processing="rule.active">
                  <span class="status-text">{{ rule.active ? '监控中' : '已停用' }}</span>
                </n-badge>
              </div>
              <n-button size="tiny" text @click="viewRuleDetails(rule)">
                详情
              </n-button>
            </div>
          </n-card>
        </div>

        <!-- 空状态 -->
        <div v-if="!loading && filteredRules.length === 0" class="empty-state">
          <n-empty description="暂无规则" size="large">
            <template #icon>
              <n-icon size="60" color="#d1d5db">
                <svg xmlns="http://www.w3.org/2000/svg" width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                  <polyline points="10 9 9 9 8 9" />
                </svg>
              </n-icon>
            </template>
          </n-empty>
        </div>
      </div>
    </n-card>

    <!-- 规则详情模态框 -->
    <n-modal v-model:show="showDetailModal">
      <n-card
        style="width: 600px"
        title="规则详情"
        :bordered="false"
        size="huge"
        role="dialog"
        aria-modal="true"
      >
        <template #header-extra>
          <n-button quaternary circle @click="showDetailModal = false">
            <template #icon>
              <n-icon>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </n-icon>
            </template>
          </n-button>
        </template>

        <div v-if="selectedRule" class="rule-detail">
          <div class="detail-header">
            <div class="detail-type-badge">
              <n-tag :bordered="false" size="medium" :color="getEventTypeColor(selectedRule.event_type)" round>
                {{ getEventTypeLabel(selectedRule.event_type) }}
              </n-tag>
              <n-tag v-if="selectedRule.event_subtype" size="medium" :bordered="false" type="default" round>
                {{ getEventSubtypeLabel(selectedRule.event_subtype) }}
              </n-tag>
            </div>
            <h3 class="detail-title">{{ selectedRule.event_description }}</h3>
          </div>

          <div class="detail-grid">
            <div class="detail-item">
              <div class="detail-item-label">
                <n-icon>
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                    <circle cx="9" cy="7" r="4" />
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                  </svg>
                </n-icon>
                关联标的
              </div>
              <div class="detail-item-value">
                <n-tag type="info" round>
                  {{ selectedRule.related_stock }}
                </n-tag>
              </div>
            </div>

            <div class="detail-item">
              <div class="detail-item-label">
                <n-icon>
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                    <polyline points="22 4 12 14.01 9 11.01" />
                  </svg>
                </n-icon>
                触发条件
              </div>
              <div class="detail-item-value">{{ selectedRule.trigger_condition }}</div>
            </div>

            <div class="detail-item">
              <div class="detail-item-label">
                <n-icon>
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10" />
                    <polyline points="12 6 12 12 16 14" />
                  </svg>
                </n-icon>
                最后触发时间
              </div>
              <div class="detail-item-value">{{ selectedRule.last_triggered || '暂未触发' }}</div>
            </div>

            <div class="detail-item">
              <div class="detail-item-label">
                <n-icon>
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="12" y1="1" x2="12" y2="23" />
                    <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                  </svg>
                </n-icon>
                触发次数
              </div>
              <div class="detail-item-value">{{ selectedRule.trigger_count || 0 }} 次</div>
            </div>

            <div class="detail-item">
              <div class="detail-item-label">
                <n-icon>
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                    <line x1="3" y1="9" x2="21" y2="9" />
                    <line x1="9" y1="21" x2="9" y2="9" />
                  </svg>
                </n-icon>
                创建时间
              </div>
              <div class="detail-item-value">{{ selectedRule.created_at || '未知' }}</div>
            </div>
          </div>
        </div>
      </n-card>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
  import { ref, computed, onMounted } from 'vue';
  import { useMessage, NIcon } from 'naive-ui';
  import { 
    BarChartOutlined,
    LineChartOutlined,
    BankOutlined,
    BuildOutlined,
    GlobalOutlined,
    CommentOutlined,
    ReadOutlined
  } from '@vicons/antd';
  // 导入您的API和store
  import { useUser } from '@/store/modules/user';
  import { getRule } from '@/api/user/user'; // 根据您的路径调整

  // 定义规则数据类型
  interface MonitoringRule {
    event_description: string;
    event_subtype: string;
    event_type: string;
    related_stock: string;
    trigger_condition: string;
    active?: boolean;
    last_triggered?: string;
    trigger_count?: number;
    created_at?: string;
  }

  // 规则类型配置
  const eventTypeConfig = {
    Trading: { label: '交易', color: '#3b82f6', icon: BarChartOutlined },
    Capital: { label: '资金', color: '#10b981', icon: LineChartOutlined },
    Company: { label: '公司', color: '#f59e0b', icon: BankOutlined },
    Industry: { label: '行业', color: '#8b5cf6', icon: BuildOutlined },
    Macro: { label: '宏观', color: '#ef4444', icon: GlobalOutlined },
    Sentiment: { label: '情绪', color: '#ec4899', icon: CommentOutlined },
    News: { label: '新闻', color: '#14b8a6', icon: ReadOutlined }
  };

  // 事件子类型映射
  const eventSubtypeLabels: Record<string, string> = {
    'price_fall_abnormal': '异常下跌',
    'ma_break_up': '均线突破',
    'price_rise_abnormal': '异常上涨',
    'northbound_inflow_abnormal': '北向流入异常',
    'performance_forecast': '业绩预告',
    'financial_report_change': '财报变化',
    'industry_consistency_rise': '行业一致性上涨',
    'industry_leader_fluctuation': '行业龙头波动',
    'macro_央行政策': '央行政策',
    'macro_金融监管': '金融监管',
    'attention_surge': '关注度激增',
    'hot_list_top10': '热门榜前十',
    'positive_news': '正面新闻',
    'negative_news': '负面新闻',
    'regulatory_news': '监管新闻'
  };

  const message = useMessage();
  const userStore = useUser(); // 使用user store
  const loading = ref(true);
  const rulesData = ref<MonitoringRule[]>([]);
  const selectedType = ref<string>('');
  const showDetailModal = ref(false);
  const selectedRule = ref<MonitoringRule | null>(null);

  // 活跃规则数量
  const activeRulesCount = computed(() => {
    return rulesData.value.filter(rule => rule.active !== false).length;
  });

  // 计算规则类型统计
  const ruleTypeStats = computed(() => {
    const stats = Object.entries(eventTypeConfig).map(([key, config]) => {
      const count = rulesData.value.filter(rule => rule.event_type === key).length;
      return {
        key,
        label: config.label,
        count,
        color: config.color,
        icon: config.icon
      };
    });
    return stats.filter(stat => stat.count > 0);
  });

  // 规则类型筛选选项
  const typeOptions = computed(() => {
    return Object.entries(eventTypeConfig).map(([value, config]) => ({
      label: config.label,
      value
    }));
  });

  // 过滤后的规则
  const filteredRules = computed(() => {
    if (!selectedType.value) return rulesData.value;
    return rulesData.value.filter(rule => rule.event_type === selectedType.value);
  });

  // 获取事件类型标签
  const getEventTypeLabel = (type: string) => {
    return eventTypeConfig[type as keyof typeof eventTypeConfig]?.label || type;
  };

  // 获取事件类型颜色
  const getEventTypeColor = (type: string) => {
    return eventTypeConfig[type as keyof typeof eventTypeConfig]?.color || '#6b7280';
  };

  // 获取事件子类型标签
  const getEventSubtypeLabel = (subtype: string) => {
    return eventSubtypeLabels[subtype] || subtype;
  };

  // 获取规则卡片样式类
  const getRuleCardClass = (type: string) => {
    return `rule-card-${type.toLowerCase()}`;
  };

  // 切换规则状态
  const toggleRuleStatus = (index: number) => {
    rulesData.value[index].active = !rulesData.value[index].active;
    message.success(rulesData.value[index].active ? '规则已启用' : '规则已停用');
  };

  // 查看规则详情
  const viewRuleDetails = (rule: MonitoringRule) => {
    selectedRule.value = rule;
    showDetailModal.value = true;
  };

  // 模拟数据（备用）
  const mockRulesData: MonitoringRule[] = [
    {
      "event_description": "平安银行股价出现异常下跌",
      "event_subtype": "price_fall_abnormal",
      "event_type": "Trading",
      "related_stock": "000001",
      "trigger_condition": "平安银行单日跌幅超过5%或连续三日累计跌幅超过8%",
      "active": true,
      "last_triggered": "2024-01-15 14:30:00",
      "trigger_count": 3,
      "created_at": "2024-01-01"
    },
    {
      "event_description": "中兴通讯股价突破关键均线",
      "event_subtype": "ma_break_up",
      "event_type": "Trading",
      "related_stock": "000063",
      "trigger_condition": "中兴通讯股价突破30日或60日移动平均线",
      "active": true,
      "last_triggered": "2024-01-14 10:15:00",
      "trigger_count": 2,
      "created_at": "2024-01-01"
    },
    {
      "event_description": "贵州茅台股价出现异常上涨",
      "event_subtype": "price_rise_abnormal",
      "event_type": "Trading",
      "related_stock": "600519",
      "trigger_condition": "贵州茅台单日涨幅超过4%或连续三日累计涨幅超过10%",
      "active": true,
      "last_triggered": "2024-01-12 11:20:00",
      "trigger_count": 1,
      "created_at": "2024-01-01"
    },
    {
      "event_description": "银行板块北向资金流入异常",
      "event_subtype": "northbound_inflow_abnormal",
      "event_type": "Capital",
      "related_stock": "银行",
      "trigger_condition": "银行板块北向资金单日净流入额创近一个月新高",
      "active": true,
      "last_triggered": "2024-01-10 15:00:00",
      "trigger_count": 4,
      "created_at": "2024-01-01"
    },
    {
      "event_description": "中国平安发布业绩预告",
      "event_subtype": "performance_forecast",
      "event_type": "Company",
      "related_stock": "601318",
      "trigger_condition": "中国平安发布季度或年度业绩预告公告",
      "active": true,
      "last_triggered": null,
      "trigger_count": 0,
      "created_at": "2024-01-01"
    },
    {
      "event_description": "海康威视财报数据发生重大变化",
      "event_subtype": "financial_report_change",
      "event_type": "Company",
      "related_stock": "002415",
      "trigger_condition": "海康威视发布的定期报告中，关键财务指标（如营收、净利润）同比或环比变化超过20%",
      "active": true,
      "last_triggered": "2024-01-08 09:00:00",
      "trigger_count": 1,
      "created_at": "2024-01-01"
    },
    {
      "event_description": "白酒行业出现一致性上涨",
      "event_subtype": "industry_consistency_rise",
      "event_type": "Industry",
      "related_stock": "白酒",
      "trigger_condition": "白酒行业指数连续三个交易日上涨，且行业内超过70%的个股上涨",
      "active": true,
      "last_triggered": "2024-01-07 14:45:00",
      "trigger_count": 2,
      "created_at": "2024-01-01"
    },
    {
      "event_description": "通信设备行业龙头出现大幅波动",
      "event_subtype": "industry_leader_fluctuation",
      "event_type": "Industry",
      "related_stock": "通信设备",
      "trigger_condition": "通信设备行业龙头股（如中兴通讯）单日涨跌幅超过行业指数涨跌幅3个百分点以上",
      "active": true,
      "last_triggered": null,
      "trigger_count": 0,
      "created_at": "2024-01-01"
    },
    {
      "event_description": "央行发布重要货币政策",
      "event_subtype": "macro_央行政策",
      "event_type": "Macro",
      "related_stock": "央行政策",
      "trigger_condition": "中国人民银行宣布调整存款准备金率、基准利率或发布重要货币政策报告",
      "active": true,
      "last_triggered": "2024-01-05 10:00:00",
      "trigger_count": 1,
      "created_at": "2024-01-01"
    },
    {
      "event_description": "金融监管部门发布重要监管政策",
      "event_subtype": "macro_金融监管",
      "event_type": "Macro",
      "related_stock": "金融监管",
      "trigger_condition": "国家金融监督管理总局等机构发布针对银行、保险等金融行业的重大监管政策或指导意见",
      "active": true,
      "last_triggered": null,
      "trigger_count": 0,
      "created_at": "2024-01-01"
    },
    {
      "event_description": "银行板块市场关注度激增",
      "event_subtype": "attention_surge",
      "event_type": "Sentiment",
      "related_stock": "银行",
      "trigger_condition": "银行板块在主流财经平台搜索量或讨论热度单日环比增长超过100%",
      "active": true,
      "last_triggered": "2024-01-03 16:30:00",
      "trigger_count": 3,
      "created_at": "2024-01-01"
    },
    {
      "event_description": "中兴通讯进入热门股票榜单前十",
      "event_subtype": "hot_list_top10",
      "event_type": "Sentiment",
      "related_stock": "000063",
      "trigger_condition": "中兴通讯进入主流交易软件或财经媒体热门股票榜单前十名",
      "active": true,
      "last_triggered": "2024-01-02 13:15:00",
      "trigger_count": 2,
      "created_at": "2024-01-01"
    },
    {
      "event_description": "中国平安出现重大正面新闻",
      "event_subtype": "positive_news",
      "event_type": "News",
      "related_stock": "601318",
      "trigger_condition": "权威媒体发布关于中国平安寿险改革取得突破、业绩超预期或获得重大合同等正面报道",
      "active": true,
      "last_triggered": null,
      "trigger_count": 0,
      "created_at": "2024-01-01"
    },
    {
      "event_description": "海康威视出现重大负面新闻",
      "event_subtype": "negative_news",
      "event_type": "News",
      "related_stock": "002415",
      "trigger_condition": "权威媒体发布关于海康威视涉及重大诉讼、监管处罚、核心业务受阻或业绩不及预期等负面报道",
      "active": true,
      "last_triggered": "2024-01-06 11:00:00",
      "trigger_count": 1,
      "created_at": "2024-01-01"
    },
    {
      "event_description": "银行板块出现重要监管新闻",
      "event_subtype": "regulatory_news",
      "event_type": "News",
      "related_stock": "银行",
      "trigger_condition": "权威媒体发布关于银行业（如房地产贷款政策、利率政策、资本监管等）的重大监管动态新闻",
      "active": true,
      "last_triggered": "2024-01-04 15:30:00",
      "trigger_count": 2,
      "created_at": "2024-01-01"
    }
  ];

  // 获取规则数据
  const fetchRules = async () => {
    loading.value = true;
    
    try {
      // 获取用户的token
      const token = userStore.getToken;

      if (!token) {
        // 如果没有token，可能是用户未登录
        throw new Error('用户未登录或token已失效');
      }

      // 调用API获取规则数据，API会自动添加Authorization头部
      const response = await getRule(token);

      if (response && response.code === 0 && response.data) {
        // API调用成功，处理数据
        const processedData = response.data.map((item: any): MonitoringRule => ({
          event_description: item.event_description || '',
          event_subtype: item.event_subtype || '',
          event_type: item.event_type || '',
          related_stock: item.related_stock || '',
          trigger_condition: item.trigger_condition || '',
          active: true, // 默认启用
          last_triggered: null,
          trigger_count: 0,
          created_at: new Date().toLocaleDateString()
        }));
        
        rulesData.value = processedData;
        message.success('规则数据加载成功');
      } else {
        // API返回数据格式不正确，使用模拟数据
        console.warn('API返回数据格式不正确，使用模拟数据');
        rulesData.value = mockRulesData;
        message.info('使用模拟数据展示');
      }
    } catch (error) {
      // API调用失败，使用模拟数据
      console.error('获取规则数据失败:', error);

      // 根据错误类型显示不同的提示信息
      if (error.message === '用户未登录或token已失效') {
        message.error('请先登录系统');
        // 这里可以跳转到登录页
        // router.push('/login');
      } else {
        message.warning('网络异常，使用模拟数据展示');
      }

      rulesData.value = mockRulesData;
    } finally {
      loading.value = false;
    }
  };

  onMounted(() => {
    fetchRules();
  });
</script>

<style scoped lang="scss">
.monitoring-rules-container {
  min-height: 100vh;
  padding: 24px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.rules-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(226, 232, 240, 0.8);
  overflow: hidden;
  transition: all 0.3s ease;

  &:hover {
    box-shadow: 0 12px 48px rgba(0, 0, 0, 0.12);
  }
}

.rules-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px 28px;
  border-bottom: 1px solid #eef1f4;
  background: linear-gradient(to right, #f8fafc, #ffffff);

  .header-title {
    .title-text {
      margin: 0;
      font-size: 24px;
      font-weight: 700;
      color: #1e293b;
      letter-spacing: -0.5px;
    }

    .title-subtext {
      margin: 6px 0 0;
      font-size: 14px;
      color: #64748b;
      opacity: 0.8;
    }
  }

  .header-stats {
    .statistic-item {
      padding: 0 20px;
      border-right: 1px solid #eef1f4;

      &:last-child {
        border-right: none;
      }
    }
  }
}

.rules-summary {
  padding: 20px 28px;
  border-bottom: 1px solid #eef1f4;

  .summary-card {
    border-radius: 12px;
    min-width: 180px;
    transition: all 0.3s ease;

    &:hover {
      transform: translateY(-2px);
    }

    .summary-card-content {
      display: flex;
      align-items: center;
      gap: 16px;

      .summary-icon {
        width: 48px;
        height: 48px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 12px;
        transition: all 0.3s ease;
      }

      .summary-info {
        .summary-count {
          font-size: 24px;
          font-weight: 700;
          color: #1e293b;
          line-height: 1;
        }

        .summary-label {
          font-size: 14px;
          color: #64748b;
          margin-top: 4px;
        }
      }
    }
  }
}

.rules-list {
  padding: 24px 28px;

  .list-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;

    .list-title {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
      color: #1e293b;
    }
  }

  // 加载状态样式
  .loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 300px;
    gap: 16px;

    .loading-text {
      color: #64748b;
      font-size: 14px;
    }
  }

  .rules-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
    gap: 20px;
  }
}

.rule-card {
  border-radius: 12px;
  border: 1px solid #eef1f4;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(to right, var(--type-color), var(--type-color-light));
    opacity: 0.8;
  }

  &.rule-card-trading::before {
    --type-color: #3b82f6;
    --type-color-light: #93c5fd;
  }

  &.rule-card-capital::before {
    --type-color: #10b981;
    --type-color-light: #6ee7b7;
  }

  &.rule-card-company::before {
    --type-color: #f59e0b;
    --type-color-light: #fcd34d;
  }

  &.rule-card-industry::before {
    --type-color: #8b5cf6;
    --type-color-light: #c4b5fd;
  }

  &.rule-card-macro::before {
    --type-color: #ef4444;
    --type-color-light: #fca5a5;
  }

  &.rule-card-sentiment::before {
    --type-color: #ec4899;
    --type-color-light: #f9a8d4;
  }

  &.rule-card-news::before {
    --type-color: #14b8a6;
    --type-color-light: #5eead4;
  }

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.12);
    border-color: transparent;

    &::before {
      opacity: 1;
    }
  }

  .rule-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px 12px;
    border-bottom: 1px solid #f1f5f9;

    .rule-type-badge {
      display: flex;
      align-items: center;
      gap: 8px;
    }
  }

  .rule-card-body {
    padding: 20px;

    .rule-title {
      margin: 0 0 16px;
      font-size: 16px;
      font-weight: 600;
      color: #1e293b;
      line-height: 1.4;
    }

    .rule-details {
      margin-bottom: 20px;

      .detail-item {
        display: flex;
        align-items: flex-start;
        margin-bottom: 12px;
        font-size: 14px;

        .detail-icon {
          margin-right: 10px;
          color: #64748b;
          flex-shrink: 0;
          margin-top: 2px;
        }

        .detail-label {
          color: #64748b;
          font-weight: 500;
          white-space: nowrap;
        }

        .detail-value {
          color: #1e293b;
          margin-left: 4px;
          flex: 1;
          line-height: 1.5;
        }
      }
    }

    .rule-progress {
      .progress-info {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
        font-size: 13px;
        color: #64748b;
      }
    }
  }

  .rule-card-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    background: #f8fafc;
    border-top: 1px solid #f1f5f9;

    .rule-status {
      .status-text {
        font-size: 13px;
        font-weight: 500;
        color: #64748b;
      }
    }
  }
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
  background: #f8fafc;
  border-radius: 12px;
  border: 2px dashed #e2e8f0;
}

// 规则详情模态框样式
.rule-detail {
  .detail-header {
    margin-bottom: 24px;

    .detail-type-badge {
      display: flex;
      gap: 8px;
      margin-bottom: 12px;
    }

    .detail-title {
      margin: 0;
      font-size: 20px;
      font-weight: 600;
      color: #1e293b;
      line-height: 1.4;
    }
  }

  .detail-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;

    .detail-item {
      .detail-item-label {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
        font-size: 14px;
        font-weight: 500;
        color: #64748b;

        .n-icon {
          color: #94a3b8;
        }
      }

      .detail-item-value {
        font-size: 15px;
        color: #1e293b;
        line-height: 1.5;
      }
    }
  }
}

@media (max-width: 768px) {
  .monitoring-rules-container {
    padding: 16px;
  }

  .rules-header {
    flex-direction: column;
    align-items: stretch;
    gap: 16px;
    padding: 20px;

    .header-stats {
      display: flex;
      justify-content: space-between;
    }
  }

  .rules-summary {
    padding: 16px;

    :deep(.n-space) {
      flex-wrap: wrap !important;
    }

    .summary-card {
      min-width: calc(50% - 12px);
    }
  }

  .rules-list {
    padding: 16px;

    .list-header {
      flex-direction: column;
      align-items: stretch;
      gap: 16px;
    }

    .rules-grid {
      grid-template-columns: 1fr;
    }
  }

  .rule-card {
    margin-bottom: 16px;
  }
}

@media (max-width: 480px) {
  .monitoring-rules-container {
    padding: 12px;
  }

  .rules-card {
    border-radius: 12px;
  }

  .summary-card {
    min-width: 100% !important;
  }
}
</style>
