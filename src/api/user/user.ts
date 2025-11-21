import { genRequestHeaders, requestAPI } from '@/api/response';

export interface UserInfoType {
  _id: string; // id
  name: string; // 姓名
  account: string; // 账号
  password: string; // 密码
  user_investment_profile: InvestmentProfileType; // 用户投资配置(json)
  status: 'active' | 'annul' | undefined; // 状态“生效”/“注销”
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

export interface LoginParams {
  account: string;
  password: string;
}

/**
 * @description 用户登录
 */
export async function login(params: LoginParams) {
  return await requestAPI('/api/user/login', 'post', null, params);
}

export interface RegisterParams {
  name: string;
  account: string;
  password: string;
  user_investment_profile?: InvestmentProfileType;
}

/**
 * @description 用户注册
 */
export async function register(params: RegisterParams) {
  return await requestAPI('/api/user/register', 'post', null, params);
}

/**
 * @description 获取用户投资信息
 */
export async function getUserInvestmentProfile(token: string) {
  return await requestAPI('/api/user/investment/profile', 'get', genRequestHeaders(token), null);
}

interface UpdateUserInvestmentProfileParams {
  user_investment_profile: InvestmentProfileType;
}

/**
 * @description 更新用户信息
 */
export async function updateUserInvestmentProfile(
  token: string,
  params: UpdateUserInvestmentProfileParams
) {
  return await requestAPI('/api/user/investment/profile', 'post', genRequestHeaders(token), params);
}
