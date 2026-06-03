// src/router/guards.ts
import { PageEnum } from '@/enums/pageEnum';
import { ErrorPageRoute } from '@/router/base';
import { useAsyncRoute } from '@/store/modules/asyncRoute';
import { ACCESS_TOKEN } from '@/store/mutation-types';
import { storage } from '@/utils/Storage';
import type { RouteRecordRaw } from 'vue-router';
import { isNavigationFailure, Router } from 'vue-router';
import { RedirectName } from './constant';
import { useUserStore } from '@/store/modules/user';

const LOGIN_PATH = PageEnum.BASE_LOGIN;
const REGISTER_PATH = PageEnum.BASE_REGISTER;

const whitePathList = [LOGIN_PATH, REGISTER_PATH]; // no redirect whitelist

export function createRouterGuards(router: Router) {
  const asyncRouteStore = useAsyncRoute();
  const userStore = useUserStore();

  router.beforeEach(async (to, from, next) => {
    const Loading = window['$loading'] || null;
    Loading && Loading.start();

    if (from.path === LOGIN_PATH && to.name === 'errorPage') {
      next(PageEnum.BASE_HOME);
      return;
    }

    // Whitelist can be directly entered
    if (whitePathList.includes(to.path as PageEnum)) {
      next();
      return;
    }

    const token = storage.get(ACCESS_TOKEN);
    console.log('路由守卫 - token:', token);
    console.log('路由守卫 - to:', to);
    console.log('路由守卫 - from:', from);

    if (!token) {
      // You can access without permissions. You need to set the routing meta.ignoreAuth to true
      if (to.meta.ignoreAuth) {
        next();
        return;
      }
      // redirect login page
      const redirectData: { path: string; replace: boolean; query?: Recordable<string> } = {
        path: LOGIN_PATH,
        replace: true,
      };
      if (to.path) {
        redirectData.query = {
          ...redirectData.query,
          redirect: to.path,
        };
      }
      next(redirectData);
      return;
    }

    // 检查是否需要管理员权限（用户ID为1）
    if (to.meta.requiresAdmin) {
      const userId = userStore.getUserId || storage.get('USER_ID');
      console.log('检查管理员权限 - 用户ID:', userId);

      if (userId !== 1) {
        // 非管理员用户尝试访问管理员页面，重定向到首页
        console.log('非管理员用户尝试访问管理员页面，已重定向');
        // 这里需要引入 message，但路由守卫中不能直接使用，可以用其他方式提示
        next(PageEnum.BASE_HOME);
        return;
      }
    }

    if (asyncRouteStore.getIsDynamicRouteAdded) {
      next();
      return;
    }

    const permissions = userStore.getPermissions;

    const routes = await asyncRouteStore.generateRoutes(permissions);

    // 动态添加可访问路由表
    routes.forEach((item) => {
      router.addRoute(item as unknown as RouteRecordRaw);
    });

    //添加404
    const isErrorPage = router.getRoutes().findIndex((item) => item.name === ErrorPageRoute.name);
    if (isErrorPage === -1) {
      router.addRoute(ErrorPageRoute as unknown as RouteRecordRaw);
    }

    const redirectPath = (from.query.redirect || to.path) as string;
    const redirect = decodeURIComponent(redirectPath);
    const nextData = to.path === redirect ? { ...to, replace: true } : { path: redirect };
    asyncRouteStore.setDynamicRouteAdded(true);
    next(nextData);
    Loading && Loading.finish();
  });

  router.afterEach((to, _, failure) => {
    document.title = (to?.meta?.title as string) || document.title;
    if (isNavigationFailure(failure)) {
      //console.log('failed navigation', failure)
    }
    const asyncRouteStore = useAsyncRoute();
    // 在这里设置需要缓存的组件名称
    const keepAliveComponents = asyncRouteStore.keepAliveComponents;
    const currentComName: any = to.matched.find((item) => item.name == to.name)?.name;
    if (currentComName && !keepAliveComponents.includes(currentComName) && to.meta?.keepAlive) {
      // 需要缓存的组件
      keepAliveComponents.push(currentComName);
    } else if (!to.meta?.keepAlive || to.name == RedirectName) {
      // 不需要缓存的组件
      const index = asyncRouteStore.keepAliveComponents.findIndex((name) => name == currentComName);
      if (index != -1) {
        keepAliveComponents.splice(index, 1);
      }
    }
    asyncRouteStore.setKeepAliveComponents(keepAliveComponents);
    const Loading = window['$loading'] || null;
    Loading && Loading.finish();
  });

  router.onError((error) => {
    console.log(error, '路由错误');
  });
}
