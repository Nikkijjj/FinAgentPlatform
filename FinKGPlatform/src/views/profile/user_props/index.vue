<!-- src/views/profile/user_props/index.vue -->
<template>
  <div class="user-profile-container">
    <n-card :bordered="false" class="profile-card" size="large">
      <!-- 头部 -->
      <div class="profile-header">
        <div class="header-title">
          <h2 class="title-text">账号管理</h2>
          <p class="title-subtext">管理您的登录账号与基础信息</p>
        </div>
        <div class="action-buttons">
          <n-button
            v-if="!isEditing"
            type="primary"
            size="medium"
            class="edit-btn"
            @click="enterEditMode"
          >
            编辑资料
          </n-button>
          <div v-else class="edit-buttons">
            <n-button type="default" size="medium" class="cancel-btn" ghost @click="cancelEdit">
              取消
            </n-button>
            <n-button
              type="success"
              size="medium"
              class="save-btn"
              :loading="saving"
              @click="handleSubmit"
            >
              保存更改
            </n-button>
          </div>
        </div>
      </div>

      <n-spin :show="loading">
        <n-form
          ref="formRef"
          :model="formData"
          :rules="rules"
          label-placement="top"
          class="profile-form"
        >
          <n-card class="info-card">
            <template #header>
              <div class="card-header">
                <div class="card-title">
                  <div class="avatar-wrapper">
                    <div class="avatar-circle">
                      <span>{{ avatarLetter }}</span>
                    </div>
                  </div>
                  <div class="card-title-texts">
                    <h3 class="card-title-text">基础信息</h3>
                    <p class="card-sub-text">
                      {{
                        isEditing
                          ? '编辑模式：可修改用户名、邮箱和密码'
                          : '查看模式：仅展示当前账号信息'
                      }}
                    </p>
                  </div>
                </div>
                <n-tag :bordered="false" size="small" type="info" round>
                  ID: {{ accountInfo?.id ?? '-' }}
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
                        <UserOutlined />
                      </n-icon>
                    </div>
                  </div>
                  <div class="info-content">
                    <div class="info-label">用户名</div>
                    <div class="info-value">
                      {{ accountInfo?.user_name || '未设置' }}
                    </div>
                  </div>
                </div>

                <div class="info-item">
                  <div class="info-icon-wrapper">
                    <div class="info-icon">
                      <n-icon>
                        <MailOutlined />
                      </n-icon>
                    </div>
                  </div>
                  <div class="info-content">
                    <div class="info-label">邮箱</div>
                    <div class="info-value">
                      {{ accountInfo?.email || '未设置' }}
                    </div>
                  </div>
                </div>

                <div class="info-item">
                  <div class="info-icon-wrapper">
                    <div class="info-icon">
                      <n-icon>
                        <CalendarOutlined />
                      </n-icon>
                    </div>
                  </div>
                  <div class="info-content">
                    <div class="info-label">创建时间</div>
                    <div class="info-value">
                      {{ accountInfo?.create_time || '未知' }}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 编辑模式 -->
            <div v-else class="info-edit">
              <div class="edit-form-grid">
                <n-form-item label="用户名" path="username" class="form-item">
                  <n-input
                    v-model:value="formData.username"
                    placeholder="请输入用户名"
                    size="large"
                    round
                  />
                </n-form-item>

                <n-form-item label="邮箱" path="email" class="form-item">
                  <n-input
                    v-model:value="formData.email"
                    placeholder="请输入邮箱（可选）"
                    size="large"
                    round
                  />
                </n-form-item>
              </div>

              <div class="password-section">
                <div class="password-header">
                  <h4 class="section-title">密码修改</h4>
                  <p class="section-subtitle">
                    如需修改登录密码，请输入新密码并确认；如不修改，可留空。
                  </p>
                </div>

                <div class="password-grid">
                  <n-form-item label="新密码" path="newPassword" class="form-item">
                    <n-input
                      v-model:value="formData.newPassword"
                      type="password"
                      placeholder="请输入新密码（至少 6 位）"
                      size="large"
                      round
                      show-password-on="click"
                    />
                  </n-form-item>

                  <n-form-item label="确认新密码" path="confirmPassword" class="form-item">
                    <n-input
                      v-model:value="formData.confirmPassword"
                      type="password"
                      placeholder="请再次输入新密码"
                      size="large"
                      round
                      show-password-on="click"
                    />
                  </n-form-item>
                </div>
              </div>
            </div>
          </n-card>
        </n-form>
      </n-spin>
    </n-card>
  </div>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import { useMessage, type FormInst, type FormRules } from 'naive-ui';
  import { useUserStore } from '@/store/modules/user';
  import { getUser, updateUser, type UpdateUserParams, type UserType } from '@/api/user/user';
  import { UserOutlined, MailOutlined, CalendarOutlined } from '@vicons/antd';

  const message = useMessage();
  const userStore = useUserStore();

  const loading = ref(false);
  const saving = ref(false);
  const isEditing = ref(false);

  const accountInfo = ref<UserType | null>(null);

  const formRef = ref<FormInst | null>(null);
  const formData = ref({
    username: '',
    email: '',
    newPassword: '',
    confirmPassword: '',
  });

  const rules: FormRules = {
    username: {
      required: true,
      trigger: ['blur', 'input'],
      message: '请输入用户名',
    },
    email: [
      {
        type: 'email',
        trigger: ['blur', 'input'],
        message: '请输入正确的邮箱格式',
      },
    ],
    newPassword: [
      {
        min: 6,
        trigger: ['blur', 'input'],
        message: '密码长度不能小于 6 位',
      },
    ],
    confirmPassword: {
      trigger: ['blur', 'input'],
      validator: (_rule, value: string) => {
        if (!formData.value.newPassword && !value) return true;
        if (value !== formData.value.newPassword) {
          return new Error('两次输入的密码不一致');
        }
        return true;
      },
    },
  };

  const avatarLetter = computed(() => {
    const name = accountInfo.value?.user_name || userStore.getUsername || 'U';
    return name.charAt(0).toUpperCase();
  });

  const loadAccount = async () => {
    const userId = userStore.getUserId;
    if (!userId) {
      message.error('未获取到用户信息，请重新登录');
      return;
    }
    loading.value = true;
    try {
      const res = await getUser(userId);
      if (res.status === 200) {
        accountInfo.value = res.data;
        formData.value.username = res.data.user_name;
        formData.value.email = res.data.email || '';
        formData.value.newPassword = '';
        formData.value.confirmPassword = '';
      } else {
        message.error(res.message || '获取账号信息失败');
      }
    } catch (error) {
      console.error('获取账号信息失败:', error);
      message.error('获取账号信息失败，请稍后重试');
    } finally {
      loading.value = false;
    }
  };

  const enterEditMode = () => {
    if (!accountInfo.value) {
      message.warning('尚未加载账号信息');
      return;
    }
    isEditing.value = true;
    formData.value.username = accountInfo.value.user_name;
    formData.value.email = accountInfo.value.email || '';
    formData.value.newPassword = '';
    formData.value.confirmPassword = '';
  };

  const cancelEdit = () => {
    isEditing.value = false;
    if (!accountInfo.value) return;
    formData.value.username = accountInfo.value.user_name;
    formData.value.email = accountInfo.value.email || '';
    formData.value.newPassword = '';
    formData.value.confirmPassword = '';
  };

  const handleSubmit = async () => {
    if (!accountInfo.value) return;
    try {
      await formRef.value?.validate();
    } catch {
      message.error('请检查表单信息是否填写正确');
      return;
    }

    const params: UpdateUserParams = {};
    const trimmedUsername = formData.value.username.trim();
    const trimmedEmail = formData.value.email.trim();

    if (trimmedUsername && trimmedUsername !== accountInfo.value.user_name) {
      params.username = trimmedUsername;
    }
    if (trimmedEmail !== (accountInfo.value.email || '')) {
      params.email = trimmedEmail || undefined;
    }
    if (formData.value.newPassword) {
      params.password = formData.value.newPassword;
    }

    if (Object.keys(params).length === 0) {
      message.info('没有需要更新的内容');
      isEditing.value = false;
      return;
    }

    saving.value = true;
    try {
      const res = await updateUser(accountInfo.value.id, params);
      if (res.status === 200) {
        message.success('账号信息更新成功');
        accountInfo.value = {
          ...accountInfo.value,
          user_name: trimmedUsername || accountInfo.value.user_name,
          email: trimmedEmail || accountInfo.value.email,
        };
        if (params.username) {
          userStore.setUsername(params.username);
          userStore.setName(params.username);
        }
        isEditing.value = false;
        formData.value.newPassword = '';
        formData.value.confirmPassword = '';
      } else {
        message.error(res.message || '更新失败');
      }
    } catch (error) {
      console.error('更新账号信息失败:', error);
      message.error('更新失败，请稍后重试');
    } finally {
      saving.value = false;
    }
  };

  onMounted(() => {
    loadAccount();
  });
</script>

<style scoped lang="scss">
  .user-profile-container {
    min-height: 100vh;
    padding: 24px;
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  }

  .profile-card {
    background: #ffffff;
    border-radius: 16px;
    box-shadow: 0 10px 40px rgba(15, 23, 42, 0.08);
    border: 1px solid rgba(226, 232, 240, 0.9);
    overflow: hidden;
    transition: box-shadow 0.3s ease, transform 0.3s ease;

    &:hover {
      box-shadow: 0 14px 48px rgba(15, 23, 42, 0.12);
      transform: translateY(-2px);
    }
  }

  .profile-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 24px 28px;
    border-bottom: 1px solid #e5e7eb;
    background: radial-gradient(circle at 0 0, #eff6ff 0, transparent 55%),
      radial-gradient(circle at 100% 0, #e0f2fe 0, transparent 55%), #ffffff;

    .header-title {
      .title-text {
        margin: 0;
        font-size: 24px;
        font-weight: 700;
        color: #0f172a;
        letter-spacing: -0.5px;
      }

      .title-subtext {
        margin: 6px 0 0;
        font-size: 14px;
        color: #64748b;
      }
    }

    .action-buttons {
      display: flex;
      align-items: center;
      gap: 12px;

      .edit-btn,
      .save-btn,
      .cancel-btn {
        padding: 9px 20px;
        border-radius: 999px;
        font-weight: 600;
      }

      .edit-btn {
        box-shadow: 0 6px 14px rgba(59, 130, 246, 0.3);

        &:hover {
          transform: translateY(-1px);
          box-shadow: 0 10px 20px rgba(59, 130, 246, 0.35);
        }
      }

      .save-btn {
        box-shadow: 0 6px 14px rgba(34, 197, 94, 0.25);

        &:hover:not(.n-button--loading) {
          transform: translateY(-1px);
          box-shadow: 0 10px 20px rgba(34, 197, 94, 0.3);
        }
      }
    }
  }

  .info-card {
    margin: 20px 28px 28px;
    border-radius: 14px;
    border: 1px solid #e5e7eb;
    background: #ffffff;
    box-shadow: 0 4px 18px rgba(15, 23, 42, 0.04);

    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 20px 24px;
      background: linear-gradient(to right, #f9fafb, #ffffff);
      border-bottom: 1px solid #e5e7eb;

      .card-title {
        display: flex;
        align-items: center;
        gap: 16px;

        .avatar-wrapper {
          .avatar-circle {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            background: radial-gradient(circle at 30% 0, #bfdbfe 0, transparent 55%),
              linear-gradient(135deg, #3b82f6, #1d4ed8);
            color: #ffffff;
            font-size: 22px;
            font-weight: 700;
            box-shadow: 0 6px 16px rgba(37, 99, 235, 0.45);
          }
        }

        .card-title-texts {
          .card-title-text {
            margin: 0;
            font-size: 18px;
            font-weight: 600;
            color: #0f172a;
          }

          .card-sub-text {
            margin: 4px 0 0;
            font-size: 13px;
            color: #6b7280;
          }
        }
      }
    }
  }

  .info-view {
    padding: 8px 0 20px;

    .info-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 20px;
      padding: 20px 24px;
    }

    .info-item {
      display: flex;
      align-items: flex-start;
      padding: 20px;
      background: #ffffff;
      border-radius: 12px;
      border: 1px solid #e5e7eb;
      transition: all 0.25s ease;
      position: relative;
      overflow: hidden;

      &::before {
        content: '';
        position: absolute;
        inset: 0;
        background: linear-gradient(120deg, rgba(59, 130, 246, 0.08), rgba(59, 130, 246, 0));
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.25s ease;
      }

      &:hover {
        transform: translateY(-3px);
        border-color: #bfdbfe;
        box-shadow: 0 10px 26px rgba(15, 23, 42, 0.08);

        &::before {
          opacity: 1;
        }

        .info-icon {
          transform: translateY(-1px);
          box-shadow: 0 6px 16px rgba(59, 130, 246, 0.35);
        }
      }

      .info-icon-wrapper {
        flex-shrink: 0;
        margin-right: 18px;
      }

      .info-icon {
        width: 42px;
        height: 42px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 12px;
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.08), rgba(59, 130, 246, 0.16));
        color: #2563eb;
        border: 1px solid rgba(59, 130, 246, 0.2);
        transition: all 0.25s ease;
      }

      .info-content {
        .info-label {
          font-size: 13px;
          font-weight: 500;
          color: #6b7280;
          margin-bottom: 6px;
        }

        .info-value {
          font-size: 17px;
          font-weight: 600;
          color: #111827;
        }
      }
    }
  }

  .info-edit {
    padding: 24px;

    .edit-form-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 20px;
      margin-bottom: 20px;
    }

    .form-item {
      :deep(.n-form-item-label) {
        font-weight: 600;
        color: #475569;
        margin-bottom: 6px;
      }

      :deep(.n-input) {
        .n-input__border,
        .n-input__state-border {
          border-radius: 999px;
        }
      }
    }

    .password-section {
      padding: 20px 20px 4px;
      border-radius: 14px;
      border: 1px solid #e5e7eb;
      background: linear-gradient(135deg, rgba(248, 250, 252, 0.9), rgba(239, 246, 255, 0.9));

      .password-header {
        margin-bottom: 16px;

        .section-title {
          margin: 0 0 4px;
          font-size: 16px;
          font-weight: 600;
          color: #0f172a;
        }

        .section-subtitle {
          margin: 0;
          font-size: 13px;
          color: #6b7280;
        }
      }

      .password-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 16px;
      }
    }
  }

  @media (max-width: 768px) {
    .user-profile-container {
      padding: 16px;
    }

    .profile-header {
      flex-direction: column;
      align-items: flex-start;
      gap: 16px;
    }

    .info-card {
      margin: 16px;
    }
  }

  @media (max-width: 480px) {
    .user-profile-container {
      padding: 12px;
    }

    .info-card {
      margin: 12px;
    }

    .info-view .info-item {
      flex-direction: column;
      align-items: center;
      text-align: center;

      .info-icon-wrapper {
        margin-right: 0;
        margin-bottom: 10px;
      }
    }
  }
</style>
