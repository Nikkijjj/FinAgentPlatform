<!-- src/views/login/index.vue -->
<template>
  <div class="view-account">
    <div class="view-account-header"></div>
    <div class="view-account-background">
      <div class="line line-1"></div>
      <div class="line line-2"></div>
      <div class="line line-3"></div>
      <div class="square square-1"></div>
      <div class="square square-2"></div>
      <div class="triangle"></div>
      <div class="wave wave-1"></div>
      <div class="wave wave-2"></div>
      <div class="wave wave-3"></div>
    </div>
    <div class="view-account-container animate__animated animate__fadeInDown">
      <div class="view-account-top">
        <div class="view-account-top-logo">
          <img :src="websiteConfig.loginImage" alt="FinAgentGraph" class="top-logo-img" />
        </div>
        <h1 class="view-account-top-title">FinAgentGraph</h1>
        <div class="view-account-top-desc">{{ websiteConfig.loginDesc }}</div>
      </div>
      <div class="view-account-form">
        <h2 class="view-account-title">账号登录</h2>
        <div class="login-welcome">欢迎回来，请登录您的账号</div>
        <n-form
          ref="formRef"
          label-placement="left"
          size="large"
          :model="formInline"
          :rules="rules"
          class="login-form"
        >
          <n-form-item path="username" class="username-item">
            <n-input
              v-model:value="formInline.username"
              placeholder="请输入账号"
              class="login-input"
              ref="inputAccount"
              @keyup="autoWrap($event)"
            >
              <template #prefix>
                <n-icon size="18" color="#808695">
                  <PersonOutline />
                </n-icon>
              </template>
            </n-input>
          </n-form-item>

          <n-form-item path="password" class="password-item">
            <n-input
              v-model:value="formInline.password"
              type="password"
              showPasswordOn="click"
              placeholder="请输入密码"
              class="login-input"
              ref="inputPassword"
              @keyup="autoWrap($event)"
            >
              <template #prefix>
                <n-icon size="18" color="#808695">
                  <LockClosedOutline />
                </n-icon>
              </template>
            </n-input>
          </n-form-item>

          <!-- 验证码输入框 -->
          <n-form-item path="captchaText" class="captcha-item">
            <div class="captcha-wrapper">
              <n-input
                v-model:value="formInline.captchaText"
                placeholder="请输入验证码"
                class="captcha-input"
                :maxlength="4"
                @keyup="autoWrap($event)"
              >
                <template #prefix>
                  <n-icon size="18" color="#808695">
                    <ShieldCheckmarkOutline />
                  </n-icon>
                </template>
              </n-input>
              <div class="captcha-image" @click="refreshCaptcha">
                <img v-if="captchaImage" :src="captchaImage" alt="验证码" class="captcha-img" />
                <n-spin v-else size="small" />
              </div>
            </div>
          </n-form-item>

          <n-form-item class="default-color auto-login-row">
            <n-checkbox v-model:checked="autoLogin">自动登录</n-checkbox>
          </n-form-item>

          <n-form-item>
            <n-button
              type="primary"
              @click="handleSubmit"
              size="large"
              :loading="loading"
              block
              class="login-button"
            >
              登录
            </n-button>
          </n-form-item>

          <n-form-item class="default-color register-row">
            <div class="register-only">
              <router-link to="/register" class="register-link">注册账号</router-link>
            </div>
          </n-form-item>
        </n-form>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { reactive, ref, onMounted } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { useUserStore } from '@/store/modules/user';
  import { useMessage } from 'naive-ui';
  import { PersonOutline, LockClosedOutline, ShieldCheckmarkOutline } from '@vicons/ionicons5';
  import { PageEnum } from '@/enums/pageEnum';
  import { websiteConfig } from '@/config/website.config';
  import { getCaptcha, login, type LoginResponse } from '@/api/user/user'; // 从user.ts导入
  import { storage } from '@/utils/Storage';
  import { ACCESS_TOKEN, CURRENT_USER } from '@/store/mutation-types';

  const formRef = ref();
  const inputAccount = ref<HTMLElement>();
  const inputPassword = ref<HTMLElement>();
  const message = useMessage();
  const loading = ref(false);
  const autoLogin = ref(true);
  const LOGIN_NAME = PageEnum.BASE_LOGIN_NAME;

  // 验证码相关
  const captchaId = ref('');
  const captchaImage = ref('');

  const formInline = reactive({
    username: '', // 注意：这里对应后端的 name 字段
    password: '',
    captchaText: '',
  });

  // 表单验证规则
  const rules = {
    username: { required: true, message: '请输入用户名', trigger: 'blur' },
    password: { required: true, message: '请输入密码', trigger: 'blur' },
    captchaText: {
      required: true,
      message: '请输入验证码',
      trigger: 'blur',
      validator: (rule: any, value: string) => {
        if (!value) return new Error('请输入验证码');
        if (value.length !== 4) return new Error('验证码必须为4位');
        return true;
      },
    },
  };

  const userStore = useUserStore();
  const router = useRouter();
  const route = useRoute();

  // 获取验证码
  const refreshCaptcha = async () => {
    try {
      const response = await getCaptcha();
      if (response.status === 200) {
        captchaId.value = response.data.id;
        captchaImage.value = response.data.svg;
      } else {
        message.error('获取验证码失败');
      }
    } catch (error) {
      console.error('获取验证码错误:', error);
      message.error('获取验证码失败');
    }
  };

  const clearForm = () => {
    formInline.username = '';
    formInline.password = '';
    formInline.captchaText = '';
    refreshCaptcha(); // 刷新验证码
  };

  // src/views/login/index.vue
  // 只需要修改登录成功部分的代码

  const handleSubmit = async (e: Event) => {
    e.preventDefault();

    formRef.value.validate(async (errors: any) => {
      if (!errors) {
        loading.value = true;

        try {
          const params = {
            name: formInline.username,
            password: formInline.password,
            captchaText: formInline.captchaText,
            captchaId: captchaId.value,
          };

          console.log('登录参数:', params);

          const response = await login(params);
          console.log('登录响应:', response);

          if (response.status === 200) {
            // 保存token和用户信息
            const { token, user } = response.data;
            console.log('登录成功，用户信息:', user);
            console.log('登录成功，token:', token);

            // 存储到本地存储
            localStorage.setItem('token', token);
            localStorage.setItem('userInfo', JSON.stringify(user));

            // 保存用户ID和用户名
            const userId = parseInt(user.id) || 0;
            localStorage.setItem('USER_ID', userId.toString());
            localStorage.setItem('USERNAME', user.username || formInline.username);

            // 使用统一的 Storage 类存储
            storage.set(ACCESS_TOKEN, token);
            storage.set(CURRENT_USER, user);
            storage.set('USER_ID', userId);
            storage.set('USERNAME', user.username || formInline.username);

            // 更新store
            userStore.setToken(token);
            userStore.setUserInfo({
              id: user.id,
              name: user.username,
            });
            userStore.setUserId(userId);
            userStore.setUsername(user.username || formInline.username);

            const toPath = decodeURIComponent((route.query?.redirect || '/') as string);

            message.success(response.message || '登录成功');

            // 处理自动登录
            if (autoLogin.value) {
              localStorage.setItem('autoLogin', 'true');
            }

            console.log('准备跳转到:', toPath);

            if (route.name === LOGIN_NAME) {
              await router.replace('/');
            } else {
              await router.replace(toPath);
            }
          } else {
            message.error(response.message || '登录失败');
            refreshCaptcha();
            formInline.captchaText = '';
          }
        } catch (error: any) {
          console.error('登录错误:', error);
          message.error(error.response?.data?.message || '登录失败，请稍后重试');
          refreshCaptcha();
          formInline.captchaText = '';
        } finally {
          loading.value = false;
        }
      } else {
        message.error('请填写完整信息');
      }
    });
  };

  const autoWrap = (e: KeyboardEvent) => {
    if (e.key !== 'Enter') return;

    if (!formInline.username) {
      inputAccount.value?.focus();
      return;
    }
    if (!formInline.password) {
      inputPassword.value?.focus();
      return;
    }
    handleSubmit(e);
  };

  // 初始化
  onMounted(() => {
    refreshCaptcha(); // 获取验证码

    // 聚焦用户名输入框
    setTimeout(() => {
      inputAccount.value?.focus();
    }, 500);
  });
</script>

<style lang="less" scoped>
  .view-account {
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: auto;
    background: linear-gradient(145deg, #e3f2fd 0%, #bbdefb 35%, #90caf9 70%, #64b5f6 100%);
    position: relative;

    &::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-image: url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI2MCIgaGVpZ2h0PSI2MCI+CiAgPGNpcmNsZSBjeD0iMTAiIGN5PSIxMCIgcj0iMiIgZmlsbD0icmdiYSgyNSwgMTE4LCAyMTAsIDAuMTIpIiAvPgo8L3N2Zz4=');
      opacity: 0.8;
      z-index: 0;
    }

    &::after {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: radial-gradient(
        ellipse 80% 50% at 50% -20%,
        rgba(45, 140, 240, 0.15),
        transparent
      );
      z-index: 0;
    }

    &-container {
      padding: 36px 44px 24px;
      max-width: 440px;
      min-width: 380px;
      margin: 0 auto;
      border-radius: 16px;
      box-shadow: 0 20px 60px rgba(13, 110, 253, 0.12), 0 8px 24px rgba(0, 0, 0, 0.06);
      margin-top: 10vh;
      position: relative;
      z-index: 1;
      backdrop-filter: blur(20px);
      background: rgba(255, 255, 255, 0.98);
      border: 1px solid rgba(255, 255, 255, 0.6);
      transition: all 0.35s ease;
      &:hover {
        box-shadow: 0 24px 64px rgba(13, 110, 253, 0.16), 0 12px 28px rgba(0, 0, 0, 0.08);
        transform: translateY(-4px);
      }
    }

    &-title {
      text-align: center;
      font-size: 20px;
      font-weight: 600;
      color: #1a1a2e;
      margin-bottom: 10px;
      position: relative;
      &::after {
        content: '';
        position: absolute;
        bottom: -12px;
        left: 50%;
        transform: translateX(-50%);
        width: 48px;
        height: 3px;
        background: linear-gradient(90deg, #2d8cf0, #0d6efd);
        border-radius: 3px;
      }
    }

    .login-welcome {
      text-align: center;
      font-size: 13px;
      color: #64748b;
      margin-bottom: 28px;
      margin-top: 24px;
    }

    &-top {
      padding: 16px 0 20px;
      text-align: center;

      &-logo {
        margin-bottom: 12px;
        display: flex;
        justify-content: center;
        .top-logo-img {
          height: 56px;
          width: auto;
          object-fit: contain;
        }
      }

      &-title {
        font-size: 26px;
        font-weight: 600;
        color: #0d6efd;
        margin: 0 0 8px;
        letter-spacing: 0.5px;
        background: linear-gradient(135deg, #2d8cf0 0%, #0d6efd 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }

      &-desc {
        font-size: 14px;
        color: #606266;
        letter-spacing: 0.3px;
      }
    }

    .default-color {
      color: #515a6e;

      .ant-checkbox-wrapper {
        color: #515a6e;
      }
    }

    .login-button {
      margin-top: 12px;
      height: 44px;
      font-size: 16px;
      font-weight: 500;
      border-radius: 8px;
      transition: all 0.3s;
      position: relative;
      overflow: hidden;
      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(13, 110, 253, 0.35);
      }
      &::after {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 5px;
        height: 5px;
        background: rgba(255, 255, 255, 0.5);
        opacity: 0;
        border-radius: 100%;
        transform: scale(1, 1) translate(-50%);
        transform-origin: 50% 50%;
      }
      &:focus:not(:active)::after {
        animation: ripple 1s ease-out;
      }
      @keyframes ripple {
        0% {
          transform: scale(0, 0);
          opacity: 0.5;
        }
        20% {
          transform: scale(25, 25);
          opacity: 0.3;
        }
        100% {
          opacity: 0;
          transform: scale(40, 40);
        }
      }
    }

    .auto-login-row {
      margin-bottom: 5px;
    }

    .register-only {
      width: 100%;
      text-align: right;
    }

    .register-link {
      color: #2d8cf0;
      transition: all 0.3s;
      &:hover {
        color: #57a3f3;
        text-decoration: underline;
      }
    }

    .login-form {
      :deep(.n-form-item-feedback-wrapper) {
        min-height: 18px;
      }
      :deep(.n-input) {
        border-radius: 8px;
      }
      padding: 0;
    }

    .login-input {
      :deep(.n-input__input-el) {
        padding-left: 5px;
      }
      :deep(.n-input-wrapper) {
        transition: all 0.3s ease;
      }
      &:hover {
        :deep(.n-input-wrapper) {
          box-shadow: 0 0 0 1px rgba(45, 140, 240, 0.2);
        }
      }
    }

    .username-item,
    .password-item {
      margin-bottom: 24px;
    }

    .captcha-item {
      margin-bottom: 24px;

      .captcha-wrapper {
        display: flex;
        gap: 12px;
        width: 100%;

        .captcha-input {
          flex: 1;
        }

        .captcha-image {
          width: 120px;
          height: 34px;
          cursor: pointer;
          border-radius: 4px;
          overflow: hidden;
          border: 1px solid #d9d9d9;
          transition: all 0.3s;
          display: flex;
          align-items: center;
          justify-content: center;

          &:hover {
            border-color: #2d8cf0;
          }

          .captcha-img {
            width: 100%;
            height: 100%;
            object-fit: cover;
          }
        }
      }
    }

    .register-row {
      margin-bottom: 0;
    }
  }

  @media (min-width: 768px) {
    .view-account {
      background-image: url('../../assets/images/login.svg'),
        radial-gradient(
          circle at 10% 20%,
          rgba(100, 149, 237, 0.25) 0%,
          rgba(65, 105, 225, 0.2) 40%,
          rgba(30, 144, 255, 0.1) 90%
        );
      background-repeat: no-repeat;
      background-position: 50%;
      background-size: cover;
      position: relative;
      &::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(135deg, rgba(45, 140, 240, 0.1), rgba(45, 140, 240, 0.05));
        backdrop-filter: blur(10px);
        z-index: 0;
      }
      &::after {
        content: '';
        position: absolute;
        width: 100%;
        height: 100%;
        top: 0;
        left: 0;
        background-image: url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPgo8ZGVmcz4KICA8cGF0dGVybiBpZD0icGF0dGVybiIgeD0iMCIgeT0iMCIgd2lkdGg9IjYwIiBoZWlnaHQ9IjYwIiBwYXR0ZXJuVW5pdHM9InVzZXJTcGFjZU9uVXNlIiBwYXR0ZXJuVHJhbnNmb3JtPSJyb3RhdGUoNDUpIj4KICAgIDxjaXJjbGUgY3g9IjMwIiBjeT0iMzAiIHI9IjEuNSIgZmlsbD0icmdiYSg0NSwgMTQwLCAyNDAsIDAuMikiIC8+CiAgPC9wYXR0ZXJuPgo8L2RlZnM+CjxyZWN0IHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIGZpbGw9InVybCgjcGF0dGVybikiIC8+Cjwvc3ZnPg==');
        opacity: 0.3;
        z-index: 0;
        pointer-events: none;
      }
      &-container {
        margin-top: 12vh;
        z-index: 1;
        position: relative;
      }
    }
  }

  @media (max-height: 650px) {
    .view-account-container {
      margin-top: 5vh;
    }
  }

  .view-account-background {
    position: absolute;
    width: 100%;
    height: 100%;
    top: 0;
    left: 0;
    overflow: hidden;
    pointer-events: none;
    z-index: 0;
    // ... 保持原有的动画样式不变
  }
</style>
