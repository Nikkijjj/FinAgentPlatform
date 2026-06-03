// src/router/modules/profile.ts
import { RouteRecordRaw } from 'vue-router';
import { Layout } from '@/router/constant';
import {
  UserOutlined,
  ToolOutlined,
  FundOutlined,
  StarOutlined,
  FormOutlined,
  HeartOutlined,
  TeamOutlined, // 添加团队图标
  ClusterOutlined,
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
          hidden: true,
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
          hidden: true,
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
          hidden: true,
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
          hidden: true,
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
          hidden: true,
        },
        component: () => import('@/views/profile/report_template/index.vue'),
      },
      {
        path: 'user_manage',
        name: `${routeName}_user_manage`,
        meta: {
          title: '用户管理',
          activeMenu: 'profile_user_manage',
          icon: renderIcon(TeamOutlined), // 使用团队图标
          requiresAdmin: true, // 添加管理员权限标识
        },
        component: () => import('@/views/profile/user_manage/index.vue'),
      },
      {
        path: 'graph_manage',
        name: `${routeName}_graph_manage`,
        meta: {
          title: '图谱管理',
          activeMenu: 'profile_graph_manage',
          icon: renderIcon(ClusterOutlined),
          requiresAdmin: true,
        },
        component: () => import('@/views/profile/graph_manage/index.vue'),
      },
    ],
  },
];

export default routes;
