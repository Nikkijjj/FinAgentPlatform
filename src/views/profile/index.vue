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
          <n-form-item label="数量">
            <n-input-number
              clearable
              :min="0"
              v-model:value="formData.user_investment_profile.current_holdings.holding_count"
            />
          </n-form-item>
        </div>

        <div class="form-block">
          <span class="block-title">自选股信息</span>
          <n-form-item label="数量">
            <n-input-number
              clearable
              :min="0"
              v-model:value="formData.user_investment_profile.watchlist.watchlist_count"
            />
          </n-form-item>
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
  import { UserInfoType } from '@/api/user/user';
  import { mockEmptyUserInfo } from '../../../mock/user';

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

  const old_password = ref('');
  const confirm_password = ref('');
  const pass = computed(() => {
    if (old_password.value == '') return '';
    else if (old_password.value == formData.password) {
      return 'success';
    } else return 'error';
  });

  const allow_change_password = ref(false);

  //能否修改密码的监视
  const stopWatch = watch(pass, (newVal) => {
    if (newVal == 'success') {
      allow_change_password.value = true;
      stopWatch();
    }
  });

  onMounted(async () => {
    const response = await userStore.fetchUserInvestmentProfile();
    if (response.code == 0) {
      const userInfo = {
        _id: '',
        name: userStore.getName,
        account: userStore.getAccount,
        password: userStore.getPassword,
        user_investment_profile: userStore.getUserInvestmentProfile,
        status: 'active',
        date: '',
      };
      Object.assign(formData, userInfo);
    } else message.error(response.msg);
  });

  const handleSubmit = async () => {
    const valid = await formRef.value.validate();
    if (!valid) {
      message.error('信息无效');
      return;
    }

    loading.value = true;
    userStore.setUserInfo(formData);

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
    padding: 0 16px;
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
  }

  .profile-form {
    margin-top: 20px;
    display: flex;
    flex-direction: row;
    flex: 1;
  }

  .form-actions {
    position: absolute;
    bottom: 20px;
    right: 20px;
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
