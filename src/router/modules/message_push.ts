import { RouteRecordRaw } from 'vue-router';
import { Layout } from '@/router/constant';
import { BorderOuterOutlined } from '@vicons/antd';
import { renderIcon } from '@/utils';

const routeName = 'message_push';

const routes: Array<RouteRecordRaw> = [
  {
    path: '/message_push',
    name: routeName,
    redirect: '/message_push/today',
    component: Layout,
    meta: {
      title: '消息推送',
      sort: 1,
      isRoot: true,
      activeMenu: 'message_push_index',
      icon: renderIcon(BorderOuterOutlined),
    },
    children: [
      {
        path: 'today',
        name: `${routeName}_today`,
        meta: {
          title: '今日消息',
          activeMenu: 'message_push_today',
        },
        component: () => import('@/views/message_push/today/index.vue'),
      },
      {
        path: 'history',
        name: `${routeName}_history`,
        meta: {
          title: '历史消息',
          activeMenu: 'message_push_history',
        },
        component: () => import('@/views/message_push/history/index.vue'),
      },
    ],
  },
];

export default routes;
