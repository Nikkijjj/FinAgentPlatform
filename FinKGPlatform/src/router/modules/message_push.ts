import { RouteRecordRaw } from 'vue-router';
import { Layout } from '@/router/constant';
import { EyeOutlined, HistoryOutlined, AlertOutlined } from '@vicons/antd';
import { renderIcon } from '@/utils';

const routes: Array<RouteRecordRaw> = [
  {
    path: '/message_push_today',
    name: 'message_push_today',
    component: Layout,
    meta: {
      title: '智能盯盘',
      sort: 1,
      isRoot: true,
      activeMenu: 'message_push_today',
      icon: renderIcon(EyeOutlined),
      hidden: true,
    },
    children: [
      {
        path: '',
        name: 'message_push_today_index',
        meta: {
          title: '智能盯盘',
          activeMenu: 'message_push_today',
          icon: renderIcon(EyeOutlined),
          hidden: true,
        },
        component: () => import('@/views/message_push/today/index.vue'),
      },
    ],
  },
  {
    path: '/message_push_history',
    name: 'message_push_history',
    component: Layout,
    meta: {
      title: '历史盯盘',
      sort: 2,
      isRoot: true,
      activeMenu: 'message_push_history',
      icon: renderIcon(HistoryOutlined),
      hidden: true,
    },
    children: [
      {
        path: '',
        name: 'message_push_history_index',
        meta: {
          title: '历史盯盘',
          activeMenu: 'message_push_history',
          icon: renderIcon(HistoryOutlined),
          hidden: true,
        },
        component: () => import('@/views/message_push/history/index.vue'),
      },
    ],
  },
  {
    path: '/message_push_events',
    name: 'message_push_events',
    component: Layout,
    meta: {
      title: '事件看板',
      sort: 4,
      isRoot: true,
      activeMenu: 'message_push_events',
      icon: renderIcon(AlertOutlined),
    },
    children: [
      {
        path: '',
        name: 'message_push_events_index',
        meta: {
          title: '事件看板',
          activeMenu: 'message_push_events',
          icon: renderIcon(AlertOutlined),
        },
        component: () => import('@/views/message_push/events/index.vue'),
      },
    ],
  },
  {
    path: '/message_push_dashboard',
    name: 'message_push_dashboard',
    component: Layout,
    meta: {
      title: '仪表盘',
      sort: 3,
      isRoot: true,
      activeMenu: 'message_push_dashboard',
      icon: renderIcon(EyeOutlined),
    },
    children: [
      {
        path: '',
        name: 'message_push_dashboard_index',
        meta: {
          title: '仪表盘',
          activeMenu: 'message_push_dashboard',
          icon: renderIcon(EyeOutlined),
        },
        component: () => import('@/views/message_push/dashboard/index.vue'),
      },
    ],
  },
];

export default routes;
