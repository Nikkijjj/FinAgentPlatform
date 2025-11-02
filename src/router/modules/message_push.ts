import { RouteRecordRaw } from 'vue-router';
import { Layout } from '@/router/constant';
import { BorderOuterOutlined } from '@vicons/antd';
import { renderIcon } from '@/utils';

const routeName = 'message_push';

const routes: Array<RouteRecordRaw> = [
  {
    path: '/message_push',
    name: routeName,
    redirect: '/message_push/index',
    component: Layout,
    meta: {
      sort: 1,
      isRoot: true,
      activeMenu: 'message_push_index',
      icon: renderIcon(BorderOuterOutlined),
    },
    children: [
      {
        path: 'index',
        name: `${routeName}_index`,
        meta: {
          title: '消息推送',
          activeMenu: 'message_push_index',
        },
        component: () => import('@/views/message_push/index.vue'),
      },
    ],
  },
];

export default routes;
