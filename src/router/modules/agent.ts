import { RouteRecordRaw } from 'vue-router';
import { Layout } from '@/router/constant';
import { MessageOutlined, UserSwitchOutlined } from '@vicons/antd';
import { renderIcon } from '@/utils';

const routeName = 'agent';

const routes: Array<RouteRecordRaw> = [
  {
    path: '/agent',
    redirect: '/agent/index',
    name: routeName,
    component: Layout,
    meta: {
      sort: 4,
      isRoot: true,
      activeMenu: 'agent',
      icon: renderIcon(MessageOutlined),
      title: '智能分析',
    },
    children: [
      {
        path: 'index',
        name: `${routeName}_index`,
        meta: {
          title: '智能分析',
          activeMenu: 'agent_index',
        },
        component: () => import('@/views/agent/index.vue'),
      },
    ],
  },
];

export default routes;
