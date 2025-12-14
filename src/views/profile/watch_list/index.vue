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
        <n-card title="自选股信息" class="form-block view-card">
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

          <!-- 查看模式 -->
          <div v-if="!isEditing" class="watchlist-view">
            <div
              class="watchlist-grid"
              v-if="formData.user_investment_profile.watchlist.watchlist_list?.length > 0"
            >
              <div
                class="watchlist-card"
                v-for="(stock, index) in formData.user_investment_profile.watchlist.watchlist_list"
                :key="index"
              >
                <div class="watchlist-header">
                  <div class="stock-code">{{ stock.stock_code || '未设置' }}</div>
                  <div class="stock-name">{{ stock.stock_name || '未设置名称' }}</div>
                </div>

                <div class="watchlist-details">
                  <div class="detail-item">
                    <div class="detail-icon">
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
                        <circle cx="12" cy="12" r="10" />
                        <polyline points="12 6 12 12 16 14" />
                      </svg>
                    </div>
                    <div class="detail-content">
                      <div class="detail-label">添加时间</div>
                      <div class="detail-value">{{
                        stock.add_time
                          ? new Date(stock.add_time).toLocaleString('zh-CN', {
                              year: 'numeric',
                              month: '2-digit',
                              day: '2-digit',
                              hour: '2-digit',
                              minute: '2-digit',
                            })
                          : '未设置'
                      }}</div>
                    </div>
                  </div>

                  <div class="detail-item full-width" v-if="stock.watch_remark">
                    <div class="detail-icon">
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
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                      </svg>
                    </div>
                    <div class="detail-content">
                      <div class="detail-label">自选股描述</div>
                      <div class="detail-value description-text">{{ stock.watch_remark }}</div>
                    </div>
                  </div>
                </div>

                <div class="watchlist-tag">
                  <n-tag size="small" type="info" round> 自选关注 </n-tag>
                </div>
              </div>
            </div>

            <div class="empty-state" v-else>
              <n-empty description="暂无自选股">
                <template #icon>
                  <n-icon>
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="48"
                      height="48"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="1"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    >
                      <path
                        d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"
                      />
                    </svg>
                  </n-icon>
                </template>
              </n-empty>
            </div>
          </div>

          <!-- 编辑模式 -->
          <div v-else class="form-group">
            <n-card
              class="stock-card"
              :closable="isEditing"
              v-for="(stock, index) in formData.user_investment_profile.watchlist.watchlist_list"
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
                <svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
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
      before_report: '',
      noon_report: '',
      after_report: '',
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
