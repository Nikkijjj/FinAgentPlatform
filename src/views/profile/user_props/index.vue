<template>
  <div class="user-profile-container">
    <n-card :bordered="false" class="profile-card" size="large">
      <!-- 头部操作区 -->
      <div class="profile-header">
        <div class="header-title">
          <h2 class="title-text">账号管理</h2>
          <p class="title-subtext">您的个人信息管理中心</p>
        </div>
        <div class="action-buttons">
          <n-button
            v-if="!isEditing"
            type="primary"
            @click="enterEditMode"
            size="medium"
            class="edit-btn"
          >
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
            <n-button type="default" @click="cancelEdit" size="medium" class="cancel-btn" ghost>
              取消
            </n-button>
            <n-button
              type="success"
              @click="handleSubmit"
              :loading="loading"
              size="medium"
              class="save-btn"
            >
              保存更改
            </n-button>
          </div>
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
        <!-- 个人信息卡片 -->
        <n-card class="info-card">
          <template #header>
            <div class="card-header">
              <div class="card-title">
                <n-icon size="25">
                  <UserOutlined />
                </n-icon>
                <h3 class="card-title-text">个人信息</h3>
              </div>
              <n-tag :bordered="false" size="small" type="info" round>
                {{ isEditing ? '编辑模式' : '查看模式' }}
              </n-tag>
            </div>
          </template>

          <!-- 查看模式 -->
          <div v-if="!isEditing" class="info-view">
            <div class="info-grid">
              <div class="info-item">
                <div class="info-icon-wrapper">
                  <div class="info-icon">
                    <n-icon>
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="20"
                        height="20"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      >
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                        <circle cx="12" cy="7" r="4" />
                      </svg>
                    </n-icon>
                  </div>
                </div>
                <div class="info-content">
                  <div class="info-label">昵称</div>
                  <div class="info-value">{{ formData.name || '未设置' }}</div>
                </div>
              </div>

              <div class="info-item">
                <div class="info-icon-wrapper">
                  <div class="info-icon">
                    <n-icon>
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="20"
                        height="20"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      >
                        <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                        <line x1="16" y1="2" x2="16" y2="6" />
                        <line x1="8" y1="2" x2="8" y2="6" />
                        <line x1="3" y1="10" x2="21" y2="10" />
                      </svg>
                    </n-icon>
                  </div>
                </div>
                <div class="info-content">
                  <div class="info-label">账号</div>
                  <div class="info-value">{{ formData.account || '未设置' }}</div>
                </div>
              </div>

              <div class="info-item">
                <div class="info-icon-wrapper">
                  <div class="info-icon">
                    <n-icon>
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="20"
                        height="20"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      >
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                      </svg>
                    </n-icon>
                  </div>
                </div>
                <div class="info-content">
                  <div class="info-label">密码状态</div>
                  <div class="info-value">
                    <n-tag
                      size="medium"
                      type="success"
                      round
                      class="password-tag"
                      :bordered="false"
                    >
                      <template #icon>
                        <n-icon>
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                          >
                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                            <polyline points="22 4 12 14.01 9 11.01" />
                          </svg>
                        </n-icon>
                      </template>
                      已设置
                    </n-tag>
                    <div class="password-hint">
                      <n-text depth="3">点击"编辑资料"按钮修改密码</n-text>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 编辑模式 -->
          <div v-else class="info-edit">
            <div class="edit-form-grid">
              <n-form-item label="昵称" class="form-item">
                <n-input
                  v-model:value="formData.name"
                  placeholder="请输入您的昵称"
                  size="large"
                  round
                  :input-props="{ style: { padding: '12px 16px' } }"
                />
              </n-form-item>

              <n-form-item label="账号" class="form-item">
                <n-input
                  v-model:value="formData.account"
                  disabled
                  placeholder="请输入登录账号"
                  size="large"
                  round
                  :input-props="{ style: { padding: '12px 16px' } }"
                />
              </n-form-item>

              <div class="password-section">
                <div class="password-header">
                  <h4 class="section-title">密码修改</h4>
                </div>

                <div class="password-step">
                  <n-form-item label="原密码" class="form-item">
                    <n-input
                      type="password"
                      v-model:value="old_password"
                      placeholder="请输入原密码"
                      size="large"
                      round
                      show-password-on="click"
                      :input-props="{ style: { padding: '12px 16px' } }"
                    />
                  </n-form-item>
                  <n-form-item label="新密码" class="form-item">
                    <n-input
                      type="password"
                      v-model:value="new_password"
                      placeholder="请输入新密码"
                      size="large"
                      round
                      show-password-on="click"
                      :input-props="{ style: { padding: '12px 16px' } }"
                    />
                  </n-form-item>
                </div>
              </div>
            </div>
          </div>
        </n-card>
      </n-form>
    </n-card>
  </div>
</template>

<script setup lang="ts">
  // 脚本部分保持不变，只修改样式
  import { ref, reactive, onMounted, computed, watch } from 'vue';
  import { FormItemRule, useMessage } from 'naive-ui';
  import { useUser } from '@/store/modules/user';
  import {
    emptyStock,
    emptyWatchlistStock,
    updateUserBaseInfo,
    UserInfoType,
  } from '@/api/user/user';
  import { mockEmptyUserInfo } from '../../../../mock/user';
  import { parseStr, parseTime } from '@/api/time';
  import { getUserInvestmentProfile, updateUserInvestmentProfile } from '@/api/user/user';
  import {
    UserOutlined,
    ToolOutlined,
    FundOutlined,
    StarOutlined,
    FormOutlined,
    HeartOutlined,
  } from '@vicons/antd';
  import { renderIcon } from '@/utils';

  const formRef = ref<any>(null);
  const loading = ref(false);
  const message = useMessage();
  const userStore = useUser();

  const isDataReady = ref(false);
  const isEditing = ref(false);
  const originalFormData = ref<UserInfoType>({ ...mockEmptyUserInfo });

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

  const formRules = {
    password: {
      validator: (rule: FormItemRule, value: string) => {
        if (!isEditing.value) return true;
        if (!value) return new Error('密码不能为空');
        return true;
      },
      trigger: 'blur',
    },
  };

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

  const allow_change_password = ref(false);
  const old_password = ref('');
  const new_password = ref('');

  const enterEditMode = () => {
    isEditing.value = true;
    originalFormData.value = JSON.parse(JSON.stringify(formData));
    old_password.value = '';
    new_password.value = '';
  };

  const cancelEdit = () => {
    isEditing.value = false;
    Object.assign(formData, JSON.parse(JSON.stringify(originalFormData.value)));
    old_password.value = '';
    new_password.value = '';
  };

  // 其他方法保持不变...
  const changeHoldingCount = () => {
    const targetCount = formData.user_investment_profile.current_holdings.holding_count ?? 0;
    const currentList = formData.user_investment_profile.current_holdings.holdings_list;

    while (currentList.length < targetCount) {
      currentList.push({ ...emptyStock });
    }
    if (currentList.length > targetCount) {
      if (confirm('当前操作可能会引起数据丢失')) {
        currentList.splice(targetCount);
      } else {
        formData.user_investment_profile.current_holdings.holding_count = currentList.length;
      }
    }
  };

  const deleteHoldingStock = (index: number) => {
    formData.user_investment_profile.current_holdings.holdings_list.splice(index, 1);
    formData.user_investment_profile.current_holdings.holding_count--;
  };

  const addHoldingStock = () => {
    formData.user_investment_profile.current_holdings.holdings_list.push({ ...emptyStock });
    formData.user_investment_profile.current_holdings.holding_count++;
  };

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

  const deleteWatchlistStock = (index: number) => {
    formData.user_investment_profile.watchlist.watchlist_list.splice(index, 1);
    formData.user_investment_profile.watchlist.watchlist_count--;
  };

  const addWatchlistStock = () => {
    formData.user_investment_profile.watchlist.watchlist_list.push({ ...emptyWatchlistStock });
    formData.user_investment_profile.watchlist.watchlist_count++;
  };

  onMounted(async () => {
    loading.value = true;
    try {
      const userProfile = await getUserInvestmentProfile(userStore.getToken);
      Object.assign(formData, userProfile.data);

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

  const transTimeToString = (userInfo: UserInfoType) => {
    userInfo.user_investment_profile.current_holdings.holdings_list.forEach((stock) => {
      stock.purchase_time = parseStr(stock.purchase_time);
    });
    userInfo.user_investment_profile.watchlist.watchlist_list.forEach((stock) => {
      stock.add_time = parseStr(stock.add_time);
    });
  };

  const handleSubmit = async () => {
    const valid = await formRef.value.validate();
    if (!valid) {
      message.error('信息填写有误');
      return;
    }

    loading.value = true;
    const transData = JSON.parse(JSON.stringify(formData));
    transTimeToString(transData);

    const old_name = originalFormData.value.name;
    const new_name = formData.name;
    const isNameChanged = old_name === new_name;
    const isPasswordChanged = old_password.value !== '' && new_password.value !== '';

    const requestParams = genRequestParams(isPasswordChanged, isNameChanged, {
      new_name: new_name,
      old_password: old_password.value,
      new_password: new_password.value,
    });

    try {
      userStore.setUserInfo(transData);
      const response = await updateUserBaseInfo(userStore.getToken, requestParams);

      if (response.code === 0) {
        message.success(response.msg);
        originalFormData.value = JSON.parse(JSON.stringify(formData));
        isEditing.value = false;
        old_password.value = '';
        new_password.value = '';
      } else {
        message.error(response.msg);
      }
    } catch (e) {
      message.error('网络异常，修改失败');
    } finally {
      loading.value = false;
    }
  };

  const genRequestParams = (isPasswordChanged, isNameChanged, data) => {
    if (isPasswordChanged && isNameChanged) {
      return {
        name: data.new_name,
        old_password: data.old_password,
        new_password: data.new_password,
      };
    } else if (isPasswordChanged) {
      return {
        old_password: data.old_password,
        new_password: data.new_password,
      };
    } else {
      return {
        name: data.new_name,
      };
    }
  };
</script>

<style scoped lang="scss">
  .user-profile-container {
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

  .profile-card {
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

  .profile-header {
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

    .action-buttons {
      display: flex;
      align-items: center;
      gap: 12px;

      .edit-btn {
        padding: 10px 20px;
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);

        &:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 16px rgba(59, 130, 246, 0.3);
        }
      }

      .edit-buttons {
        display: flex;
        gap: 12px;

        .cancel-btn {
          padding: 10px 20px;
          border-radius: 10px;
          font-weight: 500;
          border-color: #e2e8f0;

          &:hover {
            border-color: #cbd5e1;
            background: #f8fafc;
          }
        }

        .save-btn {
          padding: 10px 20px;
          border-radius: 10px;
          font-weight: 600;
          box-shadow: 0 4px 12px rgba(34, 197, 94, 0.2);

          &:hover:not(.n-button--loading) {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(34, 197, 94, 0.3);
          }
        }
      }
    }
  }

  .info-card {
    margin: 20px 28px 28px;
    border-radius: 14px;
    border: 1px solid #eef1f4;
    background: white;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
    overflow: hidden;
    transition: all 0.3s ease;

    &:hover {
      border-color: #e2e8f0;
      box-shadow: 0 6px 24px rgba(0, 0, 0, 0.06);
    }

    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 20px 24px;
      background: linear-gradient(to right, #f8fafc, #ffffff);
      border-bottom: 1px solid #eef1f4;

      .card-title {
        display: flex;
        align-items: center;
        gap: 12px;

        .card-icon {
          background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
          padding: 8px;
          border-radius: 10px;
          color: white;
          box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
        }

        .card-title-text {
          margin: 0;
          font-size: 18px;
          font-weight: 600;
          color: #1e293b;
        }
      }
    }
  }

  .info-view {
    padding: 8px 0;

    .info-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 20px;
      padding: 20px 24px;
    }

    .info-item {
      display: flex;
      align-items: flex-start;
      padding: 24px;
      background: white;
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
        height: 3px;
        background: linear-gradient(to right, #3b82f6, #8b5cf6);
        opacity: 0;
        transition: opacity 0.3s ease;
      }

      &:hover {
        transform: translateY(-4px);
        border-color: #c7d2fe;
        box-shadow: 0 12px 32px rgba(59, 130, 246, 0.12);

        &::before {
          opacity: 1;
        }

        .info-icon {
          transform: scale(1.1);
          box-shadow: 0 6px 20px rgba(59, 130, 246, 0.3);
        }
      }

      .info-icon-wrapper {
        flex-shrink: 0;
        margin-right: 20px;
      }

      .info-icon {
        width: 48px;
        height: 48px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(
          135deg,
          rgba(59, 130, 246, 0.1) 0%,
          rgba(59, 130, 246, 0.2) 100%
        );
        border-radius: 12px;
        color: #3b82f6;
        transition: all 0.3s ease;
        border: 1px solid rgba(59, 130, 246, 0.1);
      }

      .info-content {
        flex: 1;

        .info-label {
          font-size: 13px;
          font-weight: 500;
          color: #64748b;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 8px;
        }

        .info-value {
          font-size: 18px;
          font-weight: 600;
          color: #1e293b;
          line-height: 1.4;

          .password-tag {
            margin-right: 12px;
            padding: 6px 14px;
            font-weight: 600;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            border: none;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2);
          }

          .password-hint {
            display: block;
            margin-top: 8px;
            font-size: 13px;
            opacity: 0.8;
          }
        }
      }
    }
  }

  .info-edit {
    padding: 24px;

    .edit-form-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 24px;
    }

    .form-item {
      margin-bottom: 0;

      :deep(.n-form-item-label) {
        font-weight: 600;
        color: #475569;
        font-size: 14px;
        margin-bottom: 8px;
      }

      :deep(.n-input) {
        .n-input__border {
          border-color: #e2e8f0;
          border-radius: 10px;
          transition: all 0.3s ease;

          &:hover {
            border-color: #cbd5e1;
          }
        }
      }
    }

    .password-section {
      grid-column: 1 / -1;
      padding: 24px;
      background: linear-gradient(
        135deg,
        rgba(248, 250, 252, 0.8) 0%,
        rgba(241, 245, 249, 0.6) 100%
      );
      border-radius: 10px;
      border: 1px solid #eef1f4;

      .password-header {
        margin-bottom: 24px;

        .section-title {
          margin: 0 0 6px;
          font-size: 16px;
          font-weight: 600;
          color: #1e293b;
        }
      }

      .password-step {
        animation: slideDown 0.3s ease;
      }
    }
  }

  @keyframes slideDown {
    from {
      opacity: 0;
      transform: translateY(-10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @media (max-width: 768px) {
    .user-profile-container {
      padding: 16px;
    }

    .profile-header {
      flex-direction: column;
      align-items: stretch;
      gap: 16px;
      padding: 20px;

      .header-title {
        text-align: center;
      }
    }

    .info-card {
      margin: 16px;

      .card-header {
        flex-direction: column;
        align-items: stretch;
        gap: 12px;
        text-align: center;
      }
    }

    .info-view .info-grid,
    .info-edit .edit-form-grid {
      grid-template-columns: 1fr;
      gap: 16px;
    }

    .info-item {
      padding: 20px;

      .info-icon {
        width: 40px;
        height: 40px;
        margin-right: 16px;
      }
    }
  }

  @media (max-width: 480px) {
    .user-profile-container {
      padding: 12px;
    }

    .profile-card {
      border-radius: 12px;
    }

    .info-card {
      margin: 12px;
      border-radius: 10px;
    }

    .info-item {
      flex-direction: column;
      align-items: center;
      text-align: center;
      padding: 16px;

      .info-icon-wrapper {
        margin-right: 0;
        margin-bottom: 16px;
      }
    }
  }
</style>
