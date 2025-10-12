import { RouteRecordRaw } from 'vue-router';
import { Layout } from '@/router/constant';
import { BorderOuterOutlined } from '@vicons/antd';
import { renderIcon } from '@/utils/index';

const routes: Array<RouteRecordRaw> = [
  {
    path: '/messagepush',
    name: 'messagepush',
    component: Layout,
    meta: {
      sort: 9,
      isRoot: true,
      activeMenu: 'messagepush_index',
      icon: renderIcon(BorderOuterOutlined),
    },
    children: [
      {
        path: 'index',
        name: `messagepush_index`,
        meta: {
          title: '消息推送',
          activeMenu: 'messagepush_index',
        },
        component: () => import('@/views/MessagePush/index.vue'),
      },
    ],
  },
];

export default routes;
