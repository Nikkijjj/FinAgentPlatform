<script setup lang="ts">
    import { onMounted, ref, computed, h } from 'vue';
    import {
      fetchMessage_Events,
      fetchMessage_Industry,
      fetchMessage_Mood,
      fetchMessage_Stock,
    } from '@/api/message/message';
    import { 
      useMessage, 
      NTag, 
      NIcon, 
      NStatistic, 
      NGrid, 
      NGridItem,
      NModal,
      NForm,
      NFormItem,
      NText,
      NCollapse,
      NCollapseItem,
      NDescriptions,
      NDescriptionsItem,
      NEllipsis,
      NSpace,
      NTime,
      NButton,
      NResult,
      NCard,
    } from 'naive-ui';
    import { DataTableColumns } from 'naive-ui';
    import { 
      TrendingUpOutline, 
      FlashOutline, 
      ArrowUpOutline, 
      EyeOutline,
      TimeOutline,
      StatsChartOutline,
      AnalyticsOutline,
      BusinessOutline 
    } from '@vicons/ionicons5';

    const message = useMessage();

    // 数据响应式引用
    const messages_macro = ref<any[]>([]);
    const messages_industry = ref<any[]>([]);
    const messages_mood = ref<any[]>([]);
    const messages_stock = ref<any[]>([]);

    // 加载状态
    const loading = ref({
      macro: true,
      industry: true,
      mood: true,
      stock: true
    });

    // 详情对话框控制
    const detailModalVisible = ref(false);
    const currentDetail = ref<any>(null);
    const detailType = ref<'macro' | 'industry' | 'mood' | 'stock'>('macro');

    onMounted(async () => {
      try {
        // 并发请求所有数据
        const [eventsResponse, industryResponse, moodResponse, stockResponse] = await Promise.all([
          fetchMessage_Events(),
          fetchMessage_Industry(),
          fetchMessage_Mood(),
          fetchMessage_Stock(),
        ]);

        // 处理宏观数据
        if (eventsResponse.code === 0) {
          messages_macro.value = eventsResponse.data.messages || [];
        } else {
          message.error(`宏观数据获取失败: ${eventsResponse.msg}`);
        }
        loading.value.macro = false;

        // 处理行业数据
        if (industryResponse.code === 0) {
          messages_industry.value = industryResponse.data.messages || [];
        } else {
          message.error(`行业数据获取失败: ${industryResponse.msg}`);
        }
        loading.value.industry = false;

        // 处理情绪数据
        if (moodResponse.code === 0) {
          messages_mood.value = moodResponse.data.messages || [];
        } else {
          message.error(`情绪数据获取失败: ${moodResponse.msg}`);
        }
        loading.value.mood = false;

        // 处理个股数据
        if (stockResponse.code === 0) {
          messages_stock.value = stockResponse.data || [];
        } else {
          message.error(`个股数据获取失败: ${stockResponse.msg}`);
        }
        loading.value.stock = false;

      } catch (error) {
        message.error('数据加载失败');
        console.error('数据加载失败:', error);
      }
    });

    // 查看详情
    const showDetail = (item: any, type: 'macro' | 'industry' | 'mood' | 'stock' = 'macro') => {
      currentDetail.value = item;
      detailType.value = type;
      detailModalVisible.value = true;
    };

    // 格式化时间的函数
    function formatDateTime(dateString: string) {
      if (!dateString) return '-';
      const date = new Date(dateString);
      return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      });
    }

    // 格式化新闻内容的函数
    function formatNewsContent(content: string, maxLength: number = 200) {
      if (!content) return '-';
      if (content.length <= maxLength) return content;
      return content.substring(0, maxLength) + '...';
    }

    // 获取影响级别颜色的函数
    function getImpactLevelColor(level: string) {
      const colorMap: Record<string, string> = {
        critical: '#ff4d4f',
        high: '#fa541c',
        medium: '#fa8c16',
        low: '#d9d9d9'
      };
      return colorMap[level] || '#666';
    }

    // 获取情感颜色的函数
    function getSentimentColor(sentiment: string) {
      const colorMap: Record<string, string> = {
        positive: '#52c41a',
        negative: '#ff4d4f',
        neutral: '#666'
      };
      return colorMap[sentiment] || '#666';
    }

    // 宏观数据列定义
    const columns_macro: DataTableColumns = [
      {
        title: '事件时间',
        key: 'event_time',
        width: 120,
        fixed: 'left',
        align: 'center',
        sorter: (a, b) => new Date(a.event_time).getTime() - new Date(b.event_time).getTime(),
        render(row) {
          return h('div', { class: 'event-time-cell' }, [
            h(NIcon, { size: '14', style: { marginRight: '4px', color: '#1890ff' } }, { default: () => h(TimeOutline) }),
            h('span', formatDateTime(row.event_time))
          ]);
        }
      },
      {
        title: '事件摘要',
        key: 'event_description',
        width: 300,
        align: 'center',
        ellipsis: {
          tooltip: true
        },
        render(row) {
          const description = row.event_description || '';
          return h('div', { class: 'description-preview' }, [
            h(NEllipsis, { tooltip: false }, {
              default: () => description
            })
          ]);
        }
      },
      {
        title: '影响级别',
        key: 'impact_level',
        width: 60,
        align: 'center',
        render(row) {
          const level = row.impact_level;
          const levelMap: Record<string, any> = {
            critical: { text: '极高', class: 'level-critical' },
            high: { text: '高', class: 'level-high' },
            medium: { text: '中', class: 'level-medium' },
            low: { text: '低', class: 'level-low' }
          };
          const config = levelMap[level] || { text: level, class: '' };
          return h('span', { class: `impact-level ${config.class}` }, config.text);
        }
      },
      {
        title: '情感',
        key: 'sentiment',
        width: 80,
        align: 'center',
        render(row) {
          const sentiment = row.sentiment;
          const sentimentMap: Record<string, any> = {
            positive: { text: '正面', class: 'sentiment-positive' },
            negative: { text: '负面', class: 'sentiment-negative' },
            neutral: { text: '中性', class: 'sentiment-neutral' }
          };
          const config = sentimentMap[sentiment] || { text: sentiment, class: '' };
          return h('span', { class: `sentiment ${config.class}` }, config.text);
        }
      },
      {
        title: '相关标的',
        key: 'symbol',
        width: 120,
        align: 'center',
        render(row) {
          if (!row.symbol) return h('span', '-');
          return h('div', { class: 'symbol-cell' }, [
            h(NIcon, { size: '14', style: { marginRight: '4px', color: '#165dff' } }, { default: () => h(BusinessOutline) }),
            h('span', { class: 'symbol-text' }, row.symbol)
          ]);
        }
      },
    ];

    // 行业数据列定义
    const columns_industry: DataTableColumns = [
      {
        title: '事件时间',
        key: 'event_time',
        width: 120,
        fixed: 'left',
        align: 'center',
        sorter: (a, b) => new Date(a.event_time).getTime() - new Date(b.event_time).getTime(),
        render(row) {
          return h('div', { class: 'event-time-cell' }, [
            h(NIcon, { size: '14', style: { marginRight: '4px', color: '#1890ff' } }, { default: () => h(TimeOutline) }),
            h('span', formatDateTime(row.event_time))
          ]);
        }
      },
      {
        title: '事件摘要',
        key: 'event_description',
        width: 300,
        align: 'center',
        ellipsis: {
          tooltip: true
        },
        render(row) {
          // 为不同异常类型生成相应的描述
          let description = '';
          const boardName = row.board_name || row.symbol || '';
          const rawData = row.raw_data || {};
          
          switch(row.event_subtype) {
            case 'price_rise_abnormal':
              description = `${boardName}板块涨幅异常，上涨${rawData.price_change?.toFixed(2) || '0.00'}%，上涨家数${rawData.rise_stocks || 0}/${rawData.total_stocks || 0}`;
              break;
            case 'price_fall_abnormal':
              description = `${boardName}板块跌幅异常，下跌${Math.abs(rawData.price_change || 0).toFixed(2)}%，领跌股：${rawData.leader_stock || '-'}`;
              break;
            case 'leader_fluctuation_abnormal':
              description = `${boardName}板块龙头异动，${rawData.leader_stock || '龙头股'}涨跌${rawData.leader_change?.toFixed(2) || '0.00'}%`;
              break;
            case 'rise_consistency_abnormal':
              description = `${boardName}板块上涨一致性异常，上涨家数占比${rawData.rise_stocks && rawData.total_stocks ? ((rawData.rise_stocks / rawData.total_stocks) * 100).toFixed(1) : '0.0'}%`;
              break;
            case 'fall_consistency_abnormal':
              description = `${boardName}板块下跌一致性异常，成交额${rawData.total_amount ? (rawData.total_amount / 10000).toFixed(1) : '0.0'}亿元`;
              break;
            default:
              description = `${boardName}板块异常波动`;
          }
          
          return h('div', { class: 'description-preview' }, [
            h(NEllipsis, { tooltip: false }, {
              default: () => description
            })
          ]);
        }
      },
      {
        title: '影响级别',
        key: 'impact_level',
        width: 60,
        align: 'center',
        render(row) {
          // 根据异常类型自动确定影响级别
          let level = 'medium';
          const rawData = row.raw_data || {};
          
          if (row.event_subtype === 'price_rise_abnormal' || row.event_subtype === 'price_fall_abnormal') {
            const change = Math.abs(rawData.price_change || 0);
            if (change > 5) level = 'critical';
            else if (change > 3) level = 'high';
            else if (change > 2) level = 'medium';
            else level = 'low';
          } else if (row.event_subtype === 'leader_fluctuation_abnormal') {
            const change = Math.abs(rawData.leader_change || 0);
            if (change > 8) level = 'critical';
            else if (change > 5) level = 'high';
            else if (change > 3) level = 'medium';
            else level = 'low';
          }
          
          const levelMap: Record<string, any> = {
            critical: { text: '极高', class: 'level-critical' },
            high: { text: '高', class: 'level-high' },
            medium: { text: '中', class: 'level-medium' },
            low: { text: '低', class: 'level-low' }
          };
          const config = levelMap[level] || { text: level, class: '' };
          return h('span', { class: `impact-level ${config.class}` }, config.text);
        }
      },
      {
        title: '情感',
        key: 'sentiment',
        width: 80,
        align: 'center',
        render(row) {
          // 根据异常类型确定情感
          let sentiment = 'neutral';
          
          if (row.event_subtype === 'price_rise_abnormal' || 
              row.event_subtype === 'rise_consistency_abnormal') {
            sentiment = 'positive';
          } else if (row.event_subtype === 'price_fall_abnormal' || 
                     row.event_subtype === 'fall_consistency_abnormal') {
            sentiment = 'negative';
          }
          
          const sentimentMap: Record<string, any> = {
            positive: { text: '正面', class: 'sentiment-positive' },
            negative: { text: '负面', class: 'sentiment-negative' },
            neutral: { text: '中性', class: 'sentiment-neutral' }
          };
          const config = sentimentMap[sentiment] || { text: sentiment, class: '' };
          return h('span', { class: `sentiment ${config.class}` }, config.text);
        }
      },
      {
        title: '相关标的',
        key: 'symbol',
        width: 120,
        align: 'center',
        render(row) {
          const boardName = row.board_name || row.symbol || '-';
          return h('div', { class: 'symbol-cell' }, [
            h(NIcon, { size: '14', style: { marginRight: '4px', color: '#165dff' } }, { default: () => h(BusinessOutline) }),
            h('span', { class: 'symbol-text' }, boardName)
          ]);
        }
      },
    ];

    // 情绪数据列定义
    const columns_mood: DataTableColumns = [
      {
        title: '事件时间',
        key: 'event_time',
        width: 120,
        fixed: 'left',
        align: 'center',
        sorter: (a, b) => new Date(a.event_time).getTime() - new Date(b.event_time).getTime(),
        render(row) {
          return h('div', { class: 'event-time-cell' }, [
            h(NIcon, { size: '14', style: { marginRight: '4px', color: '#1890ff' } }, { default: () => h(TimeOutline) }),
            h('span', formatDateTime(row.event_time))
          ]);
        }
      },
      {
        title: '事件摘要',
        key: 'event_description',
        width: 300,
        align: 'center',
        ellipsis: {
          tooltip: true
        },
        render(row) {
          // 直接使用接口返回的 event_description
          const description = row.event_description || '';
          return h('div', { class: 'description-preview' }, [
            h(NEllipsis, { tooltip: false }, {
              default: () => description
            })
          ]);
        }
      },
      {
        title: '影响级别',
        key: 'impact_level',
        width: 60,
        align: 'center',
        render(row) {
          const level = row.impact_level;
          const levelMap: Record<string, any> = {
            critical: { text: '极高', class: 'level-critical' },
            high: { text: '高', class: 'level-high' },
            medium: { text: '中', class: 'level-medium' },
            low: { text: '低', class: 'level-low' }
          };
          const config = levelMap[level] || { text: level, class: '' };
          return h('span', { class: `impact-level ${config.class}` }, config.text);
        }
      },
      {
        title: '情感',
        key: 'sentiment',
        width: 80,
        align: 'center',
        render(row) {
          const sentiment = row.sentiment;
          const sentimentMap: Record<string, any> = {
            positive: { text: '正面', class: 'sentiment-positive' },
            negative: { text: '负面', class: 'sentiment-negative' },
            neutral: { text: '中性', class: 'sentiment-neutral' }
          };
          const config = sentimentMap[sentiment] || { text: sentiment, class: '' };
          return h('span', { class: `sentiment ${config.class}` }, config.text);
        }
      },
      {
        title: '相关标的',
        key: 'symbol',
        width: 120,
        align: 'center',
        render(row) {
          const symbol = row.symbol || '-';
          return h('div', { class: 'symbol-cell' }, [
            h(NIcon, { size: '14', style: { marginRight: '4px', color: '#165dff' } }, { default: () => h(BusinessOutline) }),
            h('span', { class: 'symbol-text' }, symbol)
          ]);
        }
      },
    ];

    // 个股数据列定义 - 优化后的版本
    const columns_stock: DataTableColumns = [
      {
        title: '事件时间',
        key: '发布时间',
        width: 120,
        fixed: 'left',
        align: 'center',
        sorter: (a, b) => {
          const timeA = a['发布时间'] ? new Date(a['发布时间']).getTime() : 0;
          const timeB = b['发布时间'] ? new Date(b['发布时间']).getTime() : 0;
          return timeA - timeB;
        },
        render(row) {
          const time = row['发布时间'];
          return h('div', { class: 'event-time-cell' }, [
            h(NIcon, { size: '14', style: { marginRight: '4px', color: '#1890ff' } }, { default: () => h(TimeOutline) }),
            h('span', time || '-')
          ]);
        }
      },
      {
        title: '事件摘要',
        key: '标题',
        width: 300,
        align: 'center',
        ellipsis: {
          tooltip: true
        },
        render(row) {
          // 使用标题作为事件摘要
          const title = row['标题'] || '个股新闻';
          const content = row['内容'] || '';
          
          // 生成更简洁的摘要
          let summary = title;
          if (content && summary === title) {
            // 如果标题就是摘要，则使用内容的前50个字符作为补充
            const briefContent = content.length > 50 ? content.substring(0, 50) + '...' : content;
            return h('div', { class: 'description-preview' }, [
              h(NEllipsis, { tooltip: false, lineClamp: 3 }, {
                default: () => `${title} - ${briefContent}`
              })
            ]);
          }
          
          return h('div', { class: 'description-preview' }, [
            h(NEllipsis, { tooltip: false, lineClamp: 3 }, {
              default: () => summary
            })
          ]);
        }
      },
      {
        title: '影响级别',
        key: 'impact_level',
        width: 60,
        align: 'center',
        render(row) {
          // 根据个股新闻内容分析影响级别
          let level = 'low';
          const content = (row['内容'] || '').toLowerCase();
          const title = (row['标题'] || '').toLowerCase();
          
          // 根据关键词判断影响级别
          const criticalKeywords = ['暴跌', '崩盘', '破产', '重大利空', '退市', 'st'];
          const highKeywords = ['大跌', '下滑', '亏损', '风险', '警告', '违规'];
          const mediumKeywords = ['调整', '波动', '影响', '变化', '下跌'];
          
          const allText = title + ' ' + content;
          
          if (criticalKeywords.some(keyword => allText.includes(keyword))) {
            level = 'critical';
          } else if (highKeywords.some(keyword => allText.includes(keyword))) {
            level = 'high';
          } else if (mediumKeywords.some(keyword => allText.includes(keyword))) {
            level = 'medium';
          }
          
          const levelMap: Record<string, any> = {
            critical: { text: '极高', class: 'level-critical' },
            high: { text: '高', class: 'level-high' },
            medium: { text: '中', class: 'level-medium' },
            low: { text: '低', class: 'level-low' }
          };
          const config = levelMap[level] || { text: level, class: '' };
          return h('span', { class: `impact-level ${config.class}` }, config.text);
        }
      },
      {
        title: '情感',
        key: 'sentiment',
        width: 80,
        align: 'center',
        render(row) {
          // 根据个股新闻内容分析情感倾向
          let sentiment = 'neutral';
          const content = (row['内容'] || '').toLowerCase();
          const title = (row['标题'] || '').toLowerCase();
          
          // 根据关键词判断情感
          const positiveKeywords = ['上涨', '涨停', '增长', '利好', '盈利', '业绩预增', '突破'];
          const negativeKeywords = ['下跌', '跌停', '下滑', '利空', '亏损', '业绩预减', '风险'];
          
          const allText = title + ' ' + content;
          
          if (positiveKeywords.some(keyword => allText.includes(keyword))) {
            sentiment = 'positive';
          } else if (negativeKeywords.some(keyword => allText.includes(keyword))) {
            sentiment = 'negative';
          }
          
          const sentimentMap: Record<string, any> = {
            positive: { text: '正面', class: 'sentiment-positive' },
            negative: { text: '负面', class: 'sentiment-negative' },
            neutral: { text: '中性', class: 'sentiment-neutral' }
          };
          const config = sentimentMap[sentiment] || { text: sentiment, class: '' };
          return h('span', { class: `sentiment ${config.class}` }, config.text);
        }
      },
      {
        title: '相关标的',
        key: 'symbol',
        width: 120,
        align: 'center',
        render(row) {
          // 从标题中提取股票代码，如果没有则使用"-"
          const title = row['标题'] || '';
          let symbol = '-';
          
          // 尝试从标题中提取股票代码（6位数字）
          const symbolMatch = title.match(/[0-9]{6}/);
          if (symbolMatch) {
            symbol = symbolMatch[0];
          }
          // 如果没有找到，尝试从内容中提取
          else {
            const content = row['内容'] || '';
            const contentSymbolMatch = content.match(/[0-9]{6}/);
            if (contentSymbolMatch) {
              symbol = contentSymbolMatch[0];
            }
          }
          
          return h('div', { class: 'symbol-cell' }, [
            h(NIcon, { size: '14', style: { marginRight: '4px', color: '#165dff' } }, { default: () => h(BusinessOutline) }),
            h('span', { class: 'symbol-text' }, symbol)
          ]);
        }
      },
    ];

    // 分页配置
    const pagination = { 
      pageSize: 10,
      showSizePicker: true,
      pageSizes: [10, 20, 50, 100],
      showQuickJumper: true
    };

    // 格式化事件类型
    function formatEventType(type: string) {
      const typeMap: Record<string, string> = {
        'macro': '宏观事件',
        'industry': '行业事件',
        'trading': '交易情绪',
        'stock': '个股事件'
      };
      return typeMap[type] || type;
    }

    // 格式化事件子类型
    function formatEventSubtype(subtype: string) {
      const subtypeMap: Record<string, string> = {
        'macro_综合宏观新闻': '综合宏观新闻',
        'macro_资本市场': '资本市场',
        'macro_央行政策': '央行政策',
        'macro_金融监管': '金融监管',
        'macro_经济增长': '经济增长',
        'macro_国际局势': '国际局势',
        'price_rise_abnormal': '涨幅异常',
        'price_fall_abnormal': '跌幅异常',
        'rise_consistency_abnormal': '上涨一致',
        'fall_consistency_abnormal': '下跌一致',
        'leader_fluctuation_abnormal': '龙头异动',
        'ma5_cross_up': 'MA5上穿',
        'ma5_cross_down': 'MA5下穿',
        'ma10_cross_up': 'MA10上穿',
        'ma10_cross_down': 'MA10下穿',
        'ma20_cross_up': 'MA20上穿',
        'ma20_cross_down': 'MA20下穿',
        'ma60_cross_up': 'MA60上穿',
        'ma60_cross_down': 'MA60下穿'
      };
      return subtypeMap[subtype] || subtype?.replace('macro_', '') || subtype;
    }

    // 格式化影响级别
    function formatImpactLevel(level: string) {
      const levelMap: Record<string, string> = {
        'critical': '极高',
        'high': '高',
        'medium': '中',
        'low': '低'
      };
      return levelMap[level] || level;
    }

    // 格式化情绪
    function formatSentiment(sentiment: string) {
      const sentimentMap: Record<string, string> = {
        'positive': '正面',
        'negative': '负面',
        'neutral': '中性'
      };
      return sentimentMap[sentiment] || sentiment;
    }

    // 格式化行业异常类型描述
    function formatIndustryEventDescription(item: any) {
      const boardName = item.board_name || item.symbol || '';
      const rawData = item.raw_data || {};
      
      switch(item.event_subtype) {
        case 'price_rise_abnormal':
          return `${boardName}板块出现异常上涨，涨幅${rawData.price_change?.toFixed(2) || '0.00'}%，成交额${rawData.total_amount ? (rawData.total_amount / 10000).toFixed(1) : '0.0'}亿元`;
        case 'price_fall_abnormal':
          return `${boardName}板块出现异常下跌，跌幅${Math.abs(rawData.price_change || 0).toFixed(2)}%，领跌股${rawData.leader_stock || '-'}跌${Math.abs(rawData.leader_change || 0).toFixed(2)}%`;
        case 'leader_fluctuation_abnormal':
          return `${boardName}板块龙头股${rawData.leader_stock || '-'}异动，涨跌${rawData.leader_change?.toFixed(2) || '0.00'}%，带动板块整体波动`;
        case 'rise_consistency_abnormal':
          return `${boardName}板块上涨一致性异常，上涨家数${rawData.rise_stocks || 0}/${rawData.total_stocks || 0}，占比${rawData.rise_stocks && rawData.total_stocks ? ((rawData.rise_stocks / rawData.total_stocks) * 100).toFixed(1) : '0.0'}%`;
        case 'fall_consistency_abnormal':
          return `${boardName}板块下跌一致性异常，下跌家数占比高，净流出${rawData.net_inflow ? Math.abs(rawData.net_inflow / 10000).toFixed(1) : '0.0'}亿元`;
        default:
          return `${boardName}板块出现异常波动`;
      }
    }

    // 格式化情绪事件描述
    function formatMoodEventDescription(item: any) {
      const rawData = item.raw_data || {};
      const symbol = item.symbol || '';
      const subtype = item.event_subtype || '';
      
      switch(subtype) {
        case 'ma5_cross_up':
        case 'ma5_cross_down':
          return `${symbol}股票价格${rawData.real_time_close?.toFixed(2) || '0.00'}元，${subtype.includes('up') ? '上穿' : '下穿'}MA5均线(${rawData.daily_MA5?.toFixed(2) || '0.00'})，偏离${Math.abs(rawData.deviation_pct || 0).toFixed(2)}%`;
        case 'ma10_cross_up':
        case 'ma10_cross_down':
          return `${symbol}股票价格${rawData.real_time_close?.toFixed(2) || '0.00'}元，${subtype.includes('up') ? '上穿' : '下穿'}MA10均线(${rawData.daily_MA10?.toFixed(2) || '0.00'})，偏离${Math.abs(rawData.deviation_pct || 0).toFixed(2)}%`;
        case 'ma20_cross_up':
        case 'ma20_cross_down':
          return `${symbol}股票价格${rawData.real_time_close?.toFixed(2) || '0.00'}元，${subtype.includes('up') ? '上穿' : '下穿'}MA20均线(${rawData.daily_MA20?.toFixed(2) || '0.00'})，偏离${Math.abs(rawData.deviation_pct || 0).toFixed(2)}%`;
        case 'ma60_cross_up':
        case 'ma60_cross_down':
          return `${symbol}股票价格${rawData.real_time_close?.toFixed(2) || '0.00'}元，${subtype.includes('up') ? '上穿' : '下穿'}MA60均线(${rawData.daily_MA60?.toFixed(2) || '0.00'})，偏离${Math.abs(rawData.deviation_pct || 0).toFixed(2)}%`;
        default:
          return `${symbol}股票价格${rawData.real_time_close?.toFixed(2) || '0.00'}元，出现技术指标异常`;
      }
    }

    // 格式化个股事件描述
    function formatStockEventDescription(item: any) {
      const title = item['标题'] || '个股新闻';
      const content = item['内容'] || '';
      
      // 生成简要描述
      if (content) {
        const briefContent = content.length > 150 ? content.substring(0, 150) + '...' : content;
        return `${title}\n\n${briefContent}`;
      }
      
      return title;
    }
</script>

<template>
  <n-card class="large-card">
    <div class="container">
      <n-tabs
        type="line"
        animated
        size="large"
        justify-content="space-between"
        tab-style="background-color: ghostwhite; padding: 20px 80px 20px 80px;"
      >
        <!-- 宏观数据标签页 -->
        <n-tab-pane name="macro" tab="宏观">     
          <!-- 宏观数据表格 -->
          <n-data-table
            :columns="columns_macro"
            :data="messages_macro"
            :pagination="pagination"
            :bordered="false"
            :single-line="false"
            max-height="600px"
            :loading="loading.macro"
            class="macro-table"
            :row-props="(row) => ({
              style: {
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              },
              onMouseenter: (e) => {
                e.currentTarget.style.backgroundColor = '#fafafa';
                e.currentTarget.style.transform = 'translateY(-1px)';
              },
              onMouseleave: (e) => {
                e.currentTarget.style.backgroundColor = '';
                e.currentTarget.style.transform = '';
              },
              onClick: () => showDetail(row, 'macro')
            })"
          />
        </n-tab-pane>
        
        <!-- 行业数据标签页 -->
        <n-tab-pane name="industry" tab="行业">
          <!-- 行业数据表格 -->
          <n-data-table
            :columns="columns_industry"
            :data="messages_industry"
            :pagination="pagination"
            :bordered="false"
            :single-line="false"
            max-height="600px"
            :loading="loading.industry"
            class="macro-table"
            :row-props="(row) => ({
              style: {
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              },
              onMouseenter: (e) => {
                e.currentTarget.style.backgroundColor = '#fafafa';
                e.currentTarget.style.transform = 'translateY(-1px)';
              },
              onMouseleave: (e) => {
                e.currentTarget.style.backgroundColor = '';
                e.currentTarget.style.transform = '';
              },
              onClick: () => showDetail(row, 'industry')
            })"
          />
        </n-tab-pane>
        
        <!-- 个股数据标签页 -->
        <n-tab-pane name="stock" tab="个股">
          <!-- 个股数据表格 -->
          <n-data-table
            :columns="columns_stock"
            :data="messages_stock"
            :pagination="pagination"
            :bordered="false"
            :single-line="false"
            max-height="600px"
            :loading="loading.stock"
            class="macro-table"
            :row-props="(row) => ({
              style: {
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              },
              onMouseenter: (e) => {
                e.currentTarget.style.backgroundColor = '#fafafa';
                e.currentTarget.style.transform = 'translateY(-1px)';
              },
              onMouseleave: (e) => {
                e.currentTarget.style.backgroundColor = '';
                e.currentTarget.style.transform = '';
              },
              onClick: () => showDetail(row, 'stock')
            })"
          />
        </n-tab-pane>
        
        <!-- 情绪数据标签页 -->
        <n-tab-pane name="mood" tab="情绪">
          <!-- 情绪数据表格 -->
          <n-data-table
            :columns="columns_mood"
            :data="messages_mood"
            :pagination="pagination"
            :bordered="false"
            :single-line="false"
            max-height="600px"
            :loading="loading.mood"
            class="macro-table"
            :row-props="(row) => ({
              style: {
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              },
              onMouseenter: (e) => {
                e.currentTarget.style.backgroundColor = '#fafafa';
                e.currentTarget.style.transform = 'translateY(-1px)';
              },
              onMouseleave: (e) => {
                e.currentTarget.style.backgroundColor = '';
                e.currentTarget.style.transform = '';
              },
              onClick: () => showDetail(row, 'mood')
            })"
          />
        </n-tab-pane>
      </n-tabs>
    </div>
  </n-card>

  <!-- 事件详情对话框 -->
  <n-modal
    v-model:show="detailModalVisible"
    preset="card"
    :title="detailType === 'macro' ? '宏观事件详情' : 
            detailType === 'industry' ? '行业事件详情' :
            detailType === 'mood' ? '交易情绪详情' : '个股事件详情'"
    style="width: 700px; max-width: 90vw;"
    :bordered="false"
  >
    <div v-if="currentDetail" class="detail-content">
      <n-descriptions
        label-placement="left"
        :column="1"
        size="small"
        bordered
        :label-style="{ 
          width: '150px', 
          minWidth: '150px',
          fontWeight: '500',
          textAlign: 'center',
        }"
        :content-style="{ 
          maxWidth: '500px',
        }"
      >
        <!-- 基本信息 -->
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
        <n-descriptions-item v-if="detailType === 'industry'" label="事件描述">
          <div style="padding: 8px; background: #f8f9fa; border-radius: 4px;">
            <n-text style="white-space: pre-wrap; line-height: 1.6; font-size: 13px;">
              {{ formatIndustryEventDescription(currentDetail) }}
            </n-text>
          </div>
        </n-descriptions-item>

        <!-- 情绪事件描述 -->
        <n-descriptions-item v-if="detailType === 'mood'" label="事件描述">
          <div style="padding: 8px; background: #f8f9fa; border-radius: 4px;">
            <n-text style="white-space: pre-wrap; line-height: 1.6; font-size: 13px;">
              {{ formatMoodEventDescription(currentDetail) }}
            </n-text>
          </div>
        </n-descriptions-item>

        <!-- 个股事件描述 -->
        <n-descriptions-item v-if="detailType === 'stock'" label="事件描述">
          <div style="padding: 8px; background: #f8f9fa; border-radius: 4px;">
            <n-text style="white-space: pre-wrap; line-height: 1.6; font-size: 13px;">
              {{ formatStockEventDescription(currentDetail) }}
            </n-text>
          </div>
        </n-descriptions-item>

        <!-- 个股新闻内容 -->
        <n-descriptions-item v-if="detailType === 'stock' && currentDetail['内容']" label="完整内容">
          <div style="max-height: 200px; overflow-y: auto; padding: 8px; background: #f8f9fa; border-radius: 4px;">
            <n-text style="white-space: pre-wrap; line-height: 1.6; font-size: 13px;">
              {{ currentDetail['内容'] }}
            </n-text>
          </div>
        </n-descriptions-item>

        <!-- 宏观新闻内容 -->
        <n-descriptions-item v-if="detailType === 'macro' && currentDetail.raw_data?.新闻内容" label="新闻内容">
          <div style="max-height: 200px; overflow-y: auto; padding: 8px; background: #f8f9fa; border-radius: 4px;">
            <n-text style="white-space: pre-wrap; line-height: 1.6; font-size: 13px;">
              {{ currentDetail.raw_data.新闻内容 }}
            </n-text>
          </div>
        </n-descriptions-item>

        <n-descriptions-item label="事件类型">
          <n-text>{{ formatEventType(detailType) }}</n-text>
        </n-descriptions-item>

        <n-descriptions-item v-if="currentDetail.event_subtype || detailType === 'stock'" label="事件子类型">
          <n-text>
            {{ detailType === 'stock' ? '个股新闻' : formatEventSubtype(currentDetail.event_subtype) }}
          </n-text>
        </n-descriptions-item>

        <!-- 股票相关信息 -->
        <n-descriptions-item v-if="currentDetail.symbol || detailType === 'stock'" label="股票代码">
          <n-text>
            <span v-if="detailType === 'stock'">
              {{ 
                (() => {
                  const title = currentDetail['标题'] || '';
                  const content = currentDetail['内容'] || '';
                  const symbolMatch = title.match(/[0-9]{6}/) || content.match(/[0-9]{6}/);
                  return symbolMatch ? symbolMatch[0] : '-';
                })()
              }}
            </span>
            <span v-else>{{ currentDetail.symbol }}</span>
          </n-text>
        </n-descriptions-item>

        <n-descriptions-item v-if="currentDetail.board_name" label="板块名称">
          <n-text>{{ currentDetail.board_name }}</n-text>
        </n-descriptions-item>

        <!-- 影响和情感 -->
        <n-descriptions-item label="影响等级">
          <n-text>
            {{ 
              detailType === 'stock' 
                ? (() => {
                    const content = (currentDetail['内容'] || '').toLowerCase();
                    const title = (currentDetail['标题'] || '').toLowerCase();
                    const allText = title + ' ' + content;
                    
                    const criticalKeywords = ['暴跌', '崩盘', '破产', '重大利空', '退市', 'st'];
                    const highKeywords = ['大跌', '下滑', '亏损', '风险', '警告', '违规'];
                    const mediumKeywords = ['调整', '波动', '影响', '变化', '下跌'];
                    
                    if (criticalKeywords.some(keyword => allText.includes(keyword))) return '极高';
                    if (highKeywords.some(keyword => allText.includes(keyword))) return '高';
                    if (mediumKeywords.some(keyword => allText.includes(keyword))) return '中';
                    return '低';
                  })()
                : formatImpactLevel(currentDetail.impact_level)
            }}
          </n-text>
        </n-descriptions-item>

        <n-descriptions-item label="情感倾向">
          <n-text>
            {{ 
              detailType === 'stock' 
                ? (() => {
                    const content = (currentDetail['内容'] || '').toLowerCase();
                    const title = (currentDetail['标题'] || '').toLowerCase();
                    const allText = title + ' ' + content;
                    
                    const positiveKeywords = ['上涨', '涨停', '增长', '利好', '盈利', '业绩预增', '突破'];
                    const negativeKeywords = ['下跌', '跌停', '下滑', '利空', '亏损', '业绩预减', '风险'];
                    
                    if (positiveKeywords.some(keyword => allText.includes(keyword))) return '正面';
                    if (negativeKeywords.some(keyword => allText.includes(keyword))) return '负面';
                    return '中性';
                  })()
                : formatSentiment(currentDetail.sentiment)
            }}
          </n-text>
        </n-descriptions-item>

        <!-- 个股标题 -->
        <n-descriptions-item v-if="detailType === 'stock' && currentDetail['标题']" label="新闻标题">
          <n-text style="font-weight: 500; color: #333;">
            {{ currentDetail['标题'] }}
          </n-text>
        </n-descriptions-item>

        <!-- 实时价格数据（情绪和行业） -->
        <n-descriptions-item v-if="currentDetail.raw_data?.real_time_close" label="实时价格">
          <n-text>{{ currentDetail.raw_data.real_time_close.toFixed(2) }}</n-text>
        </n-descriptions-item>

        <n-descriptions-item v-if="currentDetail.raw_data?.price_change !== undefined" label="涨跌幅">
          <n-text :type="currentDetail.raw_data.price_change > 0 ? 'error' : 'success'">
            {{ currentDetail.raw_data.price_change > 0 ? '+' : '' }}{{ currentDetail.raw_data.price_change.toFixed(2) }}%
          </n-text>
        </n-descriptions-item>

        <!-- 板块数据（行业） -->
        <n-descriptions-item v-if="currentDetail.raw_data?.total_amount !== undefined" label="成交额">
          <n-text>{{ (currentDetail.raw_data.total_amount / 10000).toFixed(1) }} 亿元</n-text>
        </n-descriptions-item>

        <n-descriptions-item v-if="currentDetail.raw_data?.net_inflow !== undefined" label="净流入">
          <n-text :type="currentDetail.raw_data.net_inflow > 0 ? 'error' : 'success'">
            {{ currentDetail.raw_data.net_inflow > 0 ? '+' : '' }}{{ (currentDetail.raw_data.net_inflow / 10000).toFixed(1) }} 亿元
          </n-text>
        </n-descriptions-item>

        <n-descriptions-item v-if="currentDetail.raw_data?.rise_stocks !== undefined" label="上涨家数/总数">
          <n-text>
            {{ currentDetail.raw_data.rise_stocks }} / {{ currentDetail.raw_data.total_stocks }}
            ({{ ((currentDetail.raw_data.rise_stocks / currentDetail.raw_data.total_stocks) * 100).toFixed(1) }}%)
          </n-text>
        </n-descriptions-item>

        <n-descriptions-item v-if="currentDetail.raw_data?.leader_stock" label="领涨/跌股">
          <n-text>
            {{ currentDetail.raw_data.leader_stock }}
            <span :type="currentDetail.raw_data.leader_change > 0 ? 'error' : 'success'" style="margin-left: 8px; font-size: 12px;">
              {{ currentDetail.raw_data.leader_change > 0 ? '+' : '' }}{{ currentDetail.raw_data.leader_change?.toFixed(2) }}%
            </span>
          </n-text>
        </n-descriptions-item>

        <!-- 均线数据（情绪） -->
        <n-descriptions-item v-if="currentDetail.raw_data?.daily_MA5" label="MA5均线">
          <n-text>{{ currentDetail.raw_data.daily_MA5.toFixed(2) }}</n-text>
        </n-descriptions-item>

        <n-descriptions-item v-if="currentDetail.raw_data?.daily_MA10" label="MA10均线">
          <n-text>{{ currentDetail.raw_data.daily_MA10.toFixed(2) }}</n-text>
        </n-descriptions-item>

        <n-descriptions-item v-if="currentDetail.raw_data?.daily_MA20" label="MA20均线">
          <n-text>{{ currentDetail.raw_data.daily_MA20.toFixed(2) }}</n-text>
        </n-descriptions-item>

        <n-descriptions-item v-if="currentDetail.raw_data?.daily_MA60" label="MA60均线">
          <n-text>{{ currentDetail.raw_data.daily_MA60.toFixed(2) }}</n-text>
        </n-descriptions-item>

        <n-descriptions-item v-if="currentDetail.raw_data?.deviation_pct !== undefined" label="偏离度">
          <n-text>{{ currentDetail.raw_data.deviation_pct.toFixed(2) }}%</n-text>
        </n-descriptions-item>

        <!-- 触发规则（情绪） -->
        <n-descriptions-item v-if="currentDetail.trigger_rule" label="触发规则">
          <n-text>
            指标: {{ currentDetail.trigger_rule.metric }} 
            {{ currentDetail.trigger_rule.operator }} 
            {{ currentDetail.trigger_rule.threshold }}
            (当前值: {{ currentDetail.trigger_rule.value }})
          </n-text>
        </n-descriptions-item>

        <!-- 匹配关键词 -->
        <n-descriptions-item v-if="currentDetail.raw_data?.匹配关键词?.length > 0" label="匹配关键词">
          <n-space wrap>
            <n-tag 
              v-for="(keyword, index) in currentDetail.raw_data.匹配关键词" 
              :key="index" 
              size="small"
              type="default"
              style="margin: 2px;"
            >
              {{ keyword }}
            </n-tag>
          </n-space>
        </n-descriptions-item>

        <!-- 数据源 -->
        <n-descriptions-item v-if="currentDetail.data_source" label="数据源">
          <n-text>{{ currentDetail.data_source }}</n-text>
        </n-descriptions-item>
      </n-descriptions>
    </div>
    
    <template #footer>
      <n-space justify="end">
        <n-button @click="detailModalVisible = false">
          关闭
        </n-button>
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
  --gradient-primary: linear-gradient(135deg, #1890ff 0%, #165dff 100%);
  --gradient-success: linear-gradient(135deg, #52c41a 0%, #389e0d 100%);
  --gradient-warning: linear-gradient(135deg, #fa8c16 0%, #d46b08 100%);
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

// 标签页样式
.n-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  
  :deep(.n-tabs-nav) {
    background: white;
    border-bottom: 1px solid var(--border);
    border-radius: 8px 8px 0 0;
    padding: 0 20px;
    
    .n-tabs-tab {
      padding: 16px 24px;
      font-weight: 500;
      color: var(--text-light);
      transition: all 0.2s ease;
      
      &:hover {
        color: var(--primary);
      }
      
      &.n-tabs-tab--active {
        color: var(--primary);
        font-weight: 600;
        
        &::after {
          background: var(--primary);
          height: 3px;
          border-radius: 1.5px;
        }
      }
    }
  }
  
  :deep(.n-tab-pane) {
    flex: 1;
    display: flex;
    flex-direction: column;
    background: white;
    border-radius: 0 0 8px 8px;
    padding: 0;
  }
}

// 表格通用样式
.n-data-table {
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
}

// 宏观表格样式（现在也用于行业、个股、情绪表格）
.macro-table {
  :deep(.n-data-table) {
    .event-time-cell {
      display: flex;
      align-items: center;
      font-size: 12px;
      color: var(--text-light);
      font-family: 'SFMono-Regular', Consolas, monospace;
    }
    
    .description-preview {
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
    
    .impact-level {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      min-width: 40px;
      
      &.level-critical {
        background: rgba(255, 77, 79, 0.1);
        color: var(--color-critical);
        border: 1px solid rgba(255, 77, 79, 0.2);
      }
      
      &.level-high {
        background: rgba(250, 84, 28, 0.1);
        color: var(--color-high);
        border: 1px solid rgba(250, 84, 28, 0.2);
      }
      
      &.level-medium {
        background: rgba(250, 140, 22, 0.1);
        color: var(--color-medium);
        border: 1px solid rgba(250, 140, 22, 0.2);
      }
      
      &.level-low {
        background: rgba(217, 217, 217, 0.1);
        color: var(--color-low);
        border: 1px solid rgba(217, 217, 217, 0.2);
      }
    }
    
    .sentiment {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 600;
      min-width: 40px;
      
      &::before {
        content: '';
        display: inline-block;
        width: 6px;
        height: 6px;
        border-radius: 50%;
        margin-right: 4px;
      }
      
      &.sentiment-positive {
        background: rgba(82, 196, 26, 0.1);
        color: var(--color-positive);
        
        &::before {
          background: var(--color-positive);
        }
      }
      
      &.sentiment-negative {
        background: rgba(255, 77, 79, 0.1);
        color: var(--color-negative);
        
        &::before {
          background: var(--color-negative);
        }
      }
      
      &.sentiment-neutral {
        background: rgba(217, 217, 217, 0.1);
        color: var(--color-neutral);
        
        &::before {
          background: var(--color-neutral);
        }
      }
    }
    
    .symbol-cell {
      display: flex;
      align-items: center;
    }
    
    .symbol-text {
      font-family: 'SFMono-Regular', Consolas, monospace;
      font-size: 12px;
      font-weight: 500;
      padding: 2px 6px;
      background: rgba(22, 93, 255, 0.05);
      border-radius: 3px;
      color: #165dff;
      border: 1px solid rgba(22, 93, 255, 0.1);
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
        width: 120px;
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
  
  :deep(.n-tabs) {
    .n-tab-pane {
      padding: 0;
    }
    
    .n-tabs-nav {
      padding: 0 12px;
      
      .n-tabs-tab {
        padding: 12px 16px;
        min-width: auto;
        font-size: 14px;
      }
    }
  }
  
  .detail-grid {
    grid-template-columns: 1fr !important;
  }
  
  .n-data-table {
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

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.macro-table :deep(.n-data-table-tr) {
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

// 对话框滚动条样式
.enhanced-detail-content::-webkit-scrollbar {
  width: 6px;
}

.enhanced-detail-content::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.enhanced-detail-content::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
  
  &:hover {
    background: #a8a8a8;
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