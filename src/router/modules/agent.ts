import { RouteRecordRaw } from 'vue-router';
import { Layout } from '@/router/constant';
import { ProjectOutlined } from '@vicons/antd';
import { renderIcon } from '@/utils/index';

const routes: Array<RouteRecordRaw> = [
  {
    path: '/agent',
    name: 'agent',
    component: Layout,
    meta: {
      sort: 10,
      isRoot: true,
      activeMenu: 'agent',
      icon: renderIcon(ProjectOutlined),
    },
    children: [
      {
        path: 'index',
        name: `agent_index`,
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
