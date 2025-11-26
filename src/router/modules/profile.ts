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
      sort: 3,
      isRoot: true,
      activeMenu: 'profile_index',
      icon: renderIcon(BorderOuterOutlined),
    },
    children: [
      {
        path: 'index',
        name: `${routeName}_index`,
        meta: {
          title: '用户档案',
          activeMenu: 'profile_index',
        },
        component: () => import('@/views/profile/index.vue'),
      },
    ],
  },
];

export default routes;
