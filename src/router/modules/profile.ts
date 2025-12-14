import { RouteRecordRaw } from 'vue-router';
import { Layout } from '@/router/constant';
import { BorderOuterOutlined } from '@vicons/antd';
import { renderIcon } from '@/utils';

const routeName = 'profile';

const routes: Array<RouteRecordRaw> = [
  {
    path: '/profile',
    name: routeName,
    redirect: '/profile/index',
    component: Layout,
    meta: {
      title: '个人中心',
      sort: 3,
      isRoot: true,
      activeMenu: 'profile_index',
      icon: renderIcon(BorderOuterOutlined),
    },
    children: [
      {
        path: 'user',
        name: `${routeName}_user`,
        meta: {
          title: '用户档案',
          activeMenu: 'profile_user',
        },
        component: () => import('@/views/profile/user_props/index.vue'),
      },
      {
        path: 'holding_list',
        name: `${routeName}_holding_list`,
        meta: {
          title: '持仓情况',
          activeMenu: 'profile_holding_list',
        },
        component: () => import('@/views/profile/holding_list/index.vue'),
      },
      {
        path: 'watch_list',
        name: `${routeName}_watch_list`,
        meta: {
          title: '自选股信息',
          activeMenu: 'profile_watch_list',
        },
        component: () => import('@/views/profile/watch_list/index.vue'),
      },
      {
        path: 'report_template',
        name: `${routeName}_report_template`,
        meta: {
          title: '报告模板设置',
          activeMenu: 'profile_report_template',
        },
        component: () => import('@/views/profile/report_template/index.vue'),
      },
    ],
  },
];

export default routes;
