<template>
  <div class="aside-menu-wrapper">
    <!-- 主菜单 -->
    <div class="menu-section">
      <NMenu
        :options="menus"
        :inverted="inverted"
        :mode="mode"
        :collapsed="collapsed"
        :collapsed-width="64"
        :collapsed-icon-size="20"
        :indent="24"
        :expanded-keys="openKeys"
        :value="getSelectedKeys"
        @update:value="clickMenuItem"
        @update:expanded-keys="menuExpanded"
      />
    </div>

    <!-- 历史对话部分 - 仅在多功能AGENT页面显示 -->
    <div v-if="showChatHistory && !collapsed" class="history-section">
      <div class="history-header">
        <span class="history-title">历史对话</span>
      </div>
      <n-scrollbar style="max-height: 200px">
        <div class="history-list">
          <div
            v-for="(session, sessionId) in chatHistoryList"
            :key="sessionId"
            class="history-item"
            :class="{ active: isActiveSession(sessionId as string) }"
            @click="loadChatSession(sessionId as string)"
          >
            <n-icon size="16" class="history-icon">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path
                  d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"
                />
              </svg>
            </n-icon>
            <span class="history-text">{{ getSessionTitle(session) }}</span>
          </div>
          <div v-if="Object.keys(chatHistoryList).length === 0" class="history-empty">
            暂无历史对话
          </div>
        </div>
      </n-scrollbar>
    </div>

    <!-- 个人中心菜单 - 始终显示在底部 -->
    <div v-if="bottomMenu.length > 0 && !collapsed" class="bottom-menu-section">
      <div class="menu-divider"></div>
      <!-- 使用 NPopover 包裹配置中心菜单项 -->
      <div class="profile-menu-wrapper">
        <NPopover
          v-if="profileMenuHasChildren"
          placement="top-start"
          trigger="click"
          :show-arrow="false"
          raw
          :style="{
            padding: '2px 2px',
            margin: '0px 0px 10px 10px',
            borderRadius: '5px',
            boxShadow: '0 4px 16px rgba(0, 0, 0, 0.12)',
            width: '180px',
          }"
          :disabled="collapsed"
        >
          <template #trigger>
            <div class="profile-menu-trigger">
              <NMenu
                :options="bottomMenu"
                :inverted="inverted"
                :mode="mode"
                :collapsed="collapsed"
                :collapsed-width="64"
                :collapsed-icon-size="20"
                :indent="24"
                :expanded-keys="[]"
                :value="getSelectedKeys"
                @update:value="handleProfileMenuClick"
                class="bottom-up-menu"
              />
            </div>
          </template>
          <template #default>
            <div class="profile-popover-menu">
              <NMenu
                :options="profileChildrenMenu"
                :inverted="inverted"
                mode="vertical"
                :indent="12"
                :value="getSelectedKeys"
                @update:value="handleProfileChildClick"
                class="popover-menu-content"
              />
            </div>
          </template>
        </NPopover>
        <NMenu
          v-else
          :options="bottomMenu"
          :inverted="inverted"
          :mode="mode"
          :collapsed="collapsed"
          :collapsed-width="64"
          :collapsed-icon-size="20"
          :indent="24"
          :expanded-keys="openKeys"
          :value="getSelectedKeys"
          @update:value="clickMenuItem"
          @update:expanded-keys="menuExpanded"
          class="bottom-up-menu"
        />
      </div>
    </div>
  </div>
</template>

<script lang="ts">
  import {
    defineComponent,
    ref,
    onMounted,
    reactive,
    computed,
    watch,
    toRefs,
    unref,
    onUnmounted,
  } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { NMenu, NScrollbar, NIcon, NPopover } from 'naive-ui';
  import { useAsyncRouteStore } from '@/store/modules/asyncRoute';
  import { generatorMenu, generatorMenuMix } from '@/utils';
  import { useProjectSettingStore } from '@/store/modules/projectSetting';
  import { useProjectSetting } from '@/hooks/setting/useProjectSetting';
  import { useUserStore } from '@/store/modules/user';
  import { getChatHistoryList, ChatMessage, ChatHistoryListResponse } from '@/api/chat/chat';
  export default defineComponent({
    name: 'AsideMenu',
    components: {
      NMenu,
      NScrollbar,
      NIcon,
      NPopover,
    },
    props: {
      mode: {
        type: String,
        default: 'vertical',
      },
      collapsed: {
        type: Boolean,
      },
      location: {
        type: String,
        default: 'left',
      },
    },
    emits: ['update:collapsed', 'clickMenuItem'],
    setup(props, { emit }) {
      const currentRoute = useRoute();
      const router = useRouter();
      const asyncRouteStore = useAsyncRouteStore();
      const settingStore = useProjectSettingStore();
      const userStore = useUserStore();

      const menus = ref<any[]>([]);
      const bottomMenu = ref<any[]>([]);
      const selectedKeys = ref<string>(currentRoute.name as string);
      const headerMenuSelectKey = ref<string>('');
      const chatHistoryList = ref<ChatHistoryListResponse>({});
      let historyRefreshTimer: number | null = null;

      const { navMode } = useProjectSetting();

      const matched = currentRoute.matched;
      const getOpenKeys = matched && matched.length ? matched.map((item) => item.name) : [];

      const state = reactive({
        openKeys: getOpenKeys,
      });

      const inverted = computed(() => {
        return ['dark', 'header-dark'].includes(settingStore.navTheme);
      });

      const getSelectedKeys = computed(() => {
        let location = props.location;
        return location === 'left' || (location === 'header' && unref(navMode) === 'horizontal')
          ? unref(selectedKeys)
          : unref(headerMenuSelectKey);
      });

      // 计算主菜单和底部菜单
      const separatedMenus = computed(() => {
        const allMenus = asyncRouteStore.getMenus;
        const normalMenus: any[] = [];
        const profileMenus: any[] = [];

        allMenus.forEach(item => {
          if (item?.meta?.title === '配置工具') {
            profileMenus.push(item);
          } else {
            normalMenus.push(item);
          }
        });

        return { normalMenus, profileMenus };
      });

      // 判断配置中心菜单是否有子菜单
      const profileMenuHasChildren = computed(() => {
        return bottomMenu.value.some(menu => menu.children && menu.children.length > 0);
      });

      // 提取配置中心子菜单（用于弹出气泡）
      const profileChildrenMenu = computed(() => {
        const profileMenu = bottomMenu.value.find(menu => menu.children);
        return profileMenu?.children || [];
      });

      // 判断是否显示历史对话
      const showChatHistory = computed(() => {
        return currentRoute.path.startsWith('/agent');
      });

      // 判断是否是当前激活的会话
      const isActiveSession = (sessionId: string) => {
        return currentRoute.query.session === sessionId;
      };

      // 获取会话标题
      const getSessionTitle = (session: ChatMessage[]): string => {
        const firstUserMsg = session.find((msg) => msg.role === 'user');
        if (firstUserMsg) {
          const content = firstUserMsg.content;
          return content.length > 25 ? content.substring(0, 25) + '...' : content;
        }
        return '新对话';
      };

      // 加载聊天会话
      const loadChatSession = (sessionId: string) => {
        router.push({
          name: 'agent_index',
          query: { session: sessionId },
        });
      };

      // 获取历史对话列表
      const fetchChatHistoryList = async () => {
        try {
          const response = await getChatHistoryList(userStore.getToken);
          if (response.code === 0) {
            chatHistoryList.value = response.data;
          }
        } catch (error) {
          console.error('获取历史对话失败:', error);
        }
      };

      // 处理配置中心菜单点击
      const handleProfileMenuClick = (key: string) => {
        // 如果有子菜单，不执行路由跳转，由气泡菜单处理
        if (!profileMenuHasChildren.value) {
          clickMenuItem(key);
        }
      };

      // 处理配置中心子菜单点击
      const handleProfileChildClick = (key: string) => {
        clickMenuItem(key);
      };

      // 监听分割菜单
      watch(
        () => settingStore.menuSetting.mixMenu,
        () => {
          updateMenu();
          if (props.collapsed) {
            emit('update:collapsed', !props.collapsed);
          }
        }
      );

      // 跟随页面路由变化，切换菜单选中状态
      watch(
        () => currentRoute.fullPath,
        () => {
          updateMenu();
          // 如果在agent页面，刷新历史记录
          if (showChatHistory.value) {
            fetchChatHistoryList();
          }
        }
      );

      function updateSelectedKeys() {
        const matched = currentRoute.matched;
        state.openKeys = matched.map((item) => item.name);
        const activeMenu: string = (currentRoute.meta?.activeMenu as string) || '';
        selectedKeys.value = activeMenu ? (activeMenu as string) : (currentRoute.name as string);
      }

      function updateMenu() {
        if (!settingStore.menuSetting.mixMenu) {
          const { normalMenus, profileMenus } = separatedMenus.value;

          // 生成主菜单
          menus.value = generatorMenu(normalMenus);

          // 生成底部菜单（个人中心）
          if (profileMenus.length > 0) {
            bottomMenu.value = generatorMenu(profileMenus);
          } else {
            bottomMenu.value = [];
          }
        } else {
          // mixMenu 模式的处理逻辑保持不变
          const firstRouteName: string = (currentRoute.matched[0].name as string) || '';
          menus.value = generatorMenuMix(asyncRouteStore.getMenus, firstRouteName, props.location);
          const activeMenu: string = currentRoute?.matched[0].meta?.activeMenu as string;
          headerMenuSelectKey.value = (activeMenu ? activeMenu : firstRouteName) || '';
        }
        updateSelectedKeys();
      }

      function clickMenuItem(key: string) {
        if (/http(s)?:/.test(key)) {
          window.open(key);
        } else {
          router.push({ name: key });
        }
        emit('clickMenuItem' as any, key);
      }

      function menuExpanded(openKeys: string[]) {
        if (!openKeys) return;
        const latestOpenKey = openKeys.find((key) => state.openKeys.indexOf(key) === -1);
        const isExistChildren = findChildrenLen(latestOpenKey as string);
        state.openKeys = isExistChildren ? (latestOpenKey ? [latestOpenKey] : []) : openKeys;
      }

      function findChildrenLen(key: string) {
        if (!key) return false;
        const subRouteChildren: string[] = [];
        for (const { children, key } of unref(menus)) {
          if (children && children.length) {
            subRouteChildren.push(key as string);
          }
        }
        return subRouteChildren.includes(key);
      }

      onMounted(() => {
        updateMenu();
        if (showChatHistory.value) {
          fetchChatHistoryList();
          // 每30秒自动刷新一次历史记录
          historyRefreshTimer = window.setInterval(() => {
            if (showChatHistory.value) {
              fetchChatHistoryList();
            }
          }, 30000);
        }
      });

      onUnmounted(() => {
        if (historyRefreshTimer) {
          clearInterval(historyRefreshTimer);
        }
      });

      return {
        ...toRefs(state),
        inverted,
        menus,
        bottomMenu,
        selectedKeys,
        headerMenuSelectKey,
        getSelectedKeys,
        clickMenuItem,
        menuExpanded,
        showChatHistory,
        chatHistoryList,
        isActiveSession,
        getSessionTitle,
        loadChatSession,
        profileMenuHasChildren,
        profileChildrenMenu,
        handleProfileMenuClick,
        handleProfileChildClick,
      };
    },
  });
</script>

<style scoped lang="scss">
  .aside-menu-wrapper {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .menu-section {
    flex: 1;
    overflow-y: auto;
    color: #000;
  }

  .bottom-menu-section {
    position: absolute; // 使用绝对定位
    bottom: 0; // 紧贴底部
    left: 0;
    right: 0;
    border-top: 1px solid rgba(111, 109, 109, 0.1);
    background: inherit; // 继承父元素背景
    z-index: 1; // 确保在正常内容之上

    // 如果需要特殊样式，可以在这里添加
    :deep(.n-menu-item) {
      &.n-menu-item--selected {
        background: rgba(24, 160, 88, 0.1);
      }
    }

    .profile-menu-wrapper {
      width: 100%;
    }
  }

  .profile-menu-trigger {
    cursor: pointer;

    // 当有子菜单时，移除默认的展开箭头
    :deep(.n-menu-item-content) {
      .n-menu-item-content__icon {
        &.n-menu-item-content__expand-icon {
          display: none !important;
        }
      }
    }
  }

  .profile-popover-menu {
    background: var(--n-color);
    border-radius: 8px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);

    .popover-menu-content {
      background: transparent;

      :deep(.n-menu-item) {
        border-radius: 4px;
        margin: 2px 8px;

        &.n-menu-item--selected {
          background: rgba(24, 160, 88, 0.1);
        }

        &:hover {
          background: rgba(130, 130, 130, 0.1);
        }
      }
    }
  }

  .history-section {
    border-top: 1px solid rgba(111, 109, 109, 0.1);
    padding: 12px 0;
    background: rgba(239, 232, 232, 0.1);

    .history-header {
      padding: 8px 24px;
      margin-bottom: 8px;

      .history-title {
        color: rgba(5, 5, 5, 0.9);
        font-size: 14px;
        font-weight: 500;
      }
    }

    .history-list {
      .history-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 24px;
        cursor: pointer;
        transition: all 0.3s;
        color: rgba(5, 5, 5, 0.911);
        font-size: 14px;

        .history-icon {
          flex-shrink: 0;
          opacity: 0.7;
        }

        .history-text {
          flex: 1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        &:hover {
          background: rgba(130, 130, 130, 0.1);
          color: rgb(17, 17, 18);
          border-radius: 5px;

          .history-icon {
            opacity: 1;
          }
        }

        &.active {
          background: rgba(45, 140, 240, 0.1);
          color: #2d8cf0;
          font-weight: 500;

          .history-icon {
            opacity: 1;
            color: #2d8cf0;
          }
        }
      }

      .history-empty {
        padding: 20px 24px;
        text-align: center;
        color: rgba(255, 255, 255, 0.45);
        font-size: 13px;
      }
    }
  }
</style>
