<template>
  <div class="dashboard-container">
    <n-card :bordered="false" class="filter-card">
      <n-space align="center" justify="space-between" style="width: 100%" wrap>
        <n-space align="center" wrap>
          <span class="filter-label">统一时间筛选</span>
          <n-date-picker
            v-model:value="dateRange"
            type="daterange"
            clearable
            :is-date-disabled="disableFutureDate"
            @update:value="onDateRangeChange"
          />
        </n-space>
        <n-space>
          <n-button
            v-for="item in quickRanges"
            :key="item.value"
            size="small"
            :type="selectedQuickRange === item.value ? 'primary' : 'default'"
            @click="setQuickRange(item.value)"
          >
            {{ item.label }}
          </n-button>
        </n-space>
      </n-space>
    </n-card>

    <!-- 顶部统计卡片 -->
    <n-grid :cols="2" :x-gap="16" :y-gap="16" class="stat-cards">
      <n-grid-item>
        <n-card class="stat-card" :bordered="false">
          <div class="stat-card-content">
            <div class="stat-icon" style="background: rgba(22, 93, 255, 0.1); color: #165dff">
              <n-icon :component="AnalyticsOutline" size="24" />
            </div>
            <div class="stat-info">
              <div class="stat-label">事件总数</div>
              <div class="stat-value">{{ statistics.totalEvents }}</div>
              <div class="stat-trend" style="visibility: hidden">&nbsp;</div>
            </div>
          </div>
        </n-card>
      </n-grid-item>

      <n-grid-item>
        <n-card class="stat-card" :bordered="false">
          <div class="stat-card-content">
            <div class="stat-icon" style="background: rgba(82, 196, 26, 0.1); color: #52c41a">
              <n-icon :component="TimeOutline" size="24" />
            </div>
            <div class="stat-info">
              <div class="stat-label">今日新增</div>
              <div class="stat-value">{{ statistics.todayEvents }}</div>
              <div class="stat-trend" v-if="statistics.eventTrend !== 0">
                <span :class="statistics.eventTrend > 0 ? 'trend-up' : 'trend-down'">
                  {{ statistics.eventTrend > 0 ? '+' : '' }}{{ statistics.eventTrend.toFixed(1) }}%
                </span>
                较昨日
              </div>
            </div>
          </div>
        </n-card>
      </n-grid-item>

    </n-grid>

    <!-- 图表区域 - 第一行 -->
    <n-grid :cols="2" :x-gap="16" :y-gap="16" class="chart-row">
      <!-- 事件类型分布饼图 -->
      <n-grid-item>
        <n-card title="事件类型分布" :bordered="false" class="chart-card">
          <div ref="typeChartRef" class="chart-container"></div>
        </n-card>
      </n-grid-item>

      <!-- 事件趋势折线图 -->
      <n-grid-item>
        <n-card title="事件趋势分析" :bordered="false" class="chart-card">
          <div ref="trendChartRef" class="chart-container"></div>
        </n-card>
      </n-grid-item>
    </n-grid>

    <!-- 图表区域 - 第二行 -->
    <n-grid :cols="2" :x-gap="16" :y-gap="16" class="chart-row">
      <!-- 影响等级分布 -->
      <n-grid-item>
        <n-card title="事件影响等级分布" :bordered="false" class="chart-card">
          <template #header-extra>
            <n-select
              v-model:value="impactChartType"
              :options="[
                { label: '柱状图', value: 'bar' },
                { label: '饼图', value: 'pie' },
              ]"
              size="small"
              style="width: 100px"
            />
          </template>
          <div ref="impactChartRef" class="chart-container"></div>
        </n-card>
      </n-grid-item>

      <!-- 情感倾向分布 -->
      <n-grid-item>
        <n-card title="情感倾向分析" :bordered="false" class="chart-card">
          <template #header-extra>
            <div class="sentiment-legend">
              <span class="legend-item positive"
                >正面 {{ statistics.sentimentStats?.positive || 0 }}</span
              >
              <span class="legend-item neutral"
                >中性 {{ statistics.sentimentStats?.neutral || 0 }}</span
              >
              <span class="legend-item negative"
                >负面 {{ statistics.sentimentStats?.negative || 0 }}</span
              >
            </div>
          </template>
          <div ref="sentimentChartRef" class="chart-container"></div>
        </n-card>
      </n-grid-item>
    </n-grid>

    <!-- 图表区域 - 第三行 - 改为2列，移除板块排行 -->
    <n-grid :cols="2" :x-gap="16" :y-gap="16" class="chart-row">
      <!-- 事件子类型TOP10 -->
      <n-grid-item>
        <n-card title="事件子类型TOP10" :bordered="false" class="chart-card">
          <div ref="subtypeChartRef" class="chart-container"></div>
        </n-card>
      </n-grid-item>

      <!-- 个股事件排行 -->
      <n-grid-item>
        <n-card title="个股事件排行" :bordered="false" class="chart-card">
          <div ref="stockChartRef" class="chart-container"></div>
        </n-card>
      </n-grid-item>
    </n-grid>
  </div>
</template>

<script setup lang="ts">
  import { ref, onMounted, watch, onBeforeUnmount } from 'vue';
  import { useMessage } from 'naive-ui';
  import * as echarts from 'echarts';
  import { AnalyticsOutline, TimeOutline } from '@vicons/ionicons5';
  import { fetchAllEvents } from '@/api/message/message';
  import { parseStr } from '@/api/time';

  const message = useMessage();

  // 图表实例引用
  const typeChartRef = ref<HTMLElement>();
  const trendChartRef = ref<HTMLElement>();
  const impactChartRef = ref<HTMLElement>();
  const sentimentChartRef = ref<HTMLElement>();
  const subtypeChartRef = ref<HTMLElement>();
  const stockChartRef = ref<HTMLElement>();

  // 图表实例
  let typeChart: echarts.ECharts | null = null;
  let trendChart: echarts.ECharts | null = null;
  let impactChart: echarts.ECharts | null = null;
  let sentimentChart: echarts.ECharts | null = null;
  let subtypeChart: echarts.ECharts | null = null;
  let stockChart: echarts.ECharts | null = null;

  // 统计数据
  const statistics = ref({
    totalEvents: 0,
    todayEvents: 0,
    involvedStocks: 0,
    avgEventsPerStock: 0,
    eventTrend: 0,
    typeStats: {
      macro: 0,
      industry: 0,
      trading: 0,
      sentiment: 0,
    },
    impactStats: {
      critical: 0,
      high: 0,
      medium: 0,
      low: 0,
    },
    sentimentStats: {
      positive: 0,
      negative: 0,
      neutral: 0,
    },
  });

  // 原始数据
  const allEvents = ref<any[]>([]);
  const filteredEvents = ref<any[]>([]);

  // 筛选状态
  const dateRange = ref<[number, number] | null>(null);
  const selectedQuickRange = ref('week');
  const impactChartType = ref('bar');

  // 快捷时间范围
  const quickRanges = [
    { label: '近7天', value: 'week', days: 7 },
    { label: '近30天', value: 'month', days: 30 },
    { label: '近90天', value: 'quarter', days: 90 },
    { label: '今年', value: 'year', days: 365 },
  ];

  const subtypeKeywordMap: Record<string, string> = {
    macro: '宏观',
    industry: '行业',
    trading: '个股',
    sentiment: '情绪',
    rise: '上涨',
    fall: '下跌',
    leader: '龙头',
    price: '价格',
    ma: '均线',
    cross: '交叉',
    breakout: '突破',
    breakdown: '跌破',
    policy: '政策',
    regulation: '监管',
  };

  function normalizeSubtypeLabel(rawSubtype: unknown): string {
    const text = String(rawSubtype || '').trim();
    if (!text) return '其他';

    const chineseOnly = text
      .replace(/[A-Za-z0-9_./\\|:;,+\-()\[\]{}<>~`!@#$%^&*'"\s]+/g, '')
      .replace(/[，。；：、！？“”‘’（）【】《》]/g, '')
      .trim();

    if (chineseOnly) return chineseOnly;

    const lowerText = text.toLowerCase();
    const matched = Object.entries(subtypeKeywordMap).find(([key]) => lowerText.includes(key));
    return matched?.[1] || '其他';
  }

  function disableFutureDate(ts: number) {
    return ts > Date.now();
  }

  function rangeByPreset(preset: string): [number, number] {
    const now = Date.now();
    const oneDay = 24 * 60 * 60 * 1000;
    if (preset === 'year') {
      return [now - 365 * oneDay, now];
    }
    if (preset === 'quarter') {
      return [now - 90 * oneDay, now];
    }
    if (preset === 'month') {
      return [now - 30 * oneDay, now];
    }
    return [now - 7 * oneDay, now];
  }

  function setQuickRange(preset: string) {
    selectedQuickRange.value = preset;
    dateRange.value = rangeByPreset(preset);
    loadData();
  }

  function onDateRangeChange() {
    selectedQuickRange.value = 'custom';
    if (dateRange.value && dateRange.value.length === 2) {
      loadData();
    }
  }

  function applyLocalFilterAndRender() {
    filteredEvents.value = filterEventsByDateRange(allEvents.value);
    statistics.value.totalEvents = filteredEvents.value.length;
    calculateStatistics(filteredEvents.value);
    renderAllCharts();
  }

  function getEventTimestamp(event: any): number {
    const candidates = [
      event?.event_time,
      event?.publish_time,
      event?.publishTime,
      event?.trade_date,
      event?.date,
      event?.time,
      event?.created_at,
      event?.createdAt,
    ];
    for (const value of candidates) {
      if (!value) continue;
      const ts = new Date(value).getTime();
      if (!Number.isNaN(ts)) return ts;
    }
    return 0;
  }

  function filterEventsByDateRange(events: any[]): any[] {
    if (!dateRange.value) return events;
    const [start, end] = dateRange.value;
    return events.filter((event) => {
      const ts = getEventTimestamp(event);
      return ts >= start && ts <= end;
    });
  }

  // 加载数据
  async function loadData() {
    try {
      const params: any = {
        page: 1,
        sort_field: 'event_time',
        sort_order: -1,
        // 避免一次拉取过大数据导致前端阻塞和 120s 超时
        size: 5000,
      };

      if (dateRange.value) {
        // 后端 list_all 会对时间参数做字符串处理，需传格式化字符串而非时间戳整数
        const start = parseStr(dateRange.value[0]);
        const end = parseStr(dateRange.value[1]);
        // 兼容不同后端字段命名：start_time/end_time 或 start_date/end_date
        params.start_time = start;
        params.end_time = end;
        params.start_date = start;
        params.end_date = end;
      }

      const response = await fetchAllEvents(params);
      const code = Number((response as any)?.code);
      const payload = (response as any)?.data ?? response;
      console.log('Dashboard 原始接口响应:', response);

      // 兼容 code 字段缺失/字符串等场景：只要拿到可解析数据就继续渲染
      if (Number.isFinite(code) && code !== 0) {
        message.error((response as any)?.msg || '获取事件数据失败');
        return;
      }

      let events: any[] = [];

      // 根据API响应结构解析数据（更宽松）
      if (payload && payload.messages) {
        events = Array.isArray(payload.messages) ? payload.messages : [];
      } else if (Array.isArray(payload)) {
        events = payload;
      } else if (payload && payload.data) {
        events = Array.isArray(payload.data) ? payload.data : [];
      } else if (payload && payload.list) {
        events = Array.isArray(payload.list) ? payload.list : [];
      } else if (payload && typeof payload === 'object') {
        const arrayKeys = Object.keys(payload).filter((key) =>
          Array.isArray((payload as any)[key])
        );
        if (arrayKeys.length > 0) {
          events = (payload as any)[arrayKeys[0]] || [];
        }
      }

      // 规范化事件类型
      events = events.map((event) => ({
        ...event,
        event_type: getEventType(event),
      }));

      allEvents.value = events;
      applyLocalFilterAndRender();

      if (!filteredEvents.value.length) {
        message.warning('接口已返回，但当前筛选条件下暂无可视化数据');
      }
    } catch (error) {
      message.error('数据加载失败');
      console.error(error);
    }
  }

  // 获取事件类型
  function getEventType(event: any): string {
    if (event.event_type) return event.event_type;
    if (event.type) return event.type;
    if (event.eventType) return event.eventType;

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

  // 计算统计数据
  function calculateStatistics(events: any[]) {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();

    console.log('事件数据:', events);

    // 今日新增
    statistics.value.todayEvents = events.filter((e) => {
      const eventTime = getEventTimestamp(e);
      return eventTime >= today;
    }).length;

    // 类型统计
    const typeStats = { macro: 0, industry: 0, trading: 0, sentiment: 0, unknown: 0 };
    const stocks = new Set();
    const stockEventCount: Record<string, number> = {};

    events.forEach((event) => {
      const type = event.event_type;
      if (type in typeStats) {
        typeStats[type as keyof typeof typeStats]++;
      } else {
        typeStats.unknown++;
      }

      // 个股统计
      let stockCode = event.symbol;
      if (!stockCode && event.event_type === 'trading') {
        const title = event['标题'] || '';
        const match = title.match(/[0-9]{6}/);
        if (match) stockCode = match[0];
      }
      if (stockCode) {
        stocks.add(stockCode);
        stockEventCount[stockCode] = (stockEventCount[stockCode] || 0) + 1;
      }
    });

    statistics.value.typeStats = typeStats;
    statistics.value.involvedStocks = stocks.size;
    statistics.value.avgEventsPerStock = stocks.size
      ? Number((events.length / stocks.size).toFixed(1))
      : 0;

    // 影响等级统计
    const impactStats = { critical: 0, high: 0, medium: 0, low: 0 };
    events.forEach((event) => {
      const level = event.impact_level || 'medium';
      if (level in impactStats) {
        impactStats[level as keyof typeof impactStats]++;
      }
    });
    statistics.value.impactStats = impactStats;

    // 情感倾向统计
    const sentimentStats = { positive: 0, negative: 0, neutral: 0 };
    events.forEach((event) => {
      let sentiment = event.sentiment || 'neutral';
      if (!event.sentiment) {
        if (event.event_type === 'industry' && event.event_subtype?.includes('rise')) {
          sentiment = 'positive';
        } else if (event.event_type === 'industry' && event.event_subtype?.includes('fall')) {
          sentiment = 'negative';
        }
      }
      if (sentiment in sentimentStats) {
        sentimentStats[sentiment as keyof typeof sentimentStats]++;
      }
    });
    statistics.value.sentimentStats = sentimentStats;

    // 计算趋势（与昨日比较）
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    const yesterdayStart = new Date(yesterday.setHours(0, 0, 0, 0)).getTime();
    const yesterdayEnd = new Date(yesterday.setHours(23, 59, 59, 999)).getTime();

    const yesterdayCount = events.filter((e) => {
      const eventTime = getEventTimestamp(e);
      return eventTime >= yesterdayStart && eventTime <= yesterdayEnd;
    }).length;

    if (yesterdayCount > 0) {
      statistics.value.eventTrend =
        ((statistics.value.todayEvents - yesterdayCount) / yesterdayCount) * 100;
    }
  }

  // 渲染所有图表
  function renderAllCharts() {
    renderTypeChart();
    renderTrendChart();
    renderImpactChart();
    renderSentimentChart();
    renderSubtypeChart();
    renderStockChart();
  }

  // 渲染事件类型分布饼图
  function renderTypeChart() {
    if (!typeChartRef.value) return;

    if (!typeChart) {
      typeChart = echarts.init(typeChartRef.value);
    }

    const typeStats = { macro: 0, industry: 0, trading: 0, sentiment: 0 };
    filteredEvents.value.forEach((event) => {
      const t = String(event.event_type || '');
      if (t in typeStats) {
        typeStats[t as keyof typeof typeStats]++;
      }
    });

    const data = [
      { name: '宏观事件', value: typeStats.macro },
      { name: '行业事件', value: typeStats.industry },
      { name: '个股事件', value: typeStats.trading },
      { name: '情绪事件', value: typeStats.sentiment },
    ].filter((item) => item.value > 0);

    const option = {
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)',
      },
      legend: {
        orient: 'vertical',
        right: 10,
        top: 20,
        textStyle: { fontSize: 12 },
      },
      series: [
        {
          name: '事件类型',
          type: 'pie',
          radius: ['45%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 10,
            borderColor: '#fff',
            borderWidth: 2,
          },
          label: {
            show: false,
          },
          emphasis: {
            label: {
              show: true,
              fontSize: '12',
              fontWeight: 'bold',
            },
          },
          data: data,
          color: ['#1890ff', '#52c41a', '#722ed1', '#fa8c16'],
        },
      ],
    };

    typeChart.setOption(option);
  }

  // 渲染事件趋势折线图
  function renderTrendChart() {
    if (!trendChartRef.value) return;

    if (!trendChart) {
      trendChart = echarts.init(trendChartRef.value);
    }

    const dates: string[] = [];
    const eventCounts: number[] = [];
    const range = dateRange.value || rangeByPreset('week');
    const start = new Date(range[0]);
    const end = new Date(range[1]);
    const cursor = new Date(start);

    while (cursor.getTime() <= end.getTime()) {
      const date = new Date(cursor);
      dates.push(`${date.getMonth() + 1}/${date.getDate()}`);

      // 计算当天的事件数量
      const dayStart = new Date(date.setHours(0, 0, 0, 0)).getTime();
      const dayEnd = new Date(date.setHours(23, 59, 59, 999)).getTime();

      const count = filteredEvents.value.filter((e) => {
        const eventTime = getEventTimestamp(e);
        return eventTime >= dayStart && eventTime <= dayEnd;
      }).length;

      eventCounts.push(count);
      cursor.setDate(cursor.getDate() + 1);
    }

    const option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
      },
      grid: {
        left: '5%',
        right: '5%',
        bottom: '18%',
        top: '10%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { rotate: 30 },
      },
      yAxis: {
        type: 'value',
        name: '事件数量',
      },
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: 0,
          filterMode: 'filter',
          // 降低缩放灵敏度：按住 Ctrl + 滚轮才触发缩放
          zoomOnMouseWheel: 'ctrl',
          moveOnMouseMove: true,
          moveOnMouseWheel: false,
          throttle: 120,
        },
        {
          type: 'slider',
          xAxisIndex: 0,
          filterMode: 'filter',
          realtime: false,
          height: 18,
          bottom: 10,
          borderColor: '#d9d9d9',
          fillerColor: 'rgba(22, 93, 255, 0.15)',
          handleStyle: {
            color: '#165dff',
            borderColor: '#165dff',
          },
        },
      ],
      series: [
        {
          name: '事件数量',
          type: 'line',
          data: eventCounts,
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: { width: 3, color: '#165dff' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(22, 93, 255, 0.5)' },
              { offset: 1, color: 'rgba(22, 93, 255, 0.1)' },
            ]),
          },
        },
      ],
    };

    trendChart.setOption(option);
  }

  // 渲染影响等级分布
  function renderImpactChart() {
    if (!impactChartRef.value) return;

    if (!impactChart) {
      impactChart = echarts.init(impactChartRef.value);
    }

    const impactStats = { critical: 0, high: 0, medium: 0, low: 0 };
    filteredEvents.value.forEach((event) => {
      const level = event.impact_level || 'medium';
      if (level in impactStats) {
        impactStats[level as keyof typeof impactStats]++;
      }
    });

    const data = [
      { name: '极高', value: impactStats.critical },
      { name: '高', value: impactStats.high },
      { name: '中', value: impactStats.medium },
      { name: '低', value: impactStats.low },
    ].filter((item) => item.value > 0);

    let option;

    if (impactChartType.value === 'pie') {
      option = {
        tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
        legend: { orient: 'vertical', right: 10, top: 20 },
        series: [
          {
            type: 'pie',
            radius: ['45%', '70%'],
            data: data,
            color: ['#ff4d4f', '#fa541c', '#fa8c16', '#d9d9d9'],
          },
        ],
      };
    } else {
      option = {
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        grid: { left: '10%', right: '5%', bottom: '10%', top: '10%' },
        xAxis: { type: 'category', data: data.map((d) => d.name) },
        yAxis: { type: 'value', name: '事件数量' },
        series: [
          {
            name: '事件数量',
            type: 'bar',
            data: data.map((d) => d.value),
            itemStyle: {
              color: (params: any) => {
                const colors = ['#ff4d4f', '#fa541c', '#fa8c16', '#d9d9d9'];
                return colors[params.dataIndex];
              },
            },
            barWidth: 30,
          },
        ],
      };
    }

    impactChart.setOption(option);
  }

  // 渲染情感倾向图表
  function renderSentimentChart() {
    if (!sentimentChartRef.value) return;

    if (!sentimentChart) {
      sentimentChart = echarts.init(sentimentChartRef.value);
    }

    const sentimentStats = { positive: 0, negative: 0, neutral: 0 };
    filteredEvents.value.forEach((event) => {
      let sentiment = event.sentiment || 'neutral';
      if (!event.sentiment) {
        if (event.event_type === 'industry' && event.event_subtype?.includes('rise')) {
          sentiment = 'positive';
        } else if (event.event_type === 'industry' && event.event_subtype?.includes('fall')) {
          sentiment = 'negative';
        }
      }
      if (sentiment in sentimentStats) {
        sentimentStats[sentiment as keyof typeof sentimentStats]++;
      }
    });

    const option = {
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)',
      },
      legend: {
        show: false,
      },
      series: [
        {
          name: '情感倾向',
          type: 'pie',
          radius: ['50%', '70%'],
          avoidLabelOverlap: false,
          label: {
            show: true,
            position: 'outside',
            formatter: '{b}: {d}%',
          },
          emphasis: {
            label: {
              show: true,
              fontSize: '12',
              fontWeight: 'bold',
            },
          },
          data: [
            { name: '正面', value: sentimentStats.positive },
            { name: '中性', value: sentimentStats.neutral },
            { name: '负面', value: sentimentStats.negative },
          ].filter((item) => item.value > 0),
          color: ['#52c41a', '#666666', '#ff4d4f'],
          labelLine: {
            length: 10,
            length2: 10,
            smooth: true,
          },
        },
      ],
    };

    sentimentChart.setOption(option);
  }

  // 渲染事件子类型TOP10
  function renderSubtypeChart() {
    if (!subtypeChartRef.value) return;

    if (!subtypeChart) {
      subtypeChart = echarts.init(subtypeChartRef.value);
    }

    // 统计子类型
    const subtypeCount: Record<string, number> = {};
    filteredEvents.value.forEach((event) => {
      const subtype = normalizeSubtypeLabel(event.event_subtype);
      subtypeCount[subtype] = (subtypeCount[subtype] || 0) + 1;
    });

    // 取TOP10
    const top10 = Object.entries(subtypeCount)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([name, value]) => ({ name, value }));

    const option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
      },
      grid: {
        left: '5%',
        right: '15%',
        bottom: '5%',
        top: '5%',
        containLabel: true,
      },
      xAxis: {
        type: 'value',
        name: '事件数量',
      },
      yAxis: {
        type: 'category',
        data: top10.map((item) => item.name),
        axisLabel: {
          width: 100,
          overflow: 'truncate',
        },
      },
      series: [
        {
          name: '事件数量',
          type: 'bar',
          data: top10.map((item) => item.value),
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#165dff' },
              { offset: 1, color: '#4a86ff' },
            ]),
          },
          barWidth: 15,
          label: {
            show: true,
            position: 'right',
            fontWeight: 'bold',
          },
        },
      ],
    };

    subtypeChart.setOption(option);
  }

  // 渲染个股事件排行
  function renderStockChart() {
    if (!stockChartRef.value) return;

    if (!stockChart) {
      stockChart = echarts.init(stockChartRef.value);
    }

    // 统计个股
    const stockCount: Record<string, number> = {};
    filteredEvents.value.forEach((event) => {
      let stockCode = event.symbol;
      if (!stockCode && event.event_type === 'trading') {
        const title = event['标题'] || '';
        const match = title.match(/[0-9]{6}/);
        if (match) stockCode = match[0];
      }
      if (stockCode) {
        stockCount[stockCode] = (stockCount[stockCode] || 0) + 1;
      }
    });

    // 取TOP10
    const top10 = Object.entries(stockCount)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([name, value]) => ({ name, value }));

    const option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
      },
      grid: {
        left: '5%',
        right: '15%',
        bottom: '5%',
        top: '5%',
        containLabel: true,
      },
      xAxis: {
        type: 'value',
        name: '事件数量',
      },
      yAxis: {
        type: 'category',
        data: top10.map((item) => item.name),
        axisLabel: {
          width: 60,
          overflow: 'truncate',
        },
      },
      series: [
        {
          name: '事件数量',
          type: 'bar',
          data: top10.map((item) => item.value),
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#722ed1' },
              { offset: 1, color: '#b37feb' },
            ]),
          },
          barWidth: 15,
          label: {
            show: true,
            position: 'right',
            fontWeight: 'bold',
          },
        },
      ],
    };

    stockChart.setOption(option);
  }

  // 监听图表类型变化
  watch(impactChartType, () => {
    renderImpactChart();
  });

  watch(
    () => dateRange.value,
    (val) => {
      if (val && val.length === 2 && allEvents.value.length) {
        applyLocalFilterAndRender();
      }
    },
    { deep: true }
  );

  // 窗口大小变化时重置图表
  function handleResize() {
    [typeChart, trendChart, impactChart, sentimentChart, subtypeChart, stockChart].forEach(
      (chart) => {
        chart?.resize();
      }
    );
  }

  // 初始化
  onMounted(() => {
    // 默认统计近7天
    if (!dateRange.value) {
      dateRange.value = rangeByPreset('week');
      selectedQuickRange.value = 'week';
    }
    loadData();
    window.addEventListener('resize', handleResize);
  });

  // 清理
  onBeforeUnmount(() => {
    window.removeEventListener('resize', handleResize);
    [typeChart, trendChart, impactChart, sentimentChart, subtypeChart, stockChart].forEach(
      (chart) => {
        chart?.dispose();
      }
    );
  });
</script>

<style scoped lang="less">
  .dashboard-container {
    padding: 20px;
    background: #f5f7fa;
    min-height: 100vh;
  }

  .filter-card {
    margin-bottom: 16px;
    border-radius: 12px;
    background: linear-gradient(135deg, #eef5ff 0%, #f8fbff 60%, #ffffff 100%);
    box-shadow: 0 4px 16px rgba(22, 93, 255, 0.08);

    :deep(.n-card__content) {
      padding: 14px 16px;
    }
  }

  .filter-label {
    font-size: 13px;
    font-weight: 600;
    color: #165dff;
    padding: 4px 10px;
    border-radius: 999px;
    background: rgba(22, 93, 255, 0.1);
  }

  .stat-cards {
    margin-bottom: 16px;
  }

  .stat-card {
    height: 100%;
    border-radius: 12px;
    transition: all 0.3s ease;

    &:hover {
      transform: translateY(-4px);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
    }

    :deep(.n-card__content) {
      padding: 20px;
    }
  }

  .stat-card-content {
    display: flex;
    align-items: stretch;
    gap: 16px;
  }

  .stat-icon {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .stat-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 72px;
  }

  .stat-label {
    font-size: 13px;
    color: #666;
    margin-bottom: 4px;
  }

  .stat-value {
    font-size: 24px;
    font-weight: 600;
    color: #333;
    line-height: 1.2;
    margin-bottom: 4px;
  }

  .stat-trend {
    font-size: 12px;
    color: #999;

    .trend-up {
      color: #f5222d;
      font-weight: 500;
    }

    .trend-down {
      color: #52c41a;
      font-weight: 500;
    }
  }

  .chart-row {
    margin-bottom: 16px;
  }

  .chart-card {
    border-radius: 12px;

    :deep(.n-card__content) {
      padding: 16px;
    }

    :deep(.n-card-header) {
      padding: 16px 16px 8px;
      border-bottom: 1px solid #f0f0f0;
    }
  }

  .chart-container {
    width: 100%;
    height: 280px;
  }

  .sentiment-legend {
    display: flex;
    gap: 16px;
    font-size: 12px;
  }

  .legend-item {
    padding: 2px 8px;
    border-radius: 4px;

    &.positive {
      background: rgba(82, 196, 26, 0.1);
      color: #52c41a;
    }

    &.neutral {
      background: rgba(102, 102, 102, 0.1);
      color: #666;
    }

    &.negative {
      background: rgba(255, 77, 79, 0.1);
      color: #ff4d4f;
    }
  }

  @media (max-width: 768px) {
    .dashboard-container {
      padding: 12px;
    }

    .stat-card-content {
      flex-direction: column;
      text-align: center;
    }

    .stat-icon {
      margin: 0 auto;
    }

    .chart-container {
      height: 240px;
    }
  }
</style>
