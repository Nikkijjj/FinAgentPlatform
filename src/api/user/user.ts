import { Alova } from '@/utils/http/alova';
import { ResultEnum } from '@/enums/httpEnum';

export interface UserInfoType {
  _id: string;
  name: string;
  account: string;
  password: string;
  stocks: {
    user_investment_profile: InvestmentProfileType;
  };
}

export interface InvestmentProfileType {
  personalized_investment_goals: {
    investment_tenure: {
      //short_term | medium_term | long_term
      tenure_type: string | undefined;
      specific_years: number | undefined;
      tenure_description: string | undefined;
    };

    expected_return: {
      annualized_return_rate: number | undefined;
      //stable | moderate | flexible
      return_stability: string | undefined;
      return_description: string | undefined;
      loss_tolerance_ratio: number | undefined;
    };
  };

  current_holdings: {
    holding_count: number | undefined;
    holding_list: StockType[];
  };

  watchlist: {
    watchlist_count: number | undefined;
    watchlist_list: {
      stock_code: string;
      stock_name: string;
      add_time: string;
      watch_remark: string;
    }[];
  };
}

export interface StockType {
  stock_code: string;
  stock_name: string;
  holding_quantity: number;
  purchase_price: number;
  purchase_time: string;
  holding_remark: string;
}

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
 * @description: 用户登录
 */
export function login(params) {
  return Alova.Post<InResult>(
    '/login',
    {
      params,
    },
    {
      meta: {
        isReturnNativeResponse: true,
      },
    }
  );
}

/**
 * @description: 用户注册
 */
export function register(params) {
  console.log(params);

  return {
    code: ResultEnum.SUCCESS,
    msg: '信息有效',
  };
}

/**
 * @description: 用户修改密码
 */
export function changePassword(params, uid) {
  return Alova.Post(`/user/u${uid}/changepw`, { params });
}

/**
 * @description: 更新用户信息
 */
export function updateUserProfile(params) {
  console.log(params);
  return {
    code: ResultEnum.SUCCESS,
    msg: '修改成功',
  };
}

/**
 * @description: 用户登出
 */
export function logout(params) {
  return Alova.Post('/login/logout', {
    params,
  });
}
