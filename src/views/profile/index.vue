<template>
  <div class="user-profile-container">
    <n-card :bordered="false" class="profile-card" size="large">
      <n-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-placement="top"
        label-width="80px"
        class="profile-form"
      >
        <div class="form-block">
          <span class="block-title">个人信息</span>
          <n-form-item label="昵称">
            <n-input v-model:value="formData.name" disabled />
          </n-form-item>
          <n-form-item label="账号">
            <n-input v-model:value="formData.account" disabled />
          </n-form-item>
          <n-form-item label="修改密码" path="password" v-show="allow_change_password">
            <n-input
              type="password"
              clearable
              showPasswordOn="click"
              v-model:value="formData.password"
              placeholder="输入新密码"
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
            />
          </n-form-item>
        </div>

        <div class="form-block">
          <span class="block-title">个性化投资目标</span>
          <n-form-item label="投资类别">
            <n-select
              :options="term_options"
              v-model:value="
                formData.user_investment_profile.personalized_investment_goals.investment_tenure
                  .tenure_type
              "
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
            />
          </n-form-item>
          <n-form-item label="投资描述">
            <n-input
              clearable
              v-model:value="
                formData.user_investment_profile.personalized_investment_goals.investment_tenure
                  .tenure_description
              "
            />
          </n-form-item>
        </div>

        <div class="form-block">
          <span class="block-title">投资期望</span>
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
            />
          </n-form-item>
          <n-form-item label="收益描述">
            <n-input
              clearable
              v-model:value="
                formData.user_investment_profile.personalized_investment_goals.expected_return
                  .return_description
              "
            />
          </n-form-item>
          <n-form-item label="可承受亏损率">
            <n-input-number
              clearable
              :min="0"
              :max="100"
              :precision="2"
              v-model:value="
                formData.user_investment_profile.personalized_investment_goals.expected_return
                  .risk_tolerance.loss_tolerance_ratio
              "
            >
              <template #suffix> % </template>
            </n-input-number>
          </n-form-item>
          <n-form-item label="风险等级">
            <n-select
              :options="risk_options"
              v-model:value="
                formData.user_investment_profile.personalized_investment_goals.expected_return
                  .risk_tolerance.risk_level
              "
            />
          </n-form-item>
          <n-form-item label="风险描述">
            <n-input
              clearable
              v-model:value="
                formData.user_investment_profile.personalized_investment_goals.expected_return
                  .risk_tolerance.risk_description
              "
            />
          </n-form-item>
        </div>

        <div class="form-block">
          <span class="block-title">持仓情况</span>
          <div class="count-input">
            <n-form-item label="数量">
              <n-input-number
                clearable
                :min="0"
                v-model:value="formData.user_investment_profile.current_holdings.holding_count"
              />
            </n-form-item>
            <n-button @click="changeHoldingCount">确认</n-button>
          </div>
          <div class="form-group">
            <n-card
              class="stock-card"
              closable
              v-for="(stock, index) in formData.user_investment_profile.current_holdings
                .holding_list"
              :key="index"
              @close="deleteHoldingStock(stock)"
            >
              <n-form-item label="股票代码">
                <n-input clearable v-model:value="stock.stock_code" />
              </n-form-item>
              <n-form-item label="股票名称">
                <n-input clearable v-model:value="stock.stock_name" />
              </n-form-item>
              <n-form-item label="持有数量">
                <n-input-number clearable :min="0" v-model:value="stock.holding_quantity" />
              </n-form-item>
              <n-form-item label="买入价格">
                <n-input-number
                  clearable
                  :min="0"
                  :precision="2"
                  v-model:value="stock.purchase_price"
                />
              </n-form-item>
              <n-form-item label="买入时间">
                <n-date-picker type="date" clearable v-model:value="stock.purchase_time" />
              </n-form-item>
              <n-form-item label="股票描述">
                <n-input clearable v-model:value="stock.holding_remark" />
              </n-form-item>
            </n-card>
            <n-button text @click="addHoldingStock" style="font-size: 100px; padding: 0">
              <n-icon>
                <svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <!-- 卡片主体 -->
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

                  <!-- 加号符号 -->
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
        </div>

        <div class="form-block">
          <span class="block-title">自选股信息</span>
          <div class="count-input">
            <n-form-item label="数量">
              <n-input-number
                clearable
                :min="0"
                v-model:value="formData.user_investment_profile.watchlist.watchlist_count"
              />
            </n-form-item>
            <n-button @click="changeWatchlistCount">确认</n-button>
          </div>
          <div class="form-group">
            <n-card
              class="stock-card"
              closable
              v-for="(stock, index) in formData.user_investment_profile.watchlist.watchlist_list"
              :key="index"
              @close="deleteWatchlistStock(stock)"
            >
              <n-form-item label="股票代码">
                <n-input clearable v-model:value="stock.stock_code" />
              </n-form-item>
              <n-form-item label="股票名称">
                <n-input clearable v-model:value="stock.stock_name" />
              </n-form-item>
              <n-form-item label="添加时间">
                <n-date-picker type="date" clearable v-model:value="stock.add_time" />
              </n-form-item>
              <n-form-item label="自选股描述">
                <n-input clearable v-model:value="stock.watch_remark" />
              </n-form-item>
            </n-card>
            <n-button text @click="addWatchlistStock" style="font-size: 100px; padding: 0">
              <n-icon>
                <svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <!-- 卡片主体 -->
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

                  <!-- 加号符号 -->
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
        </div>
      </n-form>
      <div class="form-actions">
        <n-button
          class="saveButton"
          type="primary"
          @click="handleSubmit"
          :loading="loading"
          size="medium"
        >
          保存修改
        </n-button>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
  import { ref, reactive, onMounted, computed, watch } from 'vue';
  import { FormItemRule, useMessage } from 'naive-ui';
  import { useUser } from '@/store/modules/user';
  import {
    emptyStock,
    emptyWatchlistStock,
    StockType,
    UserInfoType,
    WatchlistStockType,
  } from '@/api/user/user';
  import { mockEmptyUserInfo } from '../../../mock/user';
  import { parseStr, parseTime } from '@/api/time';

  const formRef = ref<any>(null);
  const loading = ref(false);
  const message = useMessage();
  const userStore = useUser();

  const formData = reactive<UserInfoType>(mockEmptyUserInfo);

  const formRules = {
    password: {
      validator: (rule: FormItemRule, value: string) => {
        if (!allow_change_password.value) return true;
        if (value == '') return new Error('密码不能为空');
        else if (confirm_password.value == '') return new Error('请确认密码');
        else if (confirm_password.value != value) return new Error('两次输入密码不一致');
        else return true;
      },
      trigger: 'blur',
    },
  };

  const term_options = [
    {
      label: '短期',
      value: 'short_term',
    },
    {
      label: '中期',
      value: 'medium+term',
    },
    {
      label: '长期',
      value: 'long-term',
    },
  ];

  const stability_options = [
    {
      label: '稳定优先',
      value: 'stable',
    },
    {
      label: '平衡',
      value: 'moderate',
    },
    {
      label: '灵活可变',
      value: 'flexible',
    },
  ];

  const risk_options = [
    {
      label: '保守',
      value: 'conservative',
    },
    {
      label: '平衡',
      value: 'moderate',
    },
    {
      label: '进取',
      value: 'aggressive',
    },
    {
      label: '激进',
      value: 'radical',
    },
  ];

  const allow_change_password = ref(false);
  const old_password = ref('');
  const confirm_password = ref('');
  const pass = computed(() => {
    if (old_password.value == '') return '';
    else if (old_password.value == formData.password) {
      return 'success';
    } else return 'error';
  });

  // 能否修改密码的监视
  const stopWatchPassword = watch(pass, (newVal) => {
    if (newVal == 'success') {
      allow_change_password.value = true;
      stopWatchPassword();
    }
  });

  const changeHoldingCount = () => {
    while (
      formData.user_investment_profile.current_holdings.holding_list.length <
      (formData.user_investment_profile.current_holdings.holding_count ?? 0)
    ) {
      formData.user_investment_profile.current_holdings.holding_list.push(emptyStock);
    }

    if (
      formData.user_investment_profile.current_holdings.holding_list.length >
      (formData.user_investment_profile.current_holdings.holding_count ?? 0)
    ) {
      if (confirm('当前操作可能会引起数据丢失')) {
        while (
          formData.user_investment_profile.current_holdings.holding_list.length >
          (formData.user_investment_profile.current_holdings.holding_count ?? 0)
        ) {
          formData.user_investment_profile.current_holdings.holding_list.pop();
        }
      }
    }
  };

  const deleteHoldingStock = (stock: StockType) => {
    if (!formData.user_investment_profile.current_holdings.holding_count) return;
    formData.user_investment_profile.current_holdings.holding_count--;
    const i = formData.user_investment_profile.current_holdings.holding_list.findIndex((s) => {
      return s == stock;
    });
    formData.user_investment_profile.current_holdings.holding_list.splice(i, 1);
  };

  const addHoldingStock = () => {
    formData.user_investment_profile.current_holdings.holding_count =
      (formData.user_investment_profile.current_holdings.holding_count ?? 0) + 1;
    formData.user_investment_profile.current_holdings.holding_list.push(emptyStock);
  };

  const changeWatchlistCount = () => {
    while (
      formData.user_investment_profile.watchlist.watchlist_list.length <
      (formData.user_investment_profile.watchlist.watchlist_count ?? 0)
    ) {
      formData.user_investment_profile.watchlist.watchlist_list.push(emptyWatchlistStock);
    }

    if (
      formData.user_investment_profile.watchlist.watchlist_list.length >
      (formData.user_investment_profile.watchlist.watchlist_count ?? 0)
    ) {
      if (confirm('当前操作可能会引起数据丢失')) {
        while (
          formData.user_investment_profile.watchlist.watchlist_list.length >
          (formData.user_investment_profile.watchlist.watchlist_count ?? 0)
        ) {
          formData.user_investment_profile.watchlist.watchlist_list.pop();
        }
      }
    }
  };

  const deleteWatchlistStock = (stock: WatchlistStockType) => {
    if (!formData.user_investment_profile.watchlist.watchlist_count) return;
    formData.user_investment_profile.watchlist.watchlist_count--;
    const i = formData.user_investment_profile.watchlist.watchlist_list.findIndex((s) => {
      return s == stock;
    });
    formData.user_investment_profile.watchlist.watchlist_list.splice(i, 1);
  };

  const addWatchlistStock = () => {
    formData.user_investment_profile.watchlist.watchlist_count =
      (formData.user_investment_profile.watchlist.watchlist_count ?? 0) + 1;
    formData.user_investment_profile.watchlist.watchlist_list.push(emptyStock);
  };

  onMounted(async () => {
    const response = await userStore.fetchUserInvestmentProfile();
    if (response.code == 0) {
      const originalUserInfo = {
        _id: '',
        name: userStore.getName,
        account: userStore.getAccount,
        password: userStore.getPassword,
        user_investment_profile: userStore.getUserInvestmentProfile,
        status: 'active',
        date: '',
      };
      const userInfo = { ...originalUserInfo };
      transStringToTime(userInfo);
      Object.assign(formData, userInfo);
    } else message.error(response.msg);
  });

  // [读入数据时]转换时间格式
  const transStringToTime = (userInfo: UserInfoType) => {
    userInfo.user_investment_profile.current_holdings.holding_list.forEach((stock) => {
      stock.purchase_time = parseTime(stock.purchase_time);
    });
    userInfo.user_investment_profile.watchlist.watchlist_list.forEach((stock) => {
      stock.add_time = parseTime(stock.add_time);
    });
  };

  // [保存信息时]转换时间格式
  const transTimeToString = (userInfo: UserInfoType) => {
    userInfo.user_investment_profile.current_holdings.holding_list.forEach((stock) => {
      stock.purchase_time = parseStr(stock.purchase_time);
    });
    userInfo.user_investment_profile.watchlist.watchlist_list.forEach((stock) => {
      stock.add_time = parseStr(stock.add_time);
    });
  };

  const handleSubmit = async () => {
    const valid = await formRef.value.validate();
    if (!valid) {
      message.error('信息无效');
      return;
    }

    loading.value = true;
    const transData = JSON.parse(JSON.stringify(formData));
    transTimeToString(transData);
    userStore.setUserInfo(transData);

    try {
      const response = await userStore.updateUserInvestmentProfile();
      if (response.code == 0) message.success(response.msg);
      else message.error(response.msg);
    } catch (e) {
      message.error('网络异常，修改失败');
    } finally {
      loading.value = false;
    }
  };
</script>

<style scoped>
  .user-profile-container {
    position: relative;
    height: 100%;
    display: flex;
    flex-direction: row;
    border-radius: 10px;
    overflow: hidden;
  }

  .form-block {
    flex: 1;
    padding: 16px;
    border: 1px solid lightgray;
  }

  .count-input {
    display: flex;
    flex-direction: row;
    align-items: center;
  }

  .stock-card {
    background-color: ghostwhite;
    border: 1px solid lightgray;
    width: 30%;
  }

  .form-group {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    gap: 10px;
    overflow: auto;
  }

  .block-title {
    font-weight: bold;
    margin-bottom: 12px;
    display: block;
  }

  .profile-card {
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
    display: flex;
    flex-direction: column;
    position: relative;
    flex: 1;
    gap: 20px;
  }

  .profile-form {
    margin-top: 20px;
    display: flex;
    flex-direction: column;
    flex: 1;
    gap: 20px;
  }

  .form-actions {
    padding: 16px;
  }

  .saveButton {
    background-color: #27ba9b;
    color: #fff;
    border-color: #27ba9b;
    border-radius: 4px;
    box-shadow: 0 2px 8px rgba(39, 186, 155, 0.3);
    transition: all 0.3s ease;

    padding: 8px 24px;
    font-size: 14px;
    font-weight: 500;
  }

  .saveButton:hover {
    background-color: #229a80;
    border-color: #229a80;
    box-shadow: 0 4px 12px rgba(39, 186, 155, 0.4);
    transform: translateY(-1px);
  }

  .saveButton:active {
    background-color: #1d8a70;
    border-color: #1d8a70;
    transform: translateY(0);
    box-shadow: 0 2px 6px rgba(39, 186, 155, 0.2);
  }
</style>
