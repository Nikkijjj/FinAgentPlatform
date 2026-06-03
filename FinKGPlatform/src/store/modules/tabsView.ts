import { RedirectName } from '@/router/constant';
import { defineStore } from 'pinia';
import { RouteLocationNormalized } from 'vue-router';

// 不需要出现在标签页中的路由
const whiteList = [RedirectName, `${RedirectName}Son`, 'login'];

export type RouteItem = Partial<RouteLocationNormalized> & {
  fullPath: string;
  path: string;
  name: string;
  hash: string;
  meta: object;
  params: object;
  query: object;
};

export type ITabsViewState = {
  tabsList: RouteItem[]; // 标签页
};

//保留固定路由
function retainAffixRoute(list: any[]) {
  return list.filter((item) => item?.meta?.affix ?? false);
}

function getRouteIdentity(route: Partial<RouteItem>): string {
  const name = String(route?.name || '').trim();
  if (name) return `name:${name}`;
  const path = String(route?.path || '').trim();
  if (path) return `path:${path}`;
  const title = String((route as any)?.meta?.title || '').trim();
  if (title) return `title:${title}`;
  return `full:${String(route?.fullPath || '').trim()}`;
}

function normalizeTabsByIdentity(routes: RouteItem[]): RouteItem[] {
  const result: RouteItem[] = [];
  const indexByIdentity = new Map<string, number>();
  for (const route of routes || []) {
    if (!route) continue;
    const key = getRouteIdentity(route);
    const idx = indexByIdentity.get(key);
    if (idx === undefined) {
      indexByIdentity.set(key, result.length);
      result.push(route);
      continue;
    }
    // 同一导航仅保留一个标签，后来的路由信息覆盖前者（用于更新 query/fullPath）
    result[idx] = { ...result[idx], ...route };
  }
  return result;
}

export const useTabsViewStore = defineStore({
  id: 'app-tabs-view',
  state: (): ITabsViewState => ({
    tabsList: [],
  }),
  getters: {},
  actions: {
    initTabs(routes: RouteItem[]) {
      // 初始化标签页
      this.tabsList = normalizeTabsByIdentity(routes || []);
    },
    addTab(route: RouteItem): boolean {
      // 添加标签页
      if (whiteList.includes(route.name)) return false;
      const identity = getRouteIdentity(route);
      const existsIndex = this.tabsList.findIndex((item) => getRouteIdentity(item) === identity);
      if (existsIndex >= 0) {
        this.tabsList[existsIndex] = { ...this.tabsList[existsIndex], ...route };
      } else {
        this.tabsList.push(route);
      }
      return true;
    },
    closeLeftTabs(route: RouteItem) {
      // 关闭左侧
      const index = this.tabsList.findIndex((item) => item.fullPath == route.fullPath);
      this.tabsList = this.tabsList.filter((item, i) => i >= index || (item?.meta?.affix ?? false));
    },
    closeRightTabs(route: RouteItem) {
      // 关闭右侧
      const index = this.tabsList.findIndex((item) => item.fullPath == route.fullPath);
      this.tabsList = this.tabsList.filter((item, i) => i <= index || (item?.meta?.affix ?? false));
    },
    closeOtherTabs(route: RouteItem) {
      // 关闭其他
      this.tabsList = this.tabsList.filter(
        (item) => item.fullPath == route.fullPath || (item?.meta?.affix ?? false)
      );
    },
    closeCurrentTab(route: RouteItem) {
      // 关闭当前页
      const index = this.tabsList.findIndex((item) => item.fullPath == route.fullPath);
      this.tabsList.splice(index, 1);
    },
    closeAllTabs() {
      // 关闭全部
      this.tabsList = retainAffixRoute(this.tabsList);
    },
  },
});
