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
    getAccount(): string {
      return this.info.account;
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
    setAccount(account: string) {
      this.info.account = account;
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
    clearUserInfo() {
      this.info = mockEmptyUserInfo;
    },
    // 登录
    async login(params: LoginParams) {
      const response = await login(params);
      if (response.code == 0) {
        this.setToken(response.data.token);
        this.setName(response.data.name);
        this.setAccount(params.account);
        this.setPassword(params.password);
        storage.set(ACCESS_TOKEN, this.getToken);
        storage.set(CURRENT_USER, this.getUserInfo);
      }
      return response;
    },

    // 注册
    async register(params: RegisterParams) {
      return await register(params);
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
// store/modules/user.ts 中的方法修改
async updateUserInvestmentProfile(params?: {
  user_investment_profile?: InvestmentProfileType;
  user_report_template?: string;
}) {
  // 优先使用传入的参数，否则用本地存储的信息
  const requestParams = {
    user_investment_profile: params?.user_investment_profile || this.info.user_investment_profile,
    // 新增 user_report_template 字段
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
