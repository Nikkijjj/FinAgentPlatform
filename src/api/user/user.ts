import { Alova } from '@/utils/http/alova';
import request from '@/utils/axios';
import { badResponse } from '@/api/response';

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
      risk_tolerance: {
        risk_level: 'conservative' | 'moderate' | 'aggressive' | 'radical' | undefined;
        risk_description?: string | undefined;
        loss_tolerance_ratio: number | undefined;
      };
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

/**
 * @description: 获取用户信息
 */
export function getUserInfo() {
  return Alova.Get<InResult>('/admin_info', {
    meta: {
      isReturnNativeResponse: true,
    },
  });
}

/**
 * @description: 用户修改密码
 */
export function changePassword(params, uid) {
  return Alova.Post(`/user/u${uid}/changepw`, { params });
}

/**
 * @description: 用户登出
 */
export function logout(params) {
  return Alova.Post('/login/logout', {
    params,
  });
}

export interface LoginParams {
  account: string;
  password: string;
}

/**
 * @description: 用户登录
 */
export async function login(params: LoginParams) {
  try {
    const result = await request.post('/api/user/login', {
      ...params,
    });
    return result.data ?? badResponse;
  } catch (error) {
    console.error(error);
    return badResponse;
  }
}

export interface RegisterParams {
  name: string;
  account: string;
  password: string;
  user_investment_profile?: InvestmentProfileType;
}

/**
 * @description: 用户注册
 */
export async function register(params: RegisterParams) {
  try {
    const result = await request.post('/api/user/register', {
      ...params,
    });
    return result.data ?? badResponse;
  } catch (error) {
    console.error(error);
    return badResponse;
  }
}

export async function getUserInvestmentProfile(token: string) {
  try {
    const result = await request.get('/api/user/investment/profile', {
      headers: {
        Authorization: token,
      },
    });
    return result.data ?? badResponse;
  } catch (error) {
    console.error(error);
    return badResponse;
  }
}

interface UpdateUserInvestmentProfileParams {
  user_investment_profile: InvestmentProfileType;
}

/**
 * @description: 更新用户信息
 */
export async function updateUserInvestmentProfile(
  token: string,
  params: UpdateUserInvestmentProfileParams
) {
  try {
    const result = await request.post('/api/user/investment/update_profile', params, {
      headers: {
        Authorization: token,
      },
    });
    return result.data ?? badResponse;
  } catch (error) {
    console.error(error);
    return badResponse;
  }
}
