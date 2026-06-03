import Mock from 'mockjs';
import { resultSuccess } from '../_util';
import { defineMock } from '@alova/mock';
import { UserInfoType } from '@/api/user/user';

const Random = Mock.Random;

const token = Random.string('upper', 32, 32);

const adminInfo = {
  userId: '1',
  username: 'admin',
  realName: 'Admin',
  avatar: Random.image(),
  desc: 'manager',
  password: Random.string('upper', 4, 16),
  token,
  permissions: [
    {
      label: '主控台',
      value: 'dashboard_console',
    },
    {
      label: '监控页',
      value: 'dashboard_monitor',
    },
    {
      label: '工作台',
      value: 'dashboard_workplace',
    },
    {
      label: '基础列表',
      value: 'basic_list',
    },
    {
      label: '基础列表删除',
      value: 'basic_list_delete',
    },
  ],
};

export const mockEmptyUserInfo: UserInfoType = {
  _id: '',
  name: '',
  account: '',
  password: '',
  user_investment_profile: {
    personalized_investment_goals: {
      investment_tenure: {
        tenure_type: undefined,
        specific_years: undefined,
        tenure_description: undefined,
      },

      expected_return: {
        annualized_return_rate: undefined,
        return_stability: undefined,
        return_description: undefined,
      },

      risk_tolerance: {
        risk_level: undefined,
        risk_description: undefined,
        loss_tolerance_ratio: undefined,
      },
    },

    current_holdings: {
      holding_count: undefined,
      holding_list: [],
    },

    watchlist: {
      watchlist_count: undefined,
      watchlist_list: [],
    },
  },
  status: undefined,
  date: '',
};

export default defineMock({
  '[POST]/api/login': () => resultSuccess({ token }),
  '/api/admin_info': () => resultSuccess(adminInfo),
});
