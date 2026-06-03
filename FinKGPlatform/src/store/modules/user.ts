// src/store/modules/user.ts
import { defineStore } from 'pinia';
import { store } from '@/store';
import { ACCESS_TOKEN, CURRENT_USER } from '@/store/mutation-types';

import {
  getUserInvestmentProfile,
  InvestmentProfileType,
  login,
  LoginParams,
  register,
  RegisterParams,
  updateUserInvestmentProfile,
  UserInfoType,
} from '@/api/user/user';
import { storage } from '@/utils/Storage';
import { mockEmptyUserInfo } from '../../../mock/user';

export interface IUserState {
  token: string;
  welcome: string;
  avatar: string;
  permissions: any[];
  info: UserInfoType;
  isLoaded: boolean;
  userId: number | null; // 添加用户ID
  username: string; // 添加用户名
}

export const useUserStore = defineStore({
  id: 'app-user',
  state: (): IUserState => ({
    token: storage.get(ACCESS_TOKEN, ''),
    welcome: '',
    avatar: '',
    permissions: [],
    info: storage.get(CURRENT_USER, mockEmptyUserInfo),
    isLoaded: false,
    userId: storage.get('USER_ID', null), // 从存储中获取用户ID
    username: storage.get('USERNAME', ''), // 从存储中获取用户名
  }),
  getters: {
    getToken(): string {
      return this.token;
    },
    getAvatar(): string {
      return this.avatar;
    },
    getName(): string {
      return this.info.name;
    },
    getEmail(): string {
      return this.info.email;
    },
    getPassword(): string {
      return this.info.password;
    },
    getUserInvestmentProfile(): InvestmentProfileType {
      return this.info.user_investment_profile;
    },
    getPermissions(): [any][] {
      return this.permissions;
    },
    getUserInfo(): UserInfoType {
      return this.info;
    },
    // 获取用户ID
    getUserId(): number | null {
      return this.userId;
    },
    // 获取用户名
    getUsername(): string {
      return this.username;
    },
    // 判断是否为管理员（ID为1的用户）
    isAdmin(): boolean {
      return this.userId === 1;
    },
  },
  actions: {
    setToken(token: string) {
      this.token = token;
    },
    setAvatar(avatar: string) {
      this.avatar = avatar;
    },
    setName(name: string) {
      this.info.name = name;
    },
    setEmail(email: string) {
      this.info.email = email;
    },
    setPassword(password: string) {
      this.info.password = password;
    },
    setInvestmentProfile(profile: InvestmentProfileType) {
      this.info.user_investment_profile = profile;
    },
    setPermissions(permissions) {
      this.permissions = permissions;
    },
    setUserInfo(info: UserInfoType) {
      this.info = info;
      storage.set(CURRENT_USER, info);
    },
    // 设置用户ID
    setUserId(userId: number) {
      this.userId = userId;
      storage.set('USER_ID', userId);
    },
    // 设置用户名
    setUsername(username: string) {
      this.username = username;
      storage.set('USERNAME', username);
    },
    clearUserInfo() {
      this.info = mockEmptyUserInfo;
      this.userId = null;
      this.username = '';
      storage.remove('USER_ID');
      storage.remove('USERNAME');
    },
    // 登录
    async login(params: LoginParams) {
      const response = await login(params);
      if (response.status == 200) {
        this.setToken(response.data.token);
        this.setName(response.data.user.username);
        // 保存用户ID和用户名
        this.setUserId(parseInt(response.data.user.id) || 0);
        this.setUsername(response.data.user.username);

        storage.set(ACCESS_TOKEN, this.getToken);
        storage.set(CURRENT_USER, {
          id: response.data.user.id,
          name: response.data.user.username,
        });
      }
      console.log('登录响应:', response);

      return response;
    },

    async register(params: RegisterParams) {
      const response = await register(params);
      return response;
    },

    // 初始化用户投资信息
    async initUserInvestmentProfile() {
      if (this.isLoaded) return;
      const response = await this.fetchUserInvestmentProfile();
      if (response.code === 0) {
        const updatedInfo = {
          ...this.info,
          user_investment_profile: response.data,
        };
        this.setUserInfo(updatedInfo);
        this.isLoaded = true;
      } else {
        const fallbackInfo = {
          ...this.info,
          user_investment_profile: mockEmptyUserInfo.user_investment_profile,
        };
        this.setUserInfo(fallbackInfo);
        this.isLoaded = true;
      }
    },

    // 获取用户投资信息
    async fetchUserInvestmentProfile() {
      return await getUserInvestmentProfile(this.token);
    },

    // 更新用户投资信息
    async updateUserInvestmentProfile(params?: {
      user_investment_profile?: InvestmentProfileType;
      user_report_template?: string;
    }) {
      const requestParams = {
        user_investment_profile:
          params?.user_investment_profile || this.info.user_investment_profile,
        user_report_template: params?.user_report_template || this.info.report_template,
      };
      return await updateUserInvestmentProfile(this.token, requestParams);
    },

    // 登出
    async logout() {
      this.setPermissions([]);
      this.clearUserInfo();
      storage.remove(ACCESS_TOKEN);
      storage.remove(CURRENT_USER);
    },
  },
});

// Need to be used outside the setup
export function useUser() {
  return useUserStore(store);
}
