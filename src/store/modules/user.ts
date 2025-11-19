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
}

export const useUserStore = defineStore({
  id: 'app-user',
  state: (): IUserState => ({
    token: storage.get(ACCESS_TOKEN, ''),
    welcome: '',
    avatar: '',
    permissions: [],
    info: storage.get(CURRENT_USER, mockEmptyUserInfo),
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

    // 获取用户投资信息
    async fetchUserInvestmentProfile() {
      const response = await getUserInvestmentProfile(this.token);
      if (response.code == 0) this.setInvestmentProfile(response.data);
      return response;
    },

    // 更新用户投资信息
    async updateUserInvestmentProfile() {
      const params = {
        user_investment_profile: this.info.user_investment_profile,
      };
      return await updateUserInvestmentProfile(this.token, params);
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
