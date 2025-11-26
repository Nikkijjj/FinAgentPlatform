import { RouteRecordRaw } from 'vue-router';
import { Layout } from '@/router/constant';
import { ProjectOutlined } from '@vicons/antd';
import { renderIcon } from '@/utils';

const routeName = 'agent';

const routes: Array<RouteRecordRaw> = [
  {
    path: '/agent',
    redirect: '/agent/index',
    name: routeName,
    component: Layout,
    meta: {
      sort: 2,
      isRoot: true,
      activeMenu: 'agent',
      icon: renderIcon(ProjectOutlined),
      title: '多功能AGENT',
    },
    children: [
      {
        path: 'index',
        name: `${routeName}_index`,
        meta: {
          title: '多功能AGENT',
          activeMenu: 'agent_index',
        },
        component: () => import('@/views/agent/index.vue'),
      },
    ],
  },
];

export default routes;
