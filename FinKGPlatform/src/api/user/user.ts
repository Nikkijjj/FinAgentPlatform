// src/api/user/user.ts
import { genRequestHeaders, requestAPI } from '@/api/response';

// 定义API基础路径常量
const API_BASE = {
  PROJECT: '/api', // 项目后端
  AUTH: '/auth', // 认证服务后端
};

// ============ 用户管理相关接口 ============

// 用户数据类型
export interface UserType {
  id: number;
  user_name: string;
  email: string;
  create_time: string;
}

// 创建用户参数
export interface CreateUserParams {
  username: string;
  password: string;
  email?: string;
}

// 更新用户参数
export interface UpdateUserParams {
  username?: string;
  password?: string;
  email?: string;
}

// 获取所有用户（不分页）- 用于前端分页
export async function getAllUsers(search?: string) {
  const timestamp = new Date().getTime();
  return (await requestAPI('/old-api/users/all', 'get', null, {
    search,
    _t: timestamp,
  })) as Promise<{
    status: number;
    message: string;
    data: {
      list: UserType[];
      total: number;
    };
  }>;
}

// 获取用户列表（分页）- 保留向后兼容
export async function getUsers(params: { page?: number; pageSize?: number; search?: string }) {
  const timestamp = new Date().getTime();
  return (await requestAPI('/old-api/users', 'get', null, {
    ...params,
    _t: timestamp,
  })) as Promise<{
    status: number;
    message: string;
    data: {
      list: UserType[];
      total: number;
      page: number;
      pageSize: number;
    };
  }>;
}

// 获取单个用户
export async function getUser(userId: number) {
  const timestamp = new Date().getTime();
  return (await requestAPI(`/old-api/users/${userId}`, 'get', null, { _t: timestamp })) as Promise<{
    status: number;
    message: string;
    data: UserType;
  }>;
}

// 创建用户
export async function createUser(params: CreateUserParams) {
  return (await requestAPI('/old-api/users', 'post', null, params)) as Promise<{
    status: number;
    message: string;
    data: {
      id: number;
      username: string;
      email: string;
      create_time: string;
    };
  }>;
}

// 更新用户
export async function updateUser(userId: number, params: UpdateUserParams) {
  return (await requestAPI(`/old-api/users/${userId}`, 'put', null, params)) as Promise<{
    status: number;
    message: string;
  }>;
}

// 删除用户
export async function deleteUser(userId: number) {
  return (await requestAPI(`/old-api/users/${userId}`, 'delete', null, null)) as Promise<{
    status: number;
    message: string;
  }>;
}

// 批量删除用户
export async function batchDeleteUsers(userIds: number[]) {
  return (await requestAPI('/old-api/users/batch', 'delete', null, {
    user_ids: userIds,
  })) as Promise<{
    status: number;
    message: string;
    data: {
      deleted_count: number;
    };
  }>;
}

// ============ 原有的 UserInfoType 和投资相关接口 ============

export interface UserInfoType {
  _id: string; // id
  name: string; // 姓名
  // account: string; // 账号
  email: string; // 邮箱
  password: string; // 密码
  report_template: {
    before_report: string;
    noon_report: string;
    after_report: string;
  };
  user_investment_profile: InvestmentProfileType; // 用户投资配置(json)
  status: '生效' | '失效' | undefined; // 状态“生效”/“注销”
  date: string; // 用户创建时间
}

export interface InvestmentProfileType {
  personalized_investment_goals: {
    investment_tenure: {
      tenure_type: 'short_term' | 'medium_term' | 'long_term' | undefined;
      specific_years: number | undefined;
      tenure_description?: string | undefined;
    };

    expected_return: {
      annualized_return_rate: number | undefined;
      return_stability: 'stable' | 'moderate' | 'flexible' | undefined;
      return_description?: string | undefined;
    };

    risk_tolerance: {
      risk_level: 'conservative' | 'moderate' | 'aggressive' | 'radical' | undefined;
      risk_description?: string | undefined;
      loss_tolerance_ratio: number | undefined;
    };
  };

  current_holdings: {
    holding_count: number | undefined;
    holding_list: StockType[];
  };

  watchlist: {
    watchlist_count: number | undefined;
    watchlist_list: WatchlistStockType[];
  };
}

export interface StockType {
  stock_code: string;
  stock_name: string;
  holding_quantity: number;
  purchase_price: number;
  purchase_time: string | number | null;
  holding_remark?: string;
}

export interface WatchlistStockType {
  stock_code: string;
  stock_name: string;
  add_time: string | number | null;
  watch_remark: string;
}

export const emptyWatchlistStock = {
  stock_code: '',
  stock_name: '',
  add_time: null,
  watch_remark: '',
};

export const emptyStock = {
  stock_code: '',
  stock_name: '',
  holding_quantity: 0,
  purchase_price: 0,
  purchase_time: null,
  holding_remark: '',
};

// ============ 认证服务相关接口 (新后端 - /auth) ============

// 验证码响应数据类型
export interface CaptchaResponse {
  status: number;
  message: string;
  data: {
    id: string;
    svg: string;
  };
}

// 登录参数类型 - 适配后端接口
export interface LoginParams {
  name: string; // 后端使用 name 而不是 account
  password: string;
  captchaText: string; // 验证码文本
  captchaId: string; // 验证码ID
}

// 登录响应数据类型
export interface LoginResponse {
  status: number;
  message: string;
  data: {
    token: string;
    user: {
      id: string;
      username: string;
    };
    expires_in: number;
  };
}

/**
 * @description 获取验证码 - 使用认证服务
 */
export async function getCaptcha() {
  // 注意：这里使用完整的路径，包括 /auth 前缀
  return (await requestAPI(
    '/auth/old-api/public/captcha',
    'get',
    null,
    null
  )) as Promise<CaptchaResponse>;
}

/**
 * @description 用户登录 - 使用认证服务
 * @param params 登录参数
 */
export async function login(params: LoginParams) {
  // 注意：这里使用完整的路径，包括 /auth 前缀
  return (await requestAPI(
    '/auth/old-api/public/login',
    'post',
    null,
    params
  )) as Promise<LoginResponse>;
}

/**
 * @description 退出登录 - 使用认证服务
 * @param token 用户token
 */
export async function logout(token: string) {
  return await requestAPI('/auth/user/logout', 'post', genRequestHeaders(token), null);
}

/**
 * @description 获取用户信息 - 使用认证服务
 * @param token 用户token
 */
export async function getUserInfo(token: string) {
  return await requestAPI('/auth/user/info', 'get', genRequestHeaders(token), null);
}

/**
 * @description 修改密码 - 使用认证服务
 * @param token 用户token
 * @param params 修改密码参数
 */
export async function changePassword(
  token: string,
  params: { oldPassword: string; newPassword: string }
) {
  return await requestAPI('/auth/user/change-password', 'post', genRequestHeaders(token), params);
}

// ============ 项目原有接口 (保持不变 - /api) ============

export interface RegisterParams {
  name: string;
  // account: string;
  email: string;
  password: string;
  user_investment_profile?: InvestmentProfileType;
}

/**
 * @description 用户注册 - 项目原有接口
 */
export async function register(params: RegisterParams) {
  return await requestAPI('/auth/old-api/public/register', 'post', null, params);
}

/**
 * @description 获取用户投资信息
 */
export async function getUserInvestmentProfile(token: string) {
  return await requestAPI('/api/user/investment/profile', 'get', genRequestHeaders(token), null);
}

interface UpdateUserInvestmentProfileParams {
  user_investment_profile: InvestmentProfileType;
  user_report_template: string;
}

/**
 * @description 更新用户信息
 */
export async function updateUserInvestmentProfile(
  token: string,
  params: UpdateUserInvestmentProfileParams
) {
  return await requestAPI(
    '/api/user/investment/update_profile',
    'post',
    genRequestHeaders(token),
    params
  );
}

/**
 * @description 获取盯盘规则
 */
export async function getRule(token: string) {
  return await requestAPI('/api/user/rules', 'get', genRequestHeaders(token), null);
}

interface UpdateRulesParams {
  event_type: string;
  event_subtype: string;
  related_stock: string;
  event_description: string;
  trigger_condition: string;
}

/**
 * @description 更新盯盘规则
 */
export async function updateRules(token: string, params: UpdateRulesParams) {
  return await requestAPI('/api/user/update/user_rules', 'post', genRequestHeaders(token), params);
}

interface UpdateUserBaseInfoParams {
  name: string;
  email?: string;
  old_password?: string;
  new_password?: string;
}

/**
 * @description 修改用户名称和/或密码
 */
export async function updateUserBaseInfo(token: string, params: UpdateUserBaseInfoParams) {
  return await requestAPI('/api/user/update_info', 'post', genRequestHeaders(token), params);
}
