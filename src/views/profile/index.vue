<template>
  <div class="user-profile-container">
    <n-card :bordered="false" class="profile-card" size="large">
      <!-- 操作按钮区 -->
      <div class="action-buttons">
        <n-button v-if="!isEditing" type="primary" @click="enterEditMode" size="medium">
          编辑资料
        </n-button>
        <div v-else class="edit-buttons">
          <n-button type="default" @click="cancelEdit" size="medium" style="margin-right: 12px">
            取消
          </n-button>
          <n-button type="success" @click="handleSubmit" :loading="loading" size="medium">
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
        <n-collapse>
          <n-collapse-item title="个人信息" name="1">
            <n-card class="form-block view-card">
              <n-form-item label="昵称">
                <n-input v-model:value="formData.name" :disabled="!isEditing" />
              </n-form-item>
              <n-form-item label="账号">
                <n-input v-model:value="formData.account" :disabled="!isEditing" />
              </n-form-item>
              <n-form-item label="修改密码" path="password" v-show="allow_change_password">
                <n-input
                  type="password"
                  clearable
                  showPasswordOn="click"
                  v-model:value="formData.password"
                  placeholder="输入新密码"
                  :disabled="!isEditing"
                />
              </n-form-item>
              <n-form-item label="密码" v-show="!allow_change_password">
                <n-input
                  type="password"
                  clearable
                  showPasswordOn="click"
                  :status="pass"
                  v-model:value="old_password"
                  placeholder="内容已隐藏（请先输入原密码）"
                  :disabled="!isEditing"
                />
              </n-form-item>
              <n-form-item
                label="确认新密码"
                path="password"
                :style="{ visibility: allow_change_password ? 'visible' : 'hidden' }"
              >
                <n-input
                  type="password"
                  clearable
                  showPasswordOn="click"
                  v-model:value="confirm_password"
                  placeholder="请确认密码"
                  :disabled="!isEditing"
                />
              </n-form-item>
            </n-card>
          </n-collapse-item>
          <n-collapse-item title="个性化投资目标" name="2">
            <n-card class="form-block view-card">
              <n-form-item label="投资类别">
                <n-select
                  :options="term_options"
                  v-model:value="
                    formData.user_investment_profile.personalized_investment_goals.investment_tenure
                      .tenure_type
                  "
                  :disabled="!isEditing"
                />
              </n-form-item>
              <n-form-item label="投资年限">
                <n-input-number
                  clearable
                  :min="0"
                  v-model:value="
                    formData.user_investment_profile.personalized_investment_goals.investment_tenure
                      .specific_years
                  "
                  :disabled="!isEditing"
                />
              </n-form-item>
              <n-form-item label="投资描述">
                <n-input
                  clearable
                  type="textarea"
                  :autosize="{ minRows: 1 }"
                  style="min-width: 100%"
                  v-model:value="
                    formData.user_investment_profile.personalized_investment_goals.investment_tenure
                      .tenure_description
                  "
                  :disabled="!isEditing"
                />
              </n-form-item>
            </n-card>
          </n-collapse-item>
          <n-collapse-item title="投资期望" name="3">
            <n-card class="form-block view-card">
              <n-form-item label="年利率">
                <n-input-number
                  clearable
                  :min="0"
                  :max="100"
                  :precision="2"
                  v-model:value="
                    formData.user_investment_profile.personalized_investment_goals.expected_return
                      .annualized_return_rate
                  "
                  :disabled="!isEditing"
                >
                  <template #suffix> % </template>
                </n-input-number>
              </n-form-item>
              <n-form-item label="收益稳定性">
                <n-select
                  :options="stability_options"
                  v-model:value="
                    formData.user_investment_profile.personalized_investment_goals.expected_return
                      .return_stability
                  "
                  :disabled="!isEditing"
                />
              </n-form-item>
              <n-form-item label="收益描述">
                <n-input
                  clearable
                  type="textarea"
                  :autosize="{ minRows: 1 }"
                  style="min-width: 100%"
                  v-model:value="
                    formData.user_investment_profile.personalized_investment_goals.expected_return
                      .return_description
                  "
                  :disabled="!isEditing"
                />
              </n-form-item>
            </n-card>
          </n-collapse-item>
          <n-collapse-item title="风险承受能力" name="4">
            <n-card class="form-block view-card">
              <n-form-item label="可承受亏损率">
                <n-input-number
                  clearable
                  :min="0"
                  :max="100"
                  :precision="2"
                  v-model:value="
                    formData.user_investment_profile.personalized_investment_goals.risk_tolerance
                      .loss_tolerance_ratio
                  "
                  :disabled="!isEditing"
                >
                  <template #suffix> % </template>
                </n-input-number>
              </n-form-item>
              <n-form-item label="风险等级">
                <n-select
                  :options="risk_options"
                  v-model:value="
                    formData.user_investment_profile.personalized_investment_goals.risk_tolerance
                      .risk_level
                  "
                  :disabled="!isEditing"
                />
              </n-form-item>
              <n-form-item label="风险描述">
                <n-input
                  clearable
                  type="textarea"
                  :autosize="{ minRows: 1 }"
                  style="min-width: 100%"
                  v-model:value="
                    formData.user_investment_profile.personalized_investment_goals.risk_tolerance
                      .risk_description
                  "
                  :disabled="!isEditing"
                />
              </n-form-item>
            </n-card>
          </n-collapse-item>
          <n-collapse-item title="持仓情况" name="5">
            <n-card class="form-block view-card">
              <!-- 数量输入区：仅编辑模式显示 -->
              <div class="count-input" v-if="isEditing">
                <n-form-item label="数量">
                  <n-input-number
                    clearable
                    :min="0"
                    v-model:value="formData.user_investment_profile.current_holdings.holding_count"
                    :disabled="!isEditing"
                  />
                </n-form-item>
                <n-button @click="changeHoldingCount" :disabled="!isEditing">确认</n-button>
              </div>
              <!-- 持仓列表 -->
              <div class="form-group">
                <n-card
                  class="stock-card"
                  :closable="isEditing"
                  v-for="(stock, index) in formData.user_investment_profile.current_holdings
                    .holdings_list"
                  :key="index"
                  @close="deleteHoldingStock(index)"
                >
                  <n-form-item label="股票代码">
                    <n-input clearable v-model:value="stock.stock_code" :disabled="!isEditing" />
                  </n-form-item>
                  <n-form-item label="股票名称">
                    <n-input clearable v-model:value="stock.stock_name" :disabled="!isEditing" />
                  </n-form-item>
                  <n-form-item label="持有数量">
                    <n-input-number
                      clearable
                      :min="0"
                      v-model:value="stock.holding_quantity"
                      :disabled="!isEditing"
                    />
                  </n-form-item>
                  <n-form-item label="买入价格">
                    <n-input-number
                      clearable
                      :min="0"
                      :precision="2"
                      v-model:value="stock.purchase_price"
                      :disabled="!isEditing"
                    />
                  </n-form-item>
                  <n-form-item label="买入时间">
                    <n-date-picker
                      type="datetime"
                      clearable
                      v-model:value="stock.purchase_time"
                      :disabled="!isEditing"
                    />
                  </n-form-item>
                  <n-form-item label="股票描述">
                    <n-input
                      clearable
                      type="textarea"
                      :autosize="{ minRows: 1 }"
                      style="min-width: 100%"
                      v-model:value="stock.holding_remark"
                      :disabled="!isEditing"
                    />
                  </n-form-item>
                </n-card>
                <!-- 新增持仓按钮：仅编辑模式显示 -->
                <n-button text @click="addHoldingStock" v-if="isEditing" class="add-stock-btn">
                  <n-icon>
                    <svg
                      width="24"
                      height="24"
                      viewBox="0 0 24 24"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <rect
                        x="3"
                        y="3"
                        width="18"
                        height="18"
                        rx="2"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                      />
                      <line
                        x1="12"
                        y1="7"
                        x2="12"
                        y2="17"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                      />
                      <line
                        x1="7"
                        y1="12"
                        x2="17"
                        y2="12"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                      />
                    </svg>
                  </n-icon>
                </n-button>
              </div>
            </n-card>
          </n-collapse-item>
          <n-collapse-item title="自选股信息" name="6">
            <n-card class="form-block view-card">
              <!-- 数量输入区：仅编辑模式显示 -->
              <div class="count-input" v-if="isEditing">
                <n-form-item label="数量">
                  <n-input-number
                    clearable
                    :min="0"
                    v-model:value="formData.user_investment_profile.watchlist.watchlist_count"
                    :disabled="!isEditing"
                  />
                </n-form-item>
                <n-button @click="changeWatchlistCount" :disabled="!isEditing">确认</n-button>
              </div>
              <!-- 自选股列表 -->
              <div class="form-group">
                <n-card
                  class="stock-card"
                  :closable="isEditing"
                  v-for="(stock, index) in formData.user_investment_profile.watchlist
                    .watchlist_list"
                  :key="index"
                  @close="deleteWatchlistStock(index)"
                >
                  <n-form-item label="股票代码">
                    <n-input clearable v-model:value="stock.stock_code" :disabled="!isEditing" />
                  </n-form-item>
                  <n-form-item label="股票名称">
                    <n-input clearable v-model:value="stock.stock_name" :disabled="!isEditing" />
                  </n-form-item>
                  <n-form-item label="添加时间">
                    <n-date-picker
                      type="datetime"
                      clearable
                      v-model:value="stock.add_time"
                      :disabled="!isEditing"
                    />
                  </n-form-item>
                  <n-form-item label="自选股描述">
                    <n-input
                      clearable
                      type="textarea"
                      :autosize="{ minRows: 1 }"
                      style="min-width: 100%"
                      v-model:value="stock.watch_remark"
                      :disabled="!isEditing"
                    />
                  </n-form-item>
                </n-card>
                <!-- 新增自选股按钮：仅编辑模式显示 -->
                <n-button text @click="addWatchlistStock" v-if="isEditing" class="add-stock-btn">
                  <n-icon>
                    <svg
                      width="24"
                      height="24"
                      viewBox="0 0 24 24"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <rect
                        x="3"
                        y="3"
                        width="18"
                        height="18"
                        rx="2"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                      />
                      <line
                        x1="12"
                        y1="7"
                        x2="12"
                        y2="17"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                      />
                      <line
                        x1="7"
                        y1="12"
                        x2="17"
                        y2="12"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                      />
                    </svg>
                  </n-icon>
                </n-button>
              </div>
            </n-card>
          </n-collapse-item>
          <!-- 报告模板设置：大文本编辑器 -->
          <n-collapse-item title="报告模板设置" name="7">
            <n-card class="form-block view-card report-template-card">
              <n-form-item label="报告模板内容">
                <n-input
                  type="textarea"
                  v-model:value="formData.report_template"
                  :disabled="!isEditing"
                  :autosize="{ minRows: 15, maxRows: 30 }"
                  placeholder="请输入或编辑报告模板内容..."
                  class="report-template-editor"
                  clearable
                />
              </n-form-item>
            </n-card>
          </n-collapse-item>
        </n-collapse>
      </n-form>
    </n-card>
  </div>
</template>

<script setup lang="ts">
  import { ref, reactive, onMounted, computed, watch } from 'vue';
  import { FormItemRule, useMessage } from 'naive-ui';
  import { useUser } from '@/store/modules/user';
  import { emptyStock, emptyWatchlistStock, UserInfoType } from '@/api/user/user';
  import { mockEmptyUserInfo } from '../../../mock/user';
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
    report_template: '',
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
    loading.value = true;
    try {
      const userProfile = await getUserInvestmentProfile(userStore.getToken);
      console.log('userProfile response:', userProfile);

      // 直接覆盖表单数据
      Object.assign(formData, userProfile.data);
      console.log('user profile', formData);
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
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
    border-radius: 8px;
  }

  .action-buttons {
    padding: 16px;
    border-bottom: 1px solid #e5e7eb;
    display: flex;
    justify-content: flex-end;
  }

  .edit-buttons {
    display: flex;
    gap: 8px;
  }

  .form-block {
    padding: 16px;
    margin-bottom: 16px;
  }

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
  @media (max-width: 1200px) {
    .stock-card {
      width: 45%;
    }
  }
  @media (max-width: 768px) {
    .stock-card {
      width: 100%;
    }
    .action-buttons {
      flex-direction: column;
      gap: 8px;
    }
    .edit-buttons {
      width: 100%;
      flex-direction: column;
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
