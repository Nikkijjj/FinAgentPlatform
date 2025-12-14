<template>
  <div class="user-profile-container">
    <n-card :bordered="false" class="profile-card" size="large">
      <!-- 操作按钮区 -->
      <div class="action-buttons">
        <n-button v-if="!isEditing" type="primary" @click="enterEditMode" size="medium">
          <template #icon>
            <n-icon>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
              </svg>
            </n-icon>
          </template>
          编辑资料
        </n-button>
        <div v-else class="edit-buttons">
          <n-button type="default" @click="cancelEdit" size="medium" style="margin-right: 12px">
            <template #icon>
              <n-icon>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </n-icon>
            </template>
            取消
          </n-button>
          <n-button type="success" @click="handleSubmit" :loading="loading" size="medium">
            <template #icon>
              <n-icon>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </n-icon>
            </template>
            保存修改
          </n-button>
        </div>
      </div>

      <n-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-placement="top"
        label-width="80px"
        class="profile-form"
      >
        <n-card title="盘前分析模板" class="form-block view-card report-template-card">
          <n-form-item>
            <n-input
              type="textarea"
              v-model:value="formData.report_template.before_report"
              :disabled="!isEditing"
              :autosize="{ minRows: 15, maxRows: 30 }"
              placeholder="请输入或编辑报告模板内容..."
              class="report-template-editor"
              clearable
            />
          </n-form-item>
        </n-card>
        <n-card title="午间分析模板" class="form-block view-card report-template-card">
          <n-form-item>
            <n-input
              type="textarea"
              v-model:value="formData.report_template.noon_report"
              :disabled="!isEditing"
              :autosize="{ minRows: 15, maxRows: 30 }"
              placeholder="请输入或编辑报告模板内容..."
              class="report-template-editor"
              clearable
            />
          </n-form-item>
        </n-card>
        <n-card title="盘后分析模板" class="form-block view-card report-template-card">
          <n-form-item>
            <n-input
              type="textarea"
              v-model:value="formData.report_template.after_report"
              :disabled="!isEditing"
              :autosize="{ minRows: 15, maxRows: 30 }"
              placeholder="请输入或编辑报告模板内容..."
              class="report-template-editor"
              clearable
            />
          </n-form-item>
        </n-card>
      </n-form>
    </n-card>
  </div>
</template>

<script setup lang="ts">
  import { ref, reactive, onMounted, computed, watch } from 'vue';
  import { FormItemRule, useMessage } from 'naive-ui';
  import { useUser } from '@/store/modules/user';
  import { emptyStock, emptyWatchlistStock, UserInfoType } from '@/api/user/user';
  import { mockEmptyUserInfo } from '../../../../mock/user';
  import { parseStr, parseTime } from '@/api/time';
  import { getUserInvestmentProfile, updateUserInvestmentProfile } from '@/api/user/user';

  const formRef = ref<any>(null);
  const loading = ref(false);
  const message = useMessage();
  const userStore = useUser();

  const isDataReady = ref(false);
  const isEditing = ref(false); // 编辑模式状态
  const originalFormData = ref<UserInfoType>({ ...mockEmptyUserInfo }); // 原始数据备份

  // 适配新数据结构的表单数据
  const formData = reactive<UserInfoType>({
    name: '',
    account: '',
    password: '',
    report_template: {
      before_report:
        '你是一个专业的投资分析助理，请根据以下 JSON 信息生成【{date} 盘前投资分析报告】：\n' +
        '\n' +
        '要求：\n' +
        '1. 自动解析用户提供的信息，包括：\n' +
        '   - 投资目标、投资期限、预期收益、收益稳定性、风险承受能力、可接受最大亏损\n' +
        '   - 当前持仓股票及买入均价和数量\n' +
        '   - 自选关注股票列表\n' +
        '2. 报告需严格遵循以下结构，并结合宏观数据与市场预期，生成盘前策略建议：\n' +
        '\n' +
        '报告结构：\n' +
        '\n' +
        '1. 宏观与海外市场前瞻：\n' +
        '   - 隔夜美股与主要海外市场表现（涨跌幅、行业走势）\n' +
        '   - 国际宏观因素（美元指数、原油、黄金、国债收益率等）对A股的潜在影响\n' +
        '   - 全球流动性与风险偏好趋势判断\n' +
        '\n' +
        '2. 市场预期与情绪：\n' +
        '   - 主要指数技术面与情绪面分析（支撑位、压力位、成交量）\n' +
        '   - 行业板块强弱预判（政策驱动、资金关注度、题材热度）\n' +
        '   - 对用户持仓相关板块的预期影响\n' +
        '\n' +
        '3. 资金面前瞻：\n' +
        '   - 北向资金动向（近期连续流向趋势）\n' +
        '   - 主力资金行业偏好与潜在调仓方向\n' +
        '   - 对用户持仓个股的资金面风险与机会评估\n' +
        '\n' +
        '4. 持仓与关注股票策略建议：\n' +
        '   - 每只持仓股票：\n' +
        '       - 技术面位置与盘前支撑/压力分析\n' +
        '       - 与投资目标的匹配度（是否需要止盈/止损/继续持有）\n' +
        '       - 当日计划操作建议（低吸/观望/调仓）\n' +
        '   - 每只关注股票：\n' +
        '       - 当日潜在催化因素与交易机会\n' +
        '       - 风险提示与跟踪要点\n' +
        '       - 是否可作为轮动替代标的\n' +
        '\n' +
        '5. 今日策略总结：\n' +
        '   - 市场主线预判（政策线/成长线/防御线）\n' +
        '   - 预期波动区间与仓位建议\n' +
        '   - 风险提示与止损参考（结合用户可接受最大亏损）\n' +
        '   - 达成预期收益目标的策略调整建议\n' +
        '\n' +
        '注意事项：\n' +
        '- 分析需结合最新新闻、期货、夜盘与外盘表现。\n' +
        '- 所有建议需符合用户风险承受能力与收益目标。\n' +
        '- 用语应逻辑严谨、量化明确、可直接执行。',
      noon_report:
        '你是一个专业的投资分析助理，请根据以下 JSON 信息生成【{date} 午间投资分析报告】：\n' +
        '\n' +
        '要求：\n' +
        '1. 自动解析用户提供的信息，包括：\n' +
        '   - 投资目标、投资期限、预期收益、收益稳定性、风险承受能力、可接受最大亏损\n' +
        '   - 当前持仓股票及买入均价和数量\n' +
        '   - 自选关注股票列表\n' +
        '2. 报告需严格遵循以下结构，对上午盘面表现进行复盘并提供午后策略建议：\n' +
        '\n' +
        '报告结构：\n' +
        '\n' +
        '1. 上午市场表现：\n' +
        '   - 大盘与主要指数上午表现（涨跌幅、成交量、情绪特征）\n' +
        '   - 行业与概念板块涨跌情况（领涨、领跌、逻辑简评）\n' +
        '   - 对用户持仓板块的即时影响（强弱对比与轮动情况）\n' +
        '\n' +
        '2. 资金面观察：\n' +
        '   - 上午北向资金与主力资金流入流出特征\n' +
        '   - 热点板块资金分布与轮动迹象\n' +
        '   - 用户持仓个股的主力异动与风险信号\n' +
        '\n' +
        '3. 持仓复盘与风险监控：\n' +
        '   - 每只持仓股票上午表现（涨跌幅、成交额、量价结构）\n' +
        '   - 盈亏变化与风险区间评估（是否触及止盈/止损线）\n' +
        '   - 投资目标偏离度分析（短期回撤对长期目标的影响）\n' +
        '   - 午后操作建议（加仓/减仓/观望）\n' +
        '\n' +
        '4. 自选关注股追踪：\n' +
        '   - 上午活跃度与成交变化\n' +
        '   - 潜在消息面催化（新闻/公告/数据）\n' +
        '   - 午后观察重点与入场参考\n' +
        '\n' +
        '5. 午后策略展望：\n' +
        '   - 市场短线节奏判断（延续/反弹/分化）\n' +
        '   - 午后关注方向（主线板块、资金风格转换）\n' +
        '   - 仓位管理与风险控制建议（结合用户风险承受度与收益目标）\n' +
        '   - 若出现反转/异动信号的应对预案\n' +
        '\n' +
        '注意事项：\n' +
        '- 强调上午行情与午后潜在变化的衔接。\n' +
        '- 所有建议均需量化并结合用户风险承受区间。\n' +
        '- 分析风格应简洁有条理，便于午后即时执行。\n' +
        '\n' +
        '"""\n' +
        '\n' +
        'POST_MARKET_TEMPLATE = """\n' +
        '你是一个专业的投资分析助理，请根据以下 JSON 信息生成【{date} 盘后投资分析报告】：\n' +
        '\n' +
        '要求：\n' +
        '1. 自动解析用户提供的信息，包括：\n' +
        '   - 投资目标、投资期限、预期收益、收益稳定性、风险承受能力、可接受最大亏损\n' +
        '   - 当前持仓股票及买入均价和数量\n' +
        '   - 自选关注股票列表\n' +
        '2. 报告需严格遵循以下结构，并对用户持仓和关注股票进行详细分析：\n' +
        '\n' +
        '报告结构：\n' +
        '\n' +
        '1. 今日市场全景：\n' +
        '   - 大盘指数最终表现（涨跌幅、成交量、市场情绪总结）\n' +
        '   - 行业板块涨跌榜（领涨板块逻辑验证，领跌板块原因）\n' +
        '   - 对用户持仓相关板块的影响（银行、消费、科技等板块）\n' +
        '\n' +
        '2. 资金动向复盘：\n' +
        '   - 北向资金/主力资金全天流向（重点板块及个股）\n' +
        '   - 成交量能特征（是否有效放大/萎缩，与行情匹配度）\n' +
        '   - 对用户持仓股票的资金流入/流出分析\n' +
        '\n' +
        '3. 持仓及个股复盘：\n' +
        '   - 对每只持仓股票进行分析：\n' +
        '       - 当日价格波动及相对成本盈亏\n' +
        '       - 当日收益贡献度与风险指标（结合用户可接受的最大亏损）\n' +
        '       - 对用户投资目标的影响（是否偏离预期收益）\n' +
        '       - 明日操作参考（增持/减持/观望）\n' +
        '   - 对自选关注股票分析：\n' +
        '       - 当前市场表现与潜在机会\n' +
        '       - 潜在风险与对投资目标的影响\n' +
        '       - 明日跟踪建议\n' +
        '\n' +
        '4. 关键事件复盘：\n' +
        '   - 今日影响市场的核心事件（政策/数据/新闻）及实际影响\n' +
        '   - 板块轮动规律（资金从哪些板块流出，流入哪些板块）\n' +
        '   - 对用户持仓和关注股票的具体影响\n' +
        '\n' +
        '5. 明日展望与操作建议：\n' +
        '   - 大盘短期趋势判断（延续/反转信号）\n' +
        '   - 明日重点关注方向（政策/板块/数据）\n' +
        '   - 用户持仓策略建议：\n' +
        '       - 仓位配置参考\n' +
        '       - 风险提示（单股波动可能超出用户可接受风险）\n' +
        '       - 调整建议以更好贴合预期收益目标\n' +
        '\n' +
        '注意事项：\n' +
        '- 所有分析必须结合用户投资目标和风险偏好。\n' +
        '- 每只持仓和关注股票都必须有具体分析与操作建议。\n' +
        '- 报告应尽量量化用户收益/风险指标。\n' +
        '- 风格应专业、逻辑清晰、可直接指导投资操作。',
      after_report:
        '你是一个专业的投资分析助理，请根据以下 JSON 信息生成【{date} 盘中投资分析报告】：\n' +
        '\n' +
        '要求：\n' +
        '1. 自动解析用户提供的信息，包括：\n' +
        '   - 投资目标、投资期限、预期收益率、收益稳定性、风险承受能力、可接受最大亏损\n' +
        '   - 当前持仓股票（含买入均价、持仓数量）\n' +
        '   - 自选关注股票列表\n' +
        '2. 报告需基于盘中实时行情特征，结合资金流、热点演变和持仓动态，给出策略调整建议。\n' +
        '\n' +
        '报告结构：\n' +
        '\n' +
        '1. 当前市场概况：\n' +
        '   - 主要指数实时表现（涨跌幅、成交额、换手率）\n' +
        '   - 市场整体情绪（涨跌家数、赚钱效应、两市成交额对比）\n' +
        '   - 盘中热点板块与题材变化（资金主攻方向、轮动节奏）\n' +
        '   - 与上午或昨日收盘数据的对比（是否延续或反转）\n' +
        '\n' +
        '2. 盘中资金动向：\n' +
        '   - 北向资金、主力资金、游资动向（重点行业与个股）\n' +
        '   - 成交量能趋势（放量/缩量、主力净流入排名）\n' +
        '   - 对用户持仓及关注股票的资金流入流出特征\n' +
        '   - 盘中异动提示（急涨/急跌/成交量异常等）\n' +
        '\n' +
        '3. 持仓动态分析：\n' +
        '   - 每只持仓股票盘中表现：\n' +
        '       - 当前涨跌幅与相对成本盈亏\n' +
        '       - 资金流与盘口结构分析（主动买卖比例、封单强度）\n' +
        '       - 风险警戒线监控（是否接近止损/止盈阈值）\n' +
        '       - 结合投资目标与风险承受度的临时策略建议（继续持有 / 减仓 / 止盈 / 加仓）\n' +
        '   - 投资组合整体波动率与收益偏离度分析\n' +
        '\n' +
        '4. 关注股票追踪：\n' +
        '   - 盘中强势或异动表现（放量上涨、资金拉升、消息刺激）\n' +
        '   - 技术面突破或反转信号\n' +
        '   - 与用户投资目标的契合度（中短线机会或风险）\n' +
        '   - 实时跟踪建议（关注入场点 / 继续观望 / 设置提醒）\n' +
        '\n' +
        '5. 盘中策略调整建议：\n' +
        '   - 当前市场节奏判断（主升 / 分化 / 高位震荡）\n' +
        '   - 短线交易策略：\n' +
        '       - 若市场强势：建议关注哪些主线板块或龙头补涨机会\n' +
        '       - 若市场回落：建议如何控制仓位与回避风险\n' +
        '   - 对用户组合的动态调整参考：\n' +
        '       - 建议持仓比例\n' +
        '       - 止损/止盈区间更新\n' +
        '       - 是否需要调仓以更好匹配收益目标与风险承受力\n' +
        '\n' +
        '6. 实时风险提示：\n' +
        '   - 市场突发事件或新闻（政策、经济数据、突发公告）\n' +
        '   - 对相关板块和个股的即时影响\n' +
        '   - 风险控制建议（防止盘中情绪化操作）\n' +
        '\n' +
        '注意事项：\n' +
        '- 强调“盘中变化”的即时性与动态策略应对。\n' +
        '- 所有分析需结合用户投资目标与风险偏好。\n' +
        '- 建议需明确可执行（例如止盈区间、加仓比例、观望信号）。\n' +
        '- 风格应专业',
    },
    user_investment_profile: {
      personalized_investment_goals: {
        investment_tenure: {
          tenure_type: '',
          pecific_years: 0,
          tenure_description: '',
        },
        expected_return: {
          annualized_return_rate: 0,
          return_stability: '',
          return_description: '',
        },
        risk_tolerance: {
          risk_level: '',
          loss_tolerance_ratio: 0,
          risk_description: '',
        },
      },
      current_holdings: { holding_count: 0, holdings_list: [] },
      watchlist: { watchlist_count: 0, watchlist_list: [] },
    },
  });

  // 表单验证规则
  const formRules = {
    password: {
      validator: (rule: FormItemRule, value: string) => {
        if (!allow_change_password.value || !isEditing.value) return true;
        if (!value) return new Error('密码不能为空');
        if (!confirm_password.value) return new Error('请确认密码');
        if (confirm_password.value !== value) return new Error('两次输入密码不一致');
        return true;
      },
      trigger: 'blur',
    },
  };

  // 下拉选项
  const term_options = [
    { label: '短期', value: 'short_term' },
    { label: '中期', value: 'medium_term' },
    { label: '长期', value: 'long_term' },
  ];
  const stability_options = [
    { label: '稳定优先', value: 'stable' },
    { label: '平衡', value: 'moderate' },
    { label: '灵活可变', value: 'flexible' },
  ];
  const risk_options = [
    { label: '保守', value: 'conservative' },
    { label: '平衡', value: 'moderate' },
    { label: '进取', value: 'aggressive' },
    { label: '激进', value: 'radical' },
  ];

  // 密码修改相关
  const allow_change_password = ref(false);
  const old_password = ref('');
  const confirm_password = ref('');
  const pass = computed(() => {
    if (!old_password.value) return '';
    return old_password.value === formData.password ? 'success' : 'error';
  });

  // 监听密码验证状态
  const stopWatchPassword = watch(pass, (newVal) => {
    if (newVal === 'success' && isEditing.value) {
      allow_change_password.value = true;
      stopWatchPassword();
    }
  });

  // 进入编辑模式
  const enterEditMode = () => {
    isEditing.value = true;
    originalFormData.value = JSON.parse(JSON.stringify(formData)); // 备份当前数据
    allow_change_password.value = false;
    old_password.value = '';
    confirm_password.value = '';
  };

  // 取消编辑（恢复原始数据）
  const cancelEdit = () => {
    isEditing.value = false;
    Object.assign(formData, JSON.parse(JSON.stringify(originalFormData.value)));
    allow_change_password.value = false;
    old_password.value = '';
    confirm_password.value = '';
  };

  // 持仓数量变更
  const changeHoldingCount = () => {
    const targetCount = formData.user_investment_profile.current_holdings.holding_count ?? 0;
    const currentList = formData.user_investment_profile.current_holdings.holdings_list;

    // 新增持仓
    while (currentList.length < targetCount) {
      currentList.push({ ...emptyStock });
    }
    // 减少持仓（需确认）
    if (currentList.length > targetCount) {
      if (confirm('当前操作可能会引起数据丢失')) {
        currentList.splice(targetCount);
      } else {
        formData.user_investment_profile.current_holdings.holding_count = currentList.length;
      }
    }
  };

  // 删除持仓
  const deleteHoldingStock = (index: number) => {
    formData.user_investment_profile.current_holdings.holdings_list.splice(index, 1);
    formData.user_investment_profile.current_holdings.holding_count--;
  };

  // 新增持仓
  const addHoldingStock = () => {
    formData.user_investment_profile.current_holdings.holdings_list.push({ ...emptyStock });
    formData.user_investment_profile.current_holdings.holding_count++;
  };

  // 自选股数量变更
  const changeWatchlistCount = () => {
    const targetCount = formData.user_investment_profile.watchlist.watchlist_count ?? 0;
    const currentList = formData.user_investment_profile.watchlist.watchlist_list;

    while (currentList.length < targetCount) {
      currentList.push({ ...emptyWatchlistStock });
    }
    if (currentList.length > targetCount) {
      if (confirm('当前操作可能会引起数据丢失')) {
        currentList.splice(targetCount);
      } else {
        formData.user_investment_profile.watchlist.watchlist_count = currentList.length;
      }
    }
  };

  // 删除自选股
  const deleteWatchlistStock = (index: number) => {
    formData.user_investment_profile.watchlist.watchlist_list.splice(index, 1);
    formData.user_investment_profile.watchlist.watchlist_count--;
  };

  // 新增自选股
  const addWatchlistStock = () => {
    formData.user_investment_profile.watchlist.watchlist_list.push({ ...emptyWatchlistStock });
    formData.user_investment_profile.watchlist.watchlist_count++;
  };

  // 初始化数据
  onMounted(async () => {
    return;
    loading.value = true;
    try {
      const userProfile = await getUserInvestmentProfile(userStore.getToken);

      // 直接覆盖表单数据
      Object.assign(formData, userProfile.data);
      // Object.assign(formData, JSON.parse(JSON.stringify(userProfile)));

      // 时间格式转换
      formData.user_investment_profile.current_holdings.holdings_list.forEach((stock) => {
        if (typeof stock.purchase_time === 'string') {
          stock.purchase_time = parseTime(stock.purchase_time);
        }
      });
      formData.user_investment_profile.watchlist.watchlist_list.forEach((stock) => {
        if (typeof stock.add_time === 'string') {
          stock.add_time = parseTime(stock.add_time);
        }
      });

      originalFormData.value = JSON.parse(JSON.stringify(formData));
      isDataReady.value = true;
    } catch (e) {
      message.error('数据加载失败');
    } finally {
      loading.value = false;
    }
  });

  // 保存时转换时间格式
  const transTimeToString = (userInfo: UserInfoType) => {
    userInfo.user_investment_profile.current_holdings.holdings_list.forEach((stock) => {
      stock.purchase_time = parseStr(stock.purchase_time);
    });
    userInfo.user_investment_profile.watchlist.watchlist_list.forEach((stock) => {
      stock.add_time = parseStr(stock.add_time);
    });
  };

  // 提交表单
  const handleSubmit = async () => {
    const valid = await formRef.value.validate();
    if (!valid) {
      message.error('信息填写有误');
      return;
    }

    loading.value = true;
    const transData = JSON.parse(JSON.stringify(formData));
    transTimeToString(transData);

    // 构造新接口要求的参数结构
    const requestParams = {
      user_investment_profile: transData.user_investment_profile,
      user_report_template: transData.report_template,
    };

    try {
      // 1. 更新用户信息（可选，根据store逻辑调整）
      userStore.setUserInfo(transData);

      // 2. 调用接口时传入新结构的参数
      const response = await updateUserInvestmentProfile(userStore.getToken, requestParams);

      if (response.code === 0) {
        message.success(response.msg);
        originalFormData.value = JSON.parse(JSON.stringify(formData));
        isEditing.value = false;
        allow_change_password.value = false;
        old_password.value = '';
        confirm_password.value = '';
      } else {
        message.error(response.msg);
      }
    } catch (e) {
      message.error('网络异常，修改失败');
    } finally {
      loading.value = false;
    }
  };
</script>

<style scoped>
  .user-profile-container {
    height: 100%;
    padding: 20px;
    background-color: #f8f9fa;
  }

  .profile-card {
    background: #fff;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    border-radius: 12px;
    overflow: hidden;
  }

  .action-buttons {
    padding: 20px 24px;
    border-bottom: 1px solid #eef1f4;
    display: flex;
    justify-content: flex-end;
    margin-bottom: 15px;
  }

  .edit-buttons {
    display: flex;
    gap: 12px;
  }

  .form-block {
    padding: 24px;
    margin-bottom: 16px;
  }

  /* 个人信息展示样式 - 大幅美化 */
  .info-view {
    padding: 16px 0;
  }

  .info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 20px;
  }

  .info-item {
    display: flex;
    align-items: flex-start;
    padding: 8px;
    /* background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); */
    background: #ffffff;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    transition: all 0.3s ease;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  }

  .info-item:hover {
    transform: translateY(-2px);
    /* box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1); */
    box-shadow: 0 5px 10px rgba(59, 130, 246, 0.1);
    border-color: #dadde0;
    /* background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%); */
    background: #ffffff;
  }

  .info-icon {
    flex-shrink: 0;
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, rgba(45, 140, 240, 0.8) 50%);
    border-radius: 12px;
    margin-right: 20px;
    color: white;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
  }

  .info-content {
    flex: 1;
  }

  .info-label {
    font-size: 13px;
    font-weight: 500;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
  }

  .info-value {
    font-size: 15px;
    font-weight: 600;
    color: #464b52;
    line-height: 1.5;
    word-break: break-word;
  }

  .password-tag {
    margin-right: 12px;
    padding: 6px 12px;
    font-weight: 500;
  }

  .password-hint {
    font-size: 13px;
    color: #94a3b8;
    display: inline-block;
    margin-top: 8px;
    font-style: italic;
  }

  /* 编辑模式样式 */
  .info-edit {
    padding: 12px 0;
    animation: slideIn 0.3s ease;
  }

  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(-10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  /* 其他样式保持不变 */
  .view-card {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    transition: box-shadow 0.3s;
  }

  .view-card:hover {
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.08);
  }

  .count-input {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
  }

  .form-group {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    padding-bottom: 16px;
  }

  .stock-card {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    width: 30%;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  }

  /* 持仓情况查看样式 */
  .holdings-view,
  .watchlist-view {
    padding: 16px 0;
  }

  .holdings-grid,
  .watchlist-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 20px;
  }

  .holding-card,
  .watchlist-card {
    /* background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); */
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 20px;
    transition: all 0.3s ease;
    box-shadow: 0 5px 10px rgba(0, 0, 0, 0.04);
    position: relative;
    overflow: hidden;
  }

  .holding-card:hover,
  .watchlist-card:hover {
    transform: translateY(-4px);
    /* box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1); */
    box-shadow: 0 5px 15px rgba(59, 130, 246, 0.1);
    border-color: #cbd5e1;
    /* background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%); */
    background: #ffffff;
  }

  .holding-header,
  .watchlist-header {
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 1px solid #e2e8f0;
  }

  .stock-code {
    font-size: 16.5px;
    font-weight: 600;
    color: #545456;
    margin-bottom: 4px;
  }

  .stock-name {
    font-size: 14px;
    color: #64748b;
  }

  .holding-details,
  .watchlist-details {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .detail-item {
    display: flex;
    align-items: flex-start;
  }

  .detail-icon {
    flex-shrink: 0;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, rgba(45, 140, 240, 0.8) 50%);
    border-radius: 8px;
    margin-right: 12px;
    color: white;
    box-shadow: 0 2px 6px rgba(59, 130, 246, 0.2);
  }

  .detail-content {
    flex: 1;
  }

  .detail-label {
    font-size: 12px;
    font-weight: 500;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
  }

  .detail-value {
    font-size: 14px;
    font-weight: 500;
    color: #1e293b;
    line-height: 1.4;
  }

  /* 自选股标签 */
  .watchlist-tag {
    position: absolute;
    top: 16px;
    right: 16px;
  }

  /* 空状态样式 */
  .empty-state {
    padding: 40px 20px;
    text-align: center;
    background: #f8fafc;
    border-radius: 12px;
    border: 1px dashed #e2e8f0;
  }

  /* 响应式调整 */
  @media (max-width: 768px) {
    .holdings-grid,
    .watchlist-grid {
      grid-template-columns: 1fr;
      gap: 16px;
    }

    .holding-card,
    .watchlist-card {
      padding: 16px;
    }

    .detail-item {
      align-items: center;
    }

    .detail-icon {
      margin-right: 16px;
    }
  }

  .holding-card .detail-icon,
  .watchlist-card .detail-icon {
    background: linear-gradient(135deg, #5aaaf4 100%);
  }

  @media (max-width: 1200px) {
    .stock-card {
      width: 45%;
    }
  }

  @media (max-width: 768px) {
    .stock-card {
      width: 100%;
    }

    .info-grid {
      grid-template-columns: 1fr;
      gap: 16px;
    }

    .info-item {
      padding: 20px;
      flex-direction: column;
      align-items: center;
      text-align: center;
    }

    .info-icon {
      margin-right: 0;
      margin-bottom: 16px;
    }

    .action-buttons {
      flex-direction: column;
      gap: 12px;
    }

    .edit-buttons {
      width: 100%;
      flex-direction: column;
    }

    .info-value {
      font-size: 18px;
    }
  }

  @media (max-width: 480px) {
    .user-profile-container {
      padding: 12px;
    }

    .form-block {
      padding: 16px;
    }

    .info-item {
      padding: 16px;
    }

    .info-value {
      font-size: 16px;
    }
  }

  .add-stock-btn {
    width: 30%;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    border: 1px dashed #e5e7eb;
    border-radius: 6px;
    cursor: pointer;
    transition: border-color 0.3s;
  }

  .add-stock-btn:hover {
    border-color: #27ba9b;
  }

  /* 报告模板编辑器样式 */
  .report-template-card {
    padding: 20px;
  }

  .report-template-editor {
    width: 100%;
    font-size: 14px;
    line-height: 1.6;
    padding: 12px;
    border-radius: 6px;
    resize: vertical;
  }

  .report-template-editor:disabled {
    background-color: #f8f9fa;
    opacity: 1;
    color: #333;
  }
</style>
