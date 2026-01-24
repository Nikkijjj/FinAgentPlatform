<script setup lang="ts">
  import { onMounted, ref, computed, h } from 'vue';
  import { fetchAllEvents } from '@/api/message/message';
  import {
    useMessage,
    NTag,
    NIcon,
    NStatistic,
    NModal,
    NText,
    NDescriptions,
    NDescriptionsItem,
    NEllipsis,
    NSpace,
    NTime,
    NButton,
    NCard,
  } from 'naive-ui';
  import { DataTableColumns } from 'naive-ui';
  import {
    ArrowUpOutline,
    TimeOutline,
    AnalyticsOutline,
    BusinessOutline,
    SearchOutline,
  } from '@vicons/ionicons5';
  import { parseStr } from '@/api/time';

  const message = useMessage();

  // 所有事件数据响应式引用
  const allEvents = ref<any[]>([]);

  // 分页相关状态
  const paginationParams = ref({
    page: 1,
    size: 10,
    total: 0,
  });

  // 加载状态
  const loading = ref(true);

  // 筛选面板展开/折叠状态
  const searchExpanded = ref(false);

  // 筛选面板相关数据
  const search_stock_code = ref<string>('');
  const search_event_type = ref<string | null>(null);
  const search_keyword = ref<string>('');
  const search_time_range = ref<[number, number] | null>(null);

  // 详情对话框控制
  const detailModalVisible = ref(false);
  const currentDetail = ref<any>(null);

  // 调试：打印数据中的事件类型分布
  function logEventTypeDistribution(events: any[]) {
    const typeCount: Record<string, number> = {};
    events.forEach((event, index) => {
      const type = getEventType(event);
      typeCount[type] = (typeCount[type] || 0) + 1;

      // 前几条数据的详细日志
      if (index < 3) {
        console.log(`数据${index + 1}:`, {
          event_type: event.event_type,
          type: getEventType(event),
          raw_keys: Object.keys(event).filter((k) => k.includes('type') || k.includes('Type')),
          data: event,
        });
      }
    });
    console.log('事件类型分布:', typeCount);
  }

  // 统一获取事件类型的函数
  function getEventType(event: any): string {
    // 尝试多种可能的字段名
    if (event.event_type) return event.event_type;
    if (event.type) return event.type;
    if (event.eventType) return event.eventType;
    if (event['事件类型']) return event['事件类型'];
    if (event.category) return event.category;

    // 如果没有明确的类型字段，根据其他字段推断
    if (
      event.board_name ||
      event.event_subtype?.includes('price') ||
      event.event_subtype?.includes('leader')
    ) {
      return 'industry';
    }
    if (event['标题'] || event['内容']) {
      return 'trading';
    }
    if (event.raw_data?.新闻内容 || event.event_subtype?.includes('macro')) {
      return 'macro';
    }
    if (event.event_subtype?.includes('ma') || event.event_subtype?.includes('cross')) {
      return 'sentiment';
    }

    return 'unknown';
  }

  // 加载数据函数
  async function loadData(page = 1) {
    try {
      loading.value = true;
      // 2026.01.23
      // 补充筛选条件： stock_code, keyword, start_time, end_time, event_type
      const response = await fetchAllEvents({
        stock_code: search_stock_code.value === '' ? undefined : search_stock_code.value,
        keyword: search_keyword.value === '' ? undefined : search_keyword.value,
        start_time: search_time_range.value ? parseStr(search_time_range.value[0]) : undefined,
        end_time: search_time_range.value ? parseStr(search_time_range.value[1]) : undefined,
        event_type: search_event_type.value ? search_event_type.value : undefined,
        sort_field: 'event_time',
        sort_order: -1,
        page: page,
        size: paginationParams.value.size,
      });

      if (response.code === 0) {
        const data = response.data;
        console.log('API响应数据:', data);

        // 根据不同接口结构获取数据
        let events: any[] = [];
        let total = 0;

        if (data && data.messages) {
          events = Array.isArray(data.messages) ? data.messages : [];
          total = data.total || data.count || data.messages.length;
        } else if (Array.isArray(data)) {
          events = data;
          total = data.length;
        } else if (data && data.data) {
          events = Array.isArray(data.data) ? data.data : [];
          total = data.total || data.count || data.data.length;
        } else if (data && data.list) {
          events = Array.isArray(data.list) ? data.list : [];
          total = data.total || data.count || data.list.length;
        } else if (data && typeof data === 'object') {
          const arrayKeys = Object.keys(data).filter((key) => Array.isArray(data[key]));
          if (arrayKeys.length > 0) {
            events = data[arrayKeys[0]];
            total = data.total || data.count || data[arrayKeys[0]].length;
          }
        }

        // 确保每个事件都有正确的 event_type 字段
        events = events.map((event) => {
          const eventType = getEventType(event);
          return {
            ...event,
            // 确保有一个统一的 event_type 字段供表格使用
            _event_type: eventType,
          };
        });

        allEvents.value = events;
        paginationParams.value.total = total;
        paginationParams.value.page = page;

        // 打印事件类型分布用于调试
        logEventTypeDistribution(events);

        console.log(`加载第${page}页数据，共${total}条，当前页${events.length}条`);

        if (events.length === 0) {
          message.warning('暂无数据');
        } else {
          message.success(`已加载第${page}页数据`);
        }
      } else {
        message.error(`数据获取失败: ${response.msg}`);
        allEvents.value = [];
        paginationParams.value.total = 0;
      }
    } catch (error) {
      message.error('数据加载失败');
      console.error('数据加载失败:', error);
      allEvents.value = [];
      paginationParams.value.total = 0;
    } finally {
      loading.value = false;
    }
  }

  // 在onMounted中调用
  onMounted(async () => {
    await loadData(1);
  });

  // 查看详情
  const showDetail = (item: any) => {
    currentDetail.value = item;
    detailModalVisible.value = true;
  };

  // 格式化时间的函数
  function formatDateTime(dateString: string) {
    if (!dateString) return '-';
    try {
      const date = new Date(dateString);
      return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      });
    } catch (e) {
      return dateString;
    }
  }

  // 格式化事件类型
  function formatEventType(type: string) {
    const typeMap: Record<string, string> = {
      macro: '宏观',
      industry: '行业',
      sentiment: '情绪',
      trading: '个股',
    };
    return typeMap[type] || type;
  }

  // 格式化事件子类型
  function formatEventSubtype(subtype: string) {
    const subtypeMap: Record<string, string> = {
      macro_综合宏观新闻: '综合宏观',
      macro_资本市场: '资本市场',
      macro_央行政策: '央行政策',
      macro_金融监管: '金融监管',
      macro_经济增长: '经济增长',
      macro_国际局势: '国际局势',
      price_rise_abnormal: '涨幅异常',
      price_fall_abnormal: '跌幅异常',
      rise_consistency_abnormal: '上涨一致',
      fall_consistency_abnormal: '下跌一致',
      leader_fluctuation_abnormal: '龙头异动',
      ma5_cross_up: 'MA5上穿',
      ma5_cross_down: 'MA5下穿',
      ma10_cross_up: 'MA10上穿',
      ma10_cross_down: 'MA10下穿',
      ma20_cross_up: 'MA20上穿',
      ma20_cross_down: 'MA20下穿',
      ma60_cross_up: 'MA60上穿',
      ma60_cross_down: 'MA60下穿',
    };
    return subtypeMap[subtype] || subtype?.replace('macro_', '') || subtype || '-';
  }

  // 格式化影响级别
  function formatImpactLevel(level: string) {
    const levelMap: Record<string, string> = {
      critical: '极高',
      high: '高',
      medium: '中',
      low: '低',
    };
    return levelMap[level] || level || '中';
  }

  // 格式化情绪
  function formatSentiment(sentiment: string) {
    const sentimentMap: Record<string, string> = {
      positive: '正面',
      negative: '负面',
      neutral: '中性',
    };
    return sentimentMap[sentiment] || sentiment || '中性';
  }

  // 获取事件摘要
  function getEventSummary(item: any): string {
    const eventType = item.event_type;
    const rawData = item.raw_data || {};

    switch (eventType) {
      case 'macro':
        return item.event_description || rawData.新闻内容?.substring(0, 100) + '...' || '宏观事件';

      case 'industry':
        const boardName = item.board_name || item.symbol || '';
        switch (item.event_subtype) {
          case 'price_rise_abnormal':
            return `${boardName}板块涨幅异常，上涨${rawData.price_change?.toFixed(2) || '0.00'}%`;
          case 'price_fall_abnormal':
            return `${boardName}板块跌幅异常，下跌${Math.abs(rawData.price_change || 0).toFixed(
              2
            )}%`;
          case 'leader_fluctuation_abnormal':
            return `${boardName}板块龙头异动`;
          case 'rise_consistency_abnormal':
            return `${boardName}板块上涨一致性异常`;
          case 'fall_consistency_abnormal':
            return `${boardName}板块下跌一致性异常`;
          default:
            return `${boardName}板块异常波动`;
        }

      case 'sentiment':
        const symbol = item.symbol || '';
        switch (item.event_subtype) {
          case 'ma5_cross_up':
          case 'ma5_cross_down':
          case 'ma10_cross_up':
          case 'ma10_cross_down':
          case 'ma20_cross_up':
          case 'ma20_cross_down':
          case 'ma60_cross_up':
          case 'ma60_cross_down':
            return `${symbol}均线${item.event_subtype.includes('up') ? '上穿' : '下穿'}`;
          default:
            return `${symbol}技术指标异常`;
        }

      case 'trading':
        return item.event_description || item['标题']?.substring(0, 100) + '...' || '个股新闻';

      default:
        return item.event_description || '事件';
    }
  }

  // 所有事件数据列定义
  const columns_all: DataTableColumns<any> = [
    {
      title: '事件类型',
      key: 'event_type',
      width: 100,
      fixed: 'left',
      align: 'center',
      render(row) {
        const type = row.event_type;
        const typeConfig: Record<string, any> = {
          macro: { text: '宏观', color: '#1890ff', bgColor: '#e6f7ff' },
          industry: { text: '行业', color: '#52c41a', bgColor: '#f6ffed' },
          trading: { text: '个股', color: '#722ed1', bgColor: '#f9f0ff' },
          sentiment: { text: '情绪', color: '#fa8c16', bgColor: '#fff7e6' },
        };
        const config = typeConfig[type] || { text: type, color: '#666', bgColor: '#f5f5f5' };

        return h(
          NTag,
          {
            size: 'small',
            type: 'default',
            style: {
              background: config.bgColor,
              color: config.color,
              borderColor: config.color + '30',
              fontWeight: '500',
            },
          },
          {
            default: () => config.text,
          }
        );
      },
    },
    {
      title: '事件时间',
      key: 'event_time',
      width: 120,
      align: 'center',
      sorter: (a, b) => {
        const timeA = a.event_time ? new Date(a.event_time).getTime() : 0;
        const timeB = b.event_time ? new Date(b.event_time).getTime() : 0;
        return timeA - timeB;
      },
      render(row) {
        return h('div', { class: 'event-time-cell' }, [
          h(
            NIcon,
            { size: '14', style: { marginRight: '4px', color: '#1890ff' } },
            { default: () => h(TimeOutline) }
          ),
          h('span', formatDateTime(row.event_time || row['发布时间'])),
        ]);
      },
    },
    {
      title: '事件摘要',
      key: 'summary',
      width: 300,
      align: 'center',
      ellipsis: {
        tooltip: true,
      },
      render(row) {
        const summary = getEventSummary(row);
        return h('div', { class: 'description-preview' }, [
          h(
            NEllipsis,
            { tooltip: false, lineClamp: 3 },
            {
              default: () => summary,
            }
          ),
        ]);
      },
    },
    {
      title: '事件子类',
      key: 'event_subtype',
      width: 120,
      align: 'center',
      render(row) {
        const subtype = formatEventSubtype(row.event_subtype);
        return h(
          'span',
          {
            style: {
              fontSize: '12px',
              padding: '2px 6px',
              background: '#f0f0f0',
              borderRadius: '3px',
            },
          },
          subtype
        );
      },
    },
    {
      title: '影响级别',
      key: 'impact_level',
      width: 80,
      align: 'center',
      render(row) {
        const level = row.impact_level || 'medium';
        const levelMap: Record<string, any> = {
          critical: { text: '极高', class: 'level-critical', color: '#ff4d4f' },
          high: { text: '高', class: 'level-high', color: '#fa541c' },
          medium: { text: '中', class: 'level-medium', color: '#fa8c16' },
          low: { text: '低', class: 'level-low', color: '#d9d9d9' },
        };
        const config = levelMap[level] || {
          text: formatImpactLevel(level),
          class: '',
          color: '#666',
        };

        return h(
          'div',
          {
            class: `impact-level ${config.class}`,
            style: {
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '2px 8px',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: '600',
              background: config.color + '10',
              color: config.color,
              border: `1px solid ${config.color}30`,
            },
          },
          config.text
        );
      },
    },
    {
      title: '情感',
      key: 'sentiment',
      width: 80,
      align: 'center',
      render(row) {
        let sentiment = row.sentiment || 'neutral';
        // 如果没有sentiment字段，根据事件类型推断
        if (!row.sentiment) {
          if (row.event_type === 'industry' && row.event_subtype?.includes('rise')) {
            sentiment = 'positive';
          } else if (row.event_type === 'industry' && row.event_subtype?.includes('fall')) {
            sentiment = 'negative';
          }
        }

        const sentimentMap: Record<string, any> = {
          positive: { text: '正面', class: 'sentiment-positive', color: '#52c41a' },
          negative: { text: '负面', class: 'sentiment-negative', color: '#ff4d4f' },
          neutral: { text: '中性', class: 'sentiment-neutral', color: '#666' },
        };
        const config = sentimentMap[sentiment] || {
          text: formatSentiment(sentiment),
          class: '',
          color: '#666',
        };

        return h(
          'div',
          {
            class: `sentiment ${config.class}`,
            style: {
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '2px 8px',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: '600',
              background: config.color + '10',
              color: config.color,
              border: `1px solid ${config.color}30`,
            },
          },
          config.text
        );
      },
    },
    {
      title: '相关标的',
      key: 'symbol',
      width: 120,
      align: 'center',
      render(row) {
        let symbol = row.symbol || '-';

        // 对于个股类型，尝试从标题中提取股票代码
        if (row.event_type === 'stock' && !symbol && row['标题']) {
          const symbolMatch = row['标题'].match(/[0-9]{6}/);
          if (symbolMatch) {
            symbol = symbolMatch[0];
          }
        }

        // 对于行业类型，使用板块名称
        if (row.event_type === 'industry' && row.board_name) {
          symbol = row.board_name;
        }

        return h('div', { class: 'symbol-cell' }, [
          h(
            NIcon,
            { size: '14', style: { marginRight: '4px', color: '#165dff' } },
            { default: () => h(BusinessOutline) }
          ),
          h(
            'span',
            {
              class: 'symbol-text',
              style: {
                fontFamily: "'SFMono-Regular', Consolas, monospace",
                fontSize: '12px',
                fontWeight: '500',
                padding: '2px 6px',
                background: 'rgba(22, 93, 255, 0.05)',
                borderRadius: '3px',
                color: '#165dff',
                border: '1px solid rgba(22, 93, 255, 0.1)',
              },
            },
            symbol
          ),
        ]);
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      fixed: 'right',
      align: 'center',
      render(row) {
        return h(
          NButton,
          {
            size: 'small',
            type: 'primary',
            onClick: () => showDetail(row),
          },
          {
            default: () => '详情',
          }
        );
      },
    },
  ];

  // 分页配置 - 使用computed动态计算
  const pagination = computed(() => {
    const pageCount = Math.ceil(paginationParams.value.total / paginationParams.value.size);

    return {
      page: paginationParams.value.page,
      pageSize: paginationParams.value.size,
      pageCount: pageCount,
      showSizePicker: true,
      pageSizes: [10, 20, 50, 100, 200],
      showQuickJumper: true,
      onChange: (page: number) => {
        console.log('切换页面:', page);
        loadData(page);
      },
      onUpdatePageSize: (size: number) => {
        console.log('更新页面大小:', size);
        paginationParams.value.size = size;
        loadData(1); // 切换每页条数时回到第一页
      },
    };
  });

  // 格式化行业事件详细描述
  function formatIndustryEventDetail(item: any) {
    const boardName = item.board_name || item.symbol || '';
    const rawData = item.raw_data || {};

    switch (item.event_subtype) {
      case 'price_rise_abnormal':
        return `${boardName}板块出现异常上涨：
          涨幅：${rawData.price_change?.toFixed(2) || '0.00'}%
          成交额：${rawData.total_amount ? (rawData.total_amount / 10000).toFixed(1) : '0.0'}亿元
          上涨家数：${rawData.rise_stocks || 0}/${rawData.total_stocks || 0}`;

      case 'price_fall_abnormal':
        return `${boardName}板块出现异常下跌：
          跌幅：${Math.abs(rawData.price_change || 0).toFixed(2)}%
          领跌股：${rawData.leader_stock || '-'}
          领跌股跌幅：${Math.abs(rawData.leader_change || 0).toFixed(2)}%`;

      case 'leader_fluctuation_abnormal':
        return `${boardName}板块龙头股异动：
          龙头股：${rawData.leader_stock || '-'}
          涨跌幅：${rawData.leader_change?.toFixed(2) || '0.00'}%
          成交量：${
            rawData.leader_volume ? (rawData.leader_volume / 10000).toFixed(1) : '0.0'
          }万手`;

      case 'rise_consistency_abnormal':
        return `${boardName}板块上涨一致性异常：
          上涨家数：${rawData.rise_stocks || 0}/${rawData.total_stocks || 0}
          上涨占比：${
            rawData.rise_stocks && rawData.total_stocks
              ? ((rawData.rise_stocks / rawData.total_stocks) * 100).toFixed(1)
              : '0.0'
          }%
          平均涨幅：${rawData.average_rise?.toFixed(2) || '0.00'}%`;

      case 'fall_consistency_abnormal':
        return `${boardName}板块下跌一致性异常：
          净流出：${
            rawData.net_inflow ? Math.abs(rawData.net_inflow / 10000).toFixed(1) : '0.0'
          }亿元
          下跌家数占比：${rawData.fall_ratio?.toFixed(1) || '0.0'}%
          平均跌幅：${Math.abs(rawData.average_fall || 0).toFixed(2)}%`;

      default:
        return `${boardName}板块出现异常波动`;
    }
  }

  // 格式化情绪事件详细描述
  function formatMoodEventDetail(item: any) {
    const rawData = item.raw_data || {};
    const symbol = item.symbol || '';
    const subtype = item.event_subtype || '';

    switch (subtype) {
      case 'ma5_cross_up':
      case 'ma5_cross_down':
        return `${symbol} MA5均线交叉：
          当前价格：${rawData.real_time_close?.toFixed(2) || '0.00'}元
          MA5均线：${rawData.daily_MA5?.toFixed(2) || '0.00'}元
          偏离度：${Math.abs(rawData.deviation_pct || 0).toFixed(2)}%
          方向：${subtype.includes('up') ? '上穿' : '下穿'}`;

      case 'ma10_cross_up':
      case 'ma10_cross_down':
        return `${symbol} MA10均线交叉：
          当前价格：${rawData.real_time_close?.toFixed(2) || '0.00'}元
          MA10均线：${rawData.daily_MA10?.toFixed(2) || '0.00'}元
          偏离度：${Math.abs(rawData.deviation_pct || 0).toFixed(2)}%
          方向：${subtype.includes('up') ? '上穿' : '下穿'}`;

      case 'ma20_cross_up':
      case 'ma20_cross_down':
        return `${symbol} MA20均线交叉：
          当前价格：${rawData.real_time_close?.toFixed(2) || '0.00'}元
          MA20均线：${rawData.daily_MA20?.toFixed(2) || '0.00'}元
          偏离度：${Math.abs(rawData.deviation_pct || 0).toFixed(2)}%
          方向：${subtype.includes('up') ? '上穿' : '下穿'}`;

      case 'ma60_cross_up':
      case 'ma60_cross_down':
        return `${symbol} MA60均线交叉：
          当前价格：${rawData.real_time_close?.toFixed(2) || '0.00'}元
          MA60均线：${rawData.daily_MA60?.toFixed(2) || '0.00'}元
          偏离度：${Math.abs(rawData.deviation_pct || 0).toFixed(2)}%
          方向：${subtype.includes('up') ? '上穿' : '下穿'}`;

      default:
        return `${symbol} 技术指标异常：
          当前价格：${rawData.real_time_close?.toFixed(2) || '0.00'}元`;
    }
  }

  // 展开筛选面板
  function toggleSearch() {
    searchExpanded.value = !searchExpanded.value;
  }

  // 重置筛选面板
  function resetSearch() {
    search_stock_code.value = '';
    search_keyword.value = '';
    search_event_type.value = null;
    search_time_range.value = null;
  }

  // 提交筛选数据
  function submitSearch() {
    loadData(1);
  }
</script>

<template>
  <n-card class="large-card">
    <div class="container">
      <!-- 标题栏 -->
      <div class="header">
        <h2 style="margin: 0; color: #333; font-weight: 600">事件总览</h2>
        <n-space>
          <n-statistic label="事件总数" :value="paginationParams.total">
            <template #prefix>
              <n-icon :component="AnalyticsOutline" />
            </template>
          </n-statistic>
        </n-space>
      </div>

      <!-- 筛选框 -->
      <n-card class="filter">
        <n-flex v-if="searchExpanded" vertical justify="center">
          <n-flex justify="space-around">
            <n-flex inline :wrap="false" :style="{ width: '30%' }" align="center">
              <n-text :style="{ width: '20%' }">股票代码</n-text>
              <n-input placeholder="查询股票代码" v-model:value="search_stock_code" clearable />
            </n-flex>
            <n-flex inline :wrap="false" :style="{ width: '30%' }" align="center">
              <n-text :style="{ width: '20%' }">关键字</n-text>
              <n-input placeholder="查询关键字" v-model:value="search_keyword" clearable />
            </n-flex>
          </n-flex>
          <n-flex justify="space-around">
            <n-flex inline :wrap="false" :style="{ width: '30%' }" align="center">
              <n-text :style="{ width: '20%' }">事件类型</n-text>
              <n-select
                clearable
                placeholder="指定事件类型"
                :options="[
                  { label: '宏观', value: 'macro' },
                  { label: '行业', value: 'industry' },
                  { label: '个股', value: 'trading' },
                  { label: '情绪', value: 'sentiment' },
                ]"
                v-model:value="search_event_type"
              />
            </n-flex>
            <n-flex inline :wrap="false" :style="{ width: '30%' }" align="center">
              <n-text :style="{ width: '20%' }">时间范围</n-text>
              <n-date-picker type="datetimerange" v-model:value="search_time_range" clearable />
            </n-flex>
          </n-flex>
        </n-flex>
        <template #action>
          <n-collapse-transition :show="searchExpanded">
            <n-flex align="center" justify="end">
              <n-button class="search-button" size="large" @click="submitSearch">查询</n-button>
              <n-button size="large" @click="resetSearch">重置</n-button>
              <n-button text @click="toggleSearch">收起面板</n-button>
            </n-flex>
          </n-collapse-transition>
          <n-collapse-transition :show="!searchExpanded">
            <n-flex align="center" @click="toggleSearch">
              <n-icon :component="SearchOutline" />
              <n-text :style="{ color: 'lightgray' }">点击此处展开筛选...</n-text>
            </n-flex>
          </n-collapse-transition>
        </template>
      </n-card>

      <!-- 所有事件表格 -->
      <n-data-table
        :columns="columns_all"
        :data="allEvents"
        :bordered="false"
        :single-line="false"
        max-height="600px"
        :loading="loading"
        class="all-events-table"
        :row-props="
          (row) => ({
            style: {
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            },
            onMouseenter: (e) => {
              e.currentTarget.style.backgroundColor = '#fafafa';
            },
            onMouseleave: (e) => {
              e.currentTarget.style.backgroundColor = '';
            },
            onClick: () => showDetail(row),
          })
        "
      />

      <!-- 快速翻页按钮 - 移到表格下方 -->
      <div v-if="paginationParams.total > 0" class="pagination-container">
        <n-space justify="center" align="center" class="pagination-wrapper">
          <n-button
            :disabled="paginationParams.page === 1"
            @click="loadData(1)"
            size="small"
            type="tertiary"
            secondary
          >
            首页
          </n-button>
          <n-button
            :disabled="paginationParams.page === 1"
            @click="loadData(paginationParams.page - 1)"
            size="small"
            secondary
          >
            <template #icon>
              <n-icon><ArrowUpOutline /></n-icon>
            </template>
            上一页
          </n-button>
          <span class="page-info">
            第 {{ paginationParams.page }} 页 / 共
            {{ Math.ceil(paginationParams.total / paginationParams.size) }} 页
          </span>
          <n-button
            :disabled="
              paginationParams.page >= Math.ceil(paginationParams.total / paginationParams.size)
            "
            @click="loadData(paginationParams.page + 1)"
            size="small"
            secondary
          >
            下一页
            <template #icon>
              <n-icon><ArrowUpOutline style="transform: rotate(180deg)" /></n-icon>
            </template>
          </n-button>
          <n-button
            @click="loadData(Math.ceil(paginationParams.total / paginationParams.size))"
            size="small"
            type="tertiary"
            secondary
          >
            末页
          </n-button>
        </n-space>
      </div>
    </div>
  </n-card>

  <!-- 事件详情对话框 -->
  <n-modal
    v-model:show="detailModalVisible"
    preset="card"
    :title="currentDetail ? formatEventType(currentDetail.event_type) + '事件详情' : '事件详情'"
    style="width: 700px; max-width: 90vw"
    :bordered="false"
  >
    <div v-if="currentDetail" class="detail-content">
      <n-descriptions
        label-placement="left"
        :column="1"
        size="small"
        bordered
        :label-style="{
          width: '100px',
          minWidth: '100px',
          fontWeight: '500',
          textAlign: 'right',
        }"
        :content-style="{
          maxWidth: '500px',
        }"
      >
        <!-- 基本信息 -->
        <n-descriptions-item label="事件类型">
          <n-tag
            :type="
              currentDetail.event_type === 'macro'
                ? 'info'
                : currentDetail.event_type === 'industry'
                ? 'success'
                : currentDetail.event_type === 'stock'
                ? 'warning'
                : 'error'
            "
          >
            {{ formatEventType(currentDetail.event_type) }}
          </n-tag>
        </n-descriptions-item>

        <n-descriptions-item label="事件子类">
          <n-text>{{ formatEventSubtype(currentDetail.event_subtype) }}</n-text>
        </n-descriptions-item>

        <n-descriptions-item label="发布时间">
          <n-text>
            <n-time
              v-if="currentDetail.event_time"
              :time="new Date(currentDetail.event_time)"
              type="datetime"
            />
            <span v-else-if="currentDetail['发布时间']">{{ currentDetail['发布时间'] }}</span>
            <span v-else>-</span>
          </n-text>
        </n-descriptions-item>

        <!-- 事件描述 -->
        <n-descriptions-item label="事件描述">
          <div style="padding: 8px; background: #f8f9fa; border-radius: 4px">
            <n-text style="white-space: pre-wrap; line-height: 1.6; font-size: 13px">
              {{
                currentDetail.event_type === 'industry'
                  ? formatIndustryEventDetail(currentDetail)
                  : currentDetail.event_type === 'mood'
                  ? formatMoodEventDetail(currentDetail)
                  : currentDetail.event_type === 'stock'
                  ? currentDetail['标题'] || currentDetail.event_description
                  : currentDetail.event_description || currentDetail.raw_data?.新闻内容 || '-'
              }}
            </n-text>
          </div>
        </n-descriptions-item>

        <!-- 详细内容 -->
        <n-descriptions-item
          v-if="currentDetail.event_type === 'stock' && currentDetail['内容']"
          label="完整内容"
        >
          <div
            style="
              max-height: 200px;
              overflow-y: auto;
              padding: 8px;
              background: #f8f9fa;
              border-radius: 4px;
            "
          >
            <n-text style="white-space: pre-wrap; line-height: 1.6; font-size: 13px">
              {{ currentDetail['内容'] }}
            </n-text>
          </div>
        </n-descriptions-item>

        <n-descriptions-item
          v-if="currentDetail.event_type === 'macro' && currentDetail.raw_data?.新闻内容"
          label="新闻内容"
        >
          <div
            style="
              max-height: 200px;
              overflow-y: auto;
              padding: 8px;
              background: #f8f9fa;
              border-radius: 4px;
            "
          >
            <n-text style="white-space: pre-wrap; line-height: 1.6; font-size: 13px">
              {{ currentDetail.raw_data.新闻内容 }}
            </n-text>
          </div>
        </n-descriptions-item>

        <!-- 股票相关信息 -->
        <n-descriptions-item
          v-if="currentDetail.symbol || currentDetail.event_type === 'stock'"
          label="相关标的"
        >
          <n-text>
            <span v-if="currentDetail.event_type === 'stock'">
              {{
                (() => {
                  const title = currentDetail['标题'] || '';
                  const content = currentDetail['内容'] || '';
                  const symbolMatch = title.match(/[0-9]{6}/) || content.match(/[0-9]{6}/);
                  return symbolMatch ? symbolMatch[0] : currentDetail.symbol || '-';
                })()
              }}
            </span>
            <span v-else-if="currentDetail.board_name">{{ currentDetail.board_name }}</span>
            <span v-else>{{ currentDetail.symbol || '-' }}</span>
          </n-text>
        </n-descriptions-item>

        <!-- 影响和情感 -->
        <n-descriptions-item label="影响等级">
          <n-tag
            :type="
              currentDetail.impact_level === 'critical'
                ? 'error'
                : currentDetail.impact_level === 'high'
                ? 'warning'
                : currentDetail.impact_level === 'medium'
                ? 'default'
                : 'info'
            "
          >
            {{ formatImpactLevel(currentDetail.impact_level) }}
          </n-tag>
        </n-descriptions-item>

        <n-descriptions-item label="情感倾向">
          <n-tag
            :type="
              currentDetail.sentiment === 'positive'
                ? 'success'
                : currentDetail.sentiment === 'negative'
                ? 'error'
                : 'default'
            "
          >
            {{ formatSentiment(currentDetail.sentiment) }}
          </n-tag>
        </n-descriptions-item>

        <!-- 实时数据 -->
        <template v-if="currentDetail.raw_data">
          <!-- 价格数据 -->
          <n-descriptions-item
            v-if="currentDetail.raw_data.real_time_close !== undefined"
            label="实时价格"
          >
            <n-text>{{ currentDetail.raw_data.real_time_close.toFixed(2) }} 元</n-text>
          </n-descriptions-item>

          <n-descriptions-item
            v-if="currentDetail.raw_data.price_change !== undefined"
            label="涨跌幅"
          >
            <n-text :type="currentDetail.raw_data.price_change > 0 ? 'error' : 'success'">
              {{ currentDetail.raw_data.price_change > 0 ? '+' : ''
              }}{{ currentDetail.raw_data.price_change.toFixed(2) }}%
            </n-text>
          </n-descriptions-item>

          <!-- 板块数据 -->
          <n-descriptions-item
            v-if="currentDetail.raw_data.total_amount !== undefined"
            label="成交额"
          >
            <n-text>{{ (currentDetail.raw_data.total_amount / 10000).toFixed(1) }} 亿元</n-text>
          </n-descriptions-item>

          <n-descriptions-item
            v-if="currentDetail.raw_data.net_inflow !== undefined"
            label="净流入"
          >
            <n-text :type="currentDetail.raw_data.net_inflow > 0 ? 'error' : 'success'">
              {{ currentDetail.raw_data.net_inflow > 0 ? '+' : ''
              }}{{ (currentDetail.raw_data.net_inflow / 10000).toFixed(1) }} 亿元
            </n-text>
          </n-descriptions-item>

          <n-descriptions-item
            v-if="currentDetail.raw_data.rise_stocks !== undefined"
            label="上涨家数"
          >
            <n-text>
              {{ currentDetail.raw_data.rise_stocks }} /
              {{ currentDetail.raw_data.total_stocks }} ({{
                (
                  (currentDetail.raw_data.rise_stocks / currentDetail.raw_data.total_stocks) *
                  100
                ).toFixed(1)
              }}%)
            </n-text>
          </n-descriptions-item>

          <n-descriptions-item v-if="currentDetail.raw_data.leader_stock" label="领涨/跌股">
            <n-text>
              {{ currentDetail.raw_data.leader_stock }}
              <span
                v-if="currentDetail.raw_data.leader_change !== undefined"
                :type="currentDetail.raw_data.leader_change > 0 ? 'error' : 'success'"
                style="margin-left: 8px; font-size: 12px"
              >
                {{ currentDetail.raw_data.leader_change > 0 ? '+' : ''
                }}{{ currentDetail.raw_data.leader_change.toFixed(2) }}%
              </span>
            </n-text>
          </n-descriptions-item>

          <!-- 均线数据 -->
          <n-descriptions-item v-if="currentDetail.raw_data.daily_MA5 !== undefined" label="MA5">
            <n-text>{{ currentDetail.raw_data.daily_MA5.toFixed(2) }}</n-text>
          </n-descriptions-item>

          <n-descriptions-item v-if="currentDetail.raw_data.daily_MA10 !== undefined" label="MA10">
            <n-text>{{ currentDetail.raw_data.daily_MA10.toFixed(2) }}</n-text>
          </n-descriptions-item>

          <n-descriptions-item v-if="currentDetail.raw_data.daily_MA20 !== undefined" label="MA20">
            <n-text>{{ currentDetail.raw_data.daily_MA20.toFixed(2) }}</n-text>
          </n-descriptions-item>

          <n-descriptions-item v-if="currentDetail.raw_data.daily_MA60 !== undefined" label="MA60">
            <n-text>{{ currentDetail.raw_data.daily_MA60.toFixed(2) }}</n-text>
          </n-descriptions-item>

          <n-descriptions-item
            v-if="currentDetail.raw_data.deviation_pct !== undefined"
            label="偏离度"
          >
            <n-text>{{ currentDetail.raw_data.deviation_pct.toFixed(2) }}%</n-text>
          </n-descriptions-item>
        </template>

        <!-- 数据源 -->
        <n-descriptions-item v-if="currentDetail.data_source" label="数据源">
          <n-text>{{ currentDetail.data_source }}</n-text>
        </n-descriptions-item>

        <!-- 匹配关键词 -->
        <n-descriptions-item v-if="currentDetail.raw_data?.匹配关键词?.length > 0" label="关键词">
          <n-space wrap>
            <n-tag
              v-for="(keyword, index) in currentDetail.raw_data.匹配关键词"
              :key="index"
              size="small"
              type="info"
              style="margin: 2px"
            >
              {{ keyword }}
            </n-tag>
          </n-space>
        </n-descriptions-item>
      </n-descriptions>
    </div>

    <template #footer>
      <n-space justify="end">
        <n-button @click="detailModalVisible = false"> 关闭 </n-button>
      </n-space>
    </template>
  </n-modal>
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
    --color-critical: #ff4d4f;
    --color-high: #fa541c;
    --color-medium: #fa8c16;
    --color-low: #d9d9d9;
    --color-positive: #52c41a;
    --color-negative: #ff4d4f;
    --color-neutral: #666;
  }

  // 筛选框
  .filter {
    width: 100%;
    display: flex;
    align-self: center;
    background: white;
  }

  // 查询按钮
  .search-button {
    background: dodgerblue;
    color: white;
  }

  // 主容器
  .large-card {
    display: flex;
    position: relative;
    height: 100%;
    flex-direction: column;
    border-radius: 10px;
    overflow: hidden;
    background: var(--bg-page);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }

  .container {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    padding: 20px;
  }

  // 标题栏
  .header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border);

    h2 {
      margin-top: 8px;
    }
  }

  // 快速分页
  .quick-pagination {
    margin-bottom: 16px;
    padding: 12px;
    background: #f8f9fa;
    border-radius: 6px;
    border: 1px solid var(--border);

    .page-info {
      display: inline-flex;
      align-items: center;
      padding: 0 12px;
      font-size: 13px;
      color: var(--text-light);
      height: 32px;
    }
  }

  /* 添加分页器容器的样式 */
  .pagination-container {
    margin-top: 20px;
    padding: 16px 0;
    border-top: 1px solid #f0f0f0;
    display: flex;
    justify-content: center;
    width: 100%;
  }

  .pagination-wrapper {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    justify-content: center;
  }

  .page-info {
    min-width: 120px;
    text-align: center;
    font-size: 13px;
    color: #666;
    font-weight: 500;
    padding: 0 12px;
  }

  /* 原有的样式保持 */
  .large-card {
    width: 100%;
    height: 100%;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .container {
    display: flex;
    flex-direction: column;
    height: 100%;
    gap: 20px;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 16px;
    border-bottom: 1px solid #f0f0f0;
  }

  .all-events-table {
    flex: 1;
    overflow: hidden;
  }

  // 所有事件表格
  .all-events-table {
    flex: 1;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid var(--border);

    :deep(.n-data-table-base-table) {
      border-radius: 8px;
      overflow: hidden;
    }

    :deep(.n-data-table-th) {
      background: #fafafa;
      font-weight: 600;
      color: var(--text-main);
      padding: 12px 16px;
      border-bottom: 1px solid #f0f0f0;

      &:first-child {
        border-radius: 8px 0 0 0;
      }

      &:last-child {
        border-radius: 0 8px 0 0;
      }
    }

    :deep(.n-data-table-td) {
      padding: 12px 16px;
      border-bottom: 1px solid #f0f0f0;
    }

    :deep(.n-data-table-tr) {
      transition: all 0.2s ease;

      &:hover {
        background-color: #fafafa;
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
      }

      &:last-child {
        .n-data-table-td {
          border-bottom: none;
        }
      }
    }

    :deep(.event-time-cell) {
      display: flex;
      align-items: center;
      font-size: 12px;
      color: var(--text-light);
      font-family: 'SFMono-Regular', Consolas, monospace;
    }

    :deep(.description-preview) {
      max-height: 60px;
      overflow: hidden;
      text-overflow: ellipsis;
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      line-height: 1.6;
      font-size: 13px;
      color: #333;
      transition: color 0.2s ease;

      &:hover {
        color: var(--primary);
      }
    }
  }

  .detail-content {
    max-height: 60vh;
    overflow-y: auto;
    padding-right: 8px;

    :deep(.n-descriptions) {
      .n-descriptions-table {
        width: 100%;

        .n-descriptions-table-label {
          width: 100px;
          background-color: #f8f9fa;
          font-weight: 500;
          color: #333;
        }

        .n-descriptions-table-content {
          padding: 12px 16px;
        }

        tr {
          border-bottom: 1px solid #f0f0f0;

          &:last-child {
            border-bottom: none;
          }
        }
      }
    }
  }

  /* 滚动条样式 */
  .detail-content::-webkit-scrollbar {
    width: 6px;
  }

  .detail-content::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 3px;
  }

  .detail-content::-webkit-scrollbar-thumb {
    background: #c1c1c1;
    border-radius: 3px;
  }

  // 响应式适配
  @media (max-width: 768px) {
    .container {
      padding: 12px;
    }

    .large-card {
      border-radius: 8px;
    }

    .header {
      flex-direction: column;
      align-items: flex-start;
      gap: 12px;
      margin-bottom: 16px;
    }

    .quick-pagination {
      .n-space {
        flex-wrap: wrap;
        gap: 8px;
      }

      .page-info {
        width: 100%;
        text-align: center;
        justify-content: center;
        padding: 8px 0;
      }
    }

    .all-events-table {
      :deep(.n-data-table-th),
      :deep(.n-data-table-td) {
        padding: 8px 12px;
      }
    }

    // 对话框响应式
    :deep(.n-modal) {
      width: 95vw !important;
      max-width: 95vw !important;

      .n-modal-body-wrapper {
        max-height: 80vh;
      }
    }
  }

  @media (max-width: 480px) {
    .container {
      padding: 8px;
    }
  }

  // 动画效果
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

  .all-events-table :deep(.n-data-table-tr) {
    animation: fadeIn 0.3s ease-out;
    animation-fill-mode: both;
  }

  // 悬停效果增强
  :deep(.n-data-table-tr) {
    transition: all 0.2s ease;

    &:hover {
      background: linear-gradient(90deg, rgba(22, 93, 255, 0.02) 0%, rgba(22, 93, 255, 0.05) 100%);
      box-shadow: inset 2px 0 0 0 #165dff;
    }
  }

  // 滚动条样式
  :deep(.n-data-table-base-table-body) {
    &::-webkit-scrollbar {
      width: 6px;
      height: 6px;
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

  // 加载状态
  .loading-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 300px;
    flex-direction: column;
    gap: 16px;
  }

  // 空状态
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 20px;
    color: var(--text-light);
    background: white;
    border-radius: 8px;
    border: 1px dashed var(--border);

    .empty-icon {
      font-size: 48px;
      margin-bottom: 16px;
      opacity: 0.3;
    }

    .empty-text {
      font-size: 14px;
    }
  }

  // 分页器样式
  :deep(.n-pagination) {
    padding: 16px;
    border-top: 1px solid var(--border);
    background: #fafafa;
    border-radius: 0 0 8px 8px;
  }

  // 卡片悬停效果
  .n-card {
    transition: all 0.3s ease;

    &:hover {
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
    }
  }
</style>
