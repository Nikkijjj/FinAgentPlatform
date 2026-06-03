import type { RouteRecordRaw } from 'vue-router';
import { Layout } from '@/router/constant';
import { ClusterOutlined } from '@vicons/antd';
import { renderIcon } from '@/utils';

const routeName = 'project_manage';

const routes: Array<RouteRecordRaw> = [
  {
    path: '/project-manage',
    name: routeName,
    component: Layout,
    redirect: '/project-manage/index',
    meta: {
      title: '图谱构建空间',
      sort: 4,
      icon: renderIcon(ClusterOutlined),
    },
    children: [
      {
        path: 'index',
        name: `${routeName}_index`,
        meta: {
          title: '图谱构建空间',
          icon: renderIcon(ClusterOutlined),
          affix: false,
        },
        component: () => import('@/views/project_manage/index.vue'),
      },
      {
        path: 'extract/:projectId',
        name: 'abstract_kg',
        meta: {
          title: '图谱构建流程',
          hidden: true,
          hideMenu: true,
          currentActiveMenu: '/project-manage/index',
        },
        component: () => import('@/views/extract_process/index.vue'),
      },
      {
        path: 'graph-editor/:projectId',
        name: 'graph_editor',
        meta: {
          title: '图谱编辑',
          hidden: true,
          hideMenu: true,
          currentActiveMenu: '/project-manage/index',
        },
        component: () => import('@/views/graph_editor/index.vue'),
      },
    ],
  },
];

export default routes;
