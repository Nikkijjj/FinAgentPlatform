import { RouteRecordRaw } from 'vue-router';
import { Layout } from '@/router/constant';
import {
  UserOutlined,
  ToolOutlined,
  FundOutlined,
  StarOutlined,
  FormOutlined,
  HeartOutlined,
} from '@vicons/antd';
import { renderIcon } from '@/utils';
import { AlarmOutline } from '@vicons/ionicons5';

const routeName = 'profile';

const routes: Array<RouteRecordRaw> = [
  {
    path: '/profile',
    name: routeName,
    redirect: '/profile/index',
    component: Layout,
    meta: {
      title: '配置工具',
      sort: 3,
      isRoot: true,
      activeMenu: 'profile_index',
      icon: renderIcon(ToolOutlined),
    },
    children: [
      {
        path: 'user',
        name: `${routeName}_user`,
        meta: {
          title: '账号管理',
          activeMenu: 'profile_user',
          icon: renderIcon(UserOutlined),
        },
        component: () => import('@/views/profile/user_props/index.vue'),
      },
      {
        path: 'user_prefer',
        name: `${routeName}_user_prefer`,
        meta: {
          title: '投资偏好',
          activeMenu: 'profile_user_prefer',
          icon: renderIcon(HeartOutlined),
        },
        component: () => import('@/views/profile/user_prefer/index.vue'),
      },
      {
        path: 'holding_list',
        name: `${routeName}_holding_list`,
        meta: {
          title: '持仓股票',
          activeMenu: 'profile_holding_list',
          icon: renderIcon(FundOutlined),
        },
        component: () => import('@/views/profile/holding_list/index.vue'),
      },
      {
        path: 'watch_list',
        name: `${routeName}_watch_list`,
        meta: {
          title: '自选股票',
          activeMenu: 'profile_watch_list',
          icon: renderIcon(StarOutlined),
        },
        component: () => import('@/views/profile/watch_list/index.vue'),
      },
      {
        path: 'watch_rule',
        name: `${routeName}_watch_rule`,
        meta: {
          title: '盯盘规则',
          activeMenu: 'profile_watch_rule',
          icon: renderIcon(AlarmOutline),
        },
        component: () => import('@/views/profile/watch_rule/index.vue'),
      },
      {
        path: 'report_template',
        name: `${routeName}_report_template`,
        meta: {
          title: '报告模板',
          activeMenu: 'profile_report_template',
          icon: renderIcon(FormOutlined),
        },
        component: () => import('@/views/profile/report_template/index.vue'),
      },
    ],
  },
];

export default routes;
