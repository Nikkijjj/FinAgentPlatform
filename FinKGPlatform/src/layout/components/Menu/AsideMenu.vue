<template>
  <div class="aside-menu-wrapper" :class="{ 'aside-menu-wrapper--fill': mode !== 'horizontal' }">
    <!-- 主菜单 + 各类历史区：同一滚动容器，历史紧跟主菜单（不被主菜单 flex 撑到侧栏最底） -->
    <div class="aside-menu-main">
      <div class="menu-section">
        <NMenu
          :options="filteredMenus"
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

      <!-- 抽取历史部分 - 仅在图谱构建流程页面显示 -->
      <div v-if="showExtractionHistory && !collapsed" class="history-section">
      <div class="history-header">
        <span class="history-title">抽取任务</span>
      </div>
      <n-scrollbar style="max-height: 200px">
        <div class="history-list">
          <div
            v-for="item in extractionHistoryList"
            :key="item.run_id"
            class="history-item"
            :class="{ active: isActiveExtractionRun(item.run_id) }"
            @click="checkoutExtractionRun(item.run_id)"
          >
            <n-icon size="16" class="history-icon">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path
                  d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"
                />
              </svg>
            </n-icon>
            <span class="history-text">{{ getExtractionTitle(item) }}</span>
            <span class="history-rename" @click.stop="openRenameExtractionDialog(item)">重命名</span>
            <span class="history-delete" @click.stop="removeExtractionHistory(item.run_id)"
              >删除</span
            >
          </div>
          <div v-if="extractionHistoryList.length === 0" class="history-empty"> 暂无抽取历史 </div>
        </div>
      </n-scrollbar>
      </div>

      <!-- 历史对话部分 - 仅在多功能AGENT页面显示（不改变上方主路由菜单结构） -->
      <div v-if="showChatHistory && !collapsed" class="history-section">
      <div class="history-header history-header--with-action">
        <span class="history-title">历史对话</span>
        <n-button text type="primary" size="tiny" @click.stop="startNewChatSession">
          新建对话
        </n-button>
      </div>
      <n-scrollbar style="max-height: 400px">
        <div class="history-list">
          <div
            v-for="([sessionId, session]) in sortedChatHistoryEntries"
            :key="sessionId"
            class="history-item"
            :class="{ active: isActiveSession(sessionId as string) }"
            @click="loadChatSession(sessionId as string)"
            :title="sessionTitlePlain(sessionId as string, session as ChatMessage[])"
          >
            <n-icon size="16" class="history-icon">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path
                  d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"
                />
              </svg>
            </n-icon>
            <span class="history-text">{{
              displaySessionTitle(sessionId as string, session as ChatMessage[])
            }}</span>
            <span
              class="history-rename"
              @click.stop="openRenameDialog(sessionId as string, session as ChatMessage[])"
              >重命名</span
            >
            <span class="history-delete" @click.stop="removeChatSession(sessionId as string)"
              >删除</span
            >
          </div>
          <div v-if="sortedChatHistoryEntries.length === 0" class="history-empty">
            暂无历史对话
          </div>
        </div>
      </n-scrollbar>
      </div>
    </div>

    <n-modal
      v-model:show="renameModalVisible"
      preset="dialog"
      title="重命名会话"
      positive-text="保存"
      negative-text="取消"
      :positive-button-props="{ loading: renameSubmitting, disabled: renameSubmitting }"
      @positive-click="confirmRenameSession"
      style="width: 420px"
    >
      <n-input
        v-model:value="renameTitleInput"
        type="textarea"
        maxlength="500"
        show-count
        placeholder="自定义标题（展示在历史列表中）"
        :autosize="{ minRows: 2, maxRows: 6 }"
      />
    </n-modal>

    <n-modal
      v-model:show="extractionTaskModalVisible"
      preset="dialog"
      :title="extractionTaskMode === 'create' ? '新建抽取任务' : '重命名抽取任务'"
      positive-text="保存"
      negative-text="取消"
      :positive-button-props="{ loading: extractionTaskSubmitting, disabled: extractionTaskSubmitting }"
      @positive-click="submitExtractionTask"
      style="width: 420px"
    >
      <n-input
        v-model:value="extractionTaskTitleInput"
        type="textarea"
        maxlength="200"
        show-count
        placeholder="输入任务名称，便于区分同一项目下的多次抽取"
        :autosize="{ minRows: 2, maxRows: 5 }"
      />
    </n-modal>

    <!-- 个人中心菜单 - 始终显示在底部 -->
    <div v-if="filteredBottomMenu.length > 0 && !collapsed" class="bottom-menu-section">
      <!-- 修改这里：使用过滤后的底部菜单 -->
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
                :options="filteredBottomMenu"
                :inverted="inverted"
                :mode="mode"
                :collapsed="collapsed"
                :collapsed-width="64"
                :collapsed-icon-size="20"
                :indent="24"
                :expanded-keys="[]"
                :value="null"
                @update:value="handleProfileMenuClick"
                class="bottom-up-menu"
              />
            </div>
          </template>
          <template #default>
            <div class="profile-popover-menu">
              <NMenu
                :options="filteredProfileChildrenMenu"
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
          :options="filteredBottomMenu"
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
    h,
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
  import {
    NMenu,
    NScrollbar,
    NIcon,
    NPopover,
    NButton,
    NModal,
    NInput,
    useMessage,
    useNotification,
  } from 'naive-ui';
  import { useAsyncRouteStore } from '@/store/modules/asyncRoute';
  import { generatorMenu, generatorMenuMix } from '@/utils';
  import { useProjectSettingStore } from '@/store/modules/projectSetting';
  import { useProjectSetting } from '@/hooks/setting/useProjectSetting';
  import { useUserStore } from '@/store/modules/user';
  import {
    deleteChatSession,
    renameChatSession,
    getChatHistoryList,
    ChatMessage,
    ChatHistoryListResponse,
  } from '@/api/chat/chat';
  import {
    getExtractionHistoryList,
    createExtractionHistorySnapshot,
    deleteExtractionHistory,
    renameExtractionHistory,
    checkoutExtractionHistory,
    getMasterAgentTaskStatus,
    EXTRACTION_HISTORY_REFRESH_EVENT,
    type ExtractionHistoryItem,
  } from '@/api/kg/extract';

  export default defineComponent({
    name: 'AsideMenu',
    components: {
      NMenu,
      NScrollbar,
      NIcon,
      NPopover,
      NButton,
      NModal,
      NInput,
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
      const message = useMessage();
      const notification = useNotification();

      /** 抽取历史权限与 graph_project.creator 对齐（存的是登录用户名）。不能用数字 user_id 优先，否则会过滤掉全部记录。 */
      const getExtractionIdentity = (): string => {
        const byUsername = (userStore.getUsername || '').trim();
        if (byUsername) return byUsername;
        const byName = (userStore.getName || '').trim();
        if (byName) return byName;
        const id = userStore.getUserId;
        if (id != null && id !== 0) return String(id);
        return '';
      };

      const menus = ref<any[]>([]);
      const bottomMenu = ref<any[]>([]);
      const selectedKeys = ref<string>((currentRoute?.name as string) || '');
      const headerMenuSelectKey = ref<string>('');
      const chatHistoryList = ref<ChatHistoryListResponse>({});
      /** 服务端 chat_session.title，优先于首条用户消息展示 */
      const chatSessionTitles = ref<Record<string, string>>({});
      const renameModalVisible = ref(false);
      const renameTitleInput = ref('');
      const renameTargetSessionId = ref('');
      const renameSubmitting = ref(false);
      const extractionHistoryList = ref<ExtractionHistoryItem[]>([]);
      const extractionTaskModalVisible = ref(false);
      const extractionTaskSubmitting = ref(false);
      const extractionTaskTitleInput = ref('');
      const extractionTaskMode = ref<'create' | 'rename'>('create');
      const extractionRenameTargetRunId = ref('');
      const MASTER_BUILD_TASKS_KEY = 'finkg-master-build-tasks';
      const MASTER_BUILD_TASKS_UPDATED_EVENT = 'finkg-master-build-tasks-updated';
      let masterTaskPollTimer: number | null = null;
      let masterTaskPolling = false;

      interface MasterBuildTaskQueueItem {
        task_id: string;
        project_id: string;
        project_name?: string;
        mode?: 'full' | 'incremental' | string;
        created_at?: string;
        run_id?: string;
        status?: 'pending' | 'running' | 'success' | 'error' | string;
        progress?: number;
      }

      const { navMode } = useProjectSetting();

      const matched = currentRoute?.matched || [];
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

      // ============ 新增：权限过滤函数 ============
      // 递归过滤菜单，移除需要管理员权限且当前用户不是管理员的菜单
      const filterMenuByPermission = (menuItems: any[] = []): any[] => {
        if (!menuItems.length) return [];

        // 注意：这里必须是纯函数，不能在 computed 链路里原地修改 item.children，
        // 否则会触发响应式依赖回写，导致 AsideMenu 递归更新。
        return menuItems.reduce((acc: any[], item) => {
          // 检查当前菜单项是否需要管理员权限
          if (item.meta?.requiresAdmin && !userStore.isAdmin) {
            return acc;
          }

          // 递归过滤子菜单（返回新数组，不修改原对象）
          const hasChildren = Array.isArray(item.children) && item.children.length > 0;
          const filteredChildren = hasChildren ? filterMenuByPermission(item.children) : [];

          // 有 children 但过滤后为空，则丢弃该父菜单
          if (hasChildren && filteredChildren.length === 0) {
            return acc;
          }

          const nextItem = hasChildren ? { ...item, children: filteredChildren } : { ...item };
          acc.push(nextItem);
          return acc;
        }, []);
      };

      // 计算过滤后的主菜单
      const filteredMenus = computed(() => {
        return filterMenuByPermission(menus.value);
      });

      // 计算过滤后的底部菜单
      const filteredBottomMenu = computed(() => {
        return filterMenuByPermission(bottomMenu.value);
      });

      // 过滤后的配置中心子菜单
      const filteredProfileChildrenMenu = computed(() => {
        return filterMenuByPermission(profileChildrenMenu.value);
      });
      // ===========================================

      // 计算主菜单和底部菜单
      const separatedMenus = computed(() => {
        const allMenus = asyncRouteStore.getMenus;
        const normalMenus: any[] = [];
        const profileMenus: any[] = [];

        if (userStore.isAdmin) {
          const shouldHideForAdmin = (_item: any) => false;

          const configItem = allMenus.find((item) => item?.meta?.title === '配置工具');
          const projectItem = allMenus.find((item) => item?.meta?.title === '图谱构建项目');
          let adminProjectMenu: any = null;

          const manageMenu = {
            name: 'admin_manage_tool',
            path: '/admin-manage',
            meta: { title: '管理工具', icon: configItem?.meta?.icon },
            children: [] as any[]
          };

          if (projectItem) {
            const projectMenu = { ...projectItem };
            projectMenu.meta = { ...projectMenu.meta, title: '图谱构建空间' };
            if (projectMenu.children && projectMenu.children.length > 0) {
              projectMenu.children = projectMenu.children.map((child) => {
                if (child.name === 'project_manage_index') {
                  return { ...child, meta: { ...child.meta, title: '图谱构建空间' } };
                }
                return child;
              });
            }
            adminProjectMenu = projectMenu;
          }

          if (configItem && configItem.children) {
            const userManageNode = configItem.children.find((c: any) => c.name === 'profile_user_manage');
            if (userManageNode) {
              manageMenu.children.push(userManageNode);
            }
            const graphManageNode = configItem.children.find((c: any) => c.name === 'profile_graph_manage');
            if (graphManageNode) {
              manageMenu.children.push(graphManageNode);
            }
          }

          const bottomConfigMenu = configItem ? { ...configItem } : null;
          if (bottomConfigMenu) {
            // 底部的配置工具剔除用户管理，保留账号管理等原有功能
            bottomConfigMenu.children = bottomConfigMenu.children
              ? bottomConfigMenu.children.filter(
                  (c: any) => c.name !== 'profile_user_manage' && c.name !== 'profile_graph_manage'
                )
              : [];
            // 确保即使只有一个子项也不会被坍缩为没壳的单级路由
            bottomConfigMenu.meta = { ...bottomConfigMenu.meta, alwaysShow: true };
          }

          allMenus.forEach((item) => {
            if (shouldHideForAdmin(item)) {
              return;
            }
            if (item?.meta?.title === '配置工具') {
              if (bottomConfigMenu) {
                profileMenus.push(bottomConfigMenu);
              }
            } else if (item?.meta?.title === '图谱构建项目') {
              return;
            } else {
              normalMenus.push(item);
            }
          });

          if (manageMenu.children.length > 0 && !normalMenus.includes(manageMenu)) {
            normalMenus.push(manageMenu);
          }

          if (adminProjectMenu && !normalMenus.includes(adminProjectMenu)) {
            normalMenus.push(adminProjectMenu);
          }
        } else {
          allMenus.forEach((item) => {
            if (item?.meta?.title === '配置工具') {
              profileMenus.push(item);
            } else {
              normalMenus.push(item);
            }
          });
        }

        return { normalMenus, profileMenus };
      });

      // 判断配置中心菜单是否有子菜单
      const profileMenuHasChildren = computed(() => {
        return filteredBottomMenu.value.some((menu) => menu.children && menu.children.length > 0);
      });

      // 提取配置中心子菜单（用于弹出气泡）
      const profileChildrenMenu = computed(() => {
        const profileMenu = filteredBottomMenu.value.find((menu) => menu.children);
        return profileMenu?.children || [];
      });

      // 判断是否显示历史对话
      const showChatHistory = computed(() => {
        return (currentRoute?.path || '').startsWith('/agent');
      });

      // 判断是否显示抽取历史
      const showExtractionHistory = computed(() => {
        return (currentRoute?.path || '').startsWith('/project-manage/extract');
      });

      // 当前项目ID（从 extract 路由中提取）
      const extractProjectId = computed(() => {
        const path = currentRoute?.path || '';
        const m = path.match(/\/project-manage\/extract\/([^/]+)/);
        return m ? m[1] : '';
      });

      const isActiveExtractionRun = (runId: string) => {
        const q = currentRoute?.query?.run;
        return runId ? q === runId : !q;
      };

      const getExtractionTitle = (item: ExtractionHistoryItem) => {
        const t = (item.title || '').trim();
        if (t) {
          return t.length > 40 ? `${t.substring(0, 40)}…` : t;
        }
        const typeMap: Record<string, string> = {
          nodes: '节点抽取',
          relations: '关系抽取',
          master: '一键构建',
          incremental: '增量构建',
          snapshot: '手动快照',
        };
        const typeName = typeMap[item.run_type] || item.run_type;
        const date = item.created_at ? new Date(item.created_at).toLocaleDateString('zh-CN') : '';
        return `${typeName} ${item.nodes_count}节点/${item.edges_count}边 ${date}`;
      };

      const checkoutExtractionRun = async (runId: string) => {
        const target = {
          name: 'abstract_kg',
          params: { projectId: extractProjectId.value },
          query: runId ? { run: runId } : {},
        };
        const sameName = router.currentRoute.value.name === target.name;
        const sameRun = (router.currentRoute.value.query?.run || '') === (runId || '');
        
        if (!(sameName && sameRun)) {
          if (runId) {
            // 调用后端checkout接口，将该跑的节点和边恢复为项目工作区视图
            try {
              const identity = getExtractionIdentity();
              const username =
                (userStore.getUsername || userStore.getName || '').trim() || identity;
              await checkoutExtractionHistory({
                project_id: extractProjectId.value,
                run_id: runId,
                user_id: identity,
                creator: identity,
                username,
              });
              // 派发事件让 index.vue 重新加载图谱（实际上 router.push 会触发路由监听重新获取）
            } catch (e) {
              console.error('checkout 出错', e);
            }
          }
          router.push(target);
        }
      };

      const fetchExtractionHistoryList = async () => {
        if (!extractProjectId.value) return;
        try {
          // 管理员查看他人项目时：不能用 admin 身份去过滤 creator/user_id，否则会把历史筛空
          // 管理员：直接取项目下全部抽取历史
          const isAdmin = Boolean(userStore.isAdmin);
          const identity = isAdmin ? '' : getExtractionIdentity();
          if (!isAdmin && !identity) {
            extractionHistoryList.value = [];
            return;
          }
          const res = isAdmin
            ? await getExtractionHistoryList(extractProjectId.value)
            : await getExtractionHistoryList(extractProjectId.value, { user_id: identity });
          if (res.success && res.data) {
            extractionHistoryList.value = res.data.items || [];
          } else {
            extractionHistoryList.value = [];
          }
        } catch (error) {
          console.error('获取抽取历史失败:', error);
          extractionHistoryList.value = [];
        }
      };

      const removeExtractionHistory = async (runId: string) => {
        if (!extractProjectId.value || !runId) return;
        const isAdmin = Boolean(userStore.isAdmin);
        const identity = isAdmin ? '' : getExtractionIdentity();
        const username = isAdmin ? '' : (userStore.getUsername || userStore.getName || '').trim() || identity;
        if (!isAdmin && !identity) return;
        try {
          const res = await deleteExtractionHistory({
            project_id: extractProjectId.value,
            run_id: runId,
            user_id: identity,
            creator: identity,
            username,
          });
          if (res.success) {
            await fetchExtractionHistoryList();
            window.dispatchEvent(new CustomEvent(EXTRACTION_HISTORY_REFRESH_EVENT));
            const currRun = String(router.currentRoute.value.query?.run || '');
            if (currRun === runId) {
              router.push({
                name: 'abstract_kg',
                params: { projectId: extractProjectId.value },
                query: {},
              });
            }
          }
        } catch (error) {
          console.error('删除抽取历史失败:', error);
        }
      };

      const openRenameExtractionDialog = (item: ExtractionHistoryItem) => {
        extractionTaskMode.value = 'rename';
        extractionRenameTargetRunId.value = item.run_id;
        extractionTaskTitleInput.value = item.title || getExtractionTitle(item);
        extractionTaskModalVisible.value = true;
      };

      const submitExtractionTask = async (): Promise<boolean> => {
        const title = extractionTaskTitleInput.value.trim();
        if (!title) {
          message.warning('请输入任务名称');
          return false;
        }
        if (!extractProjectId.value || extractionTaskSubmitting.value) return false;
        extractionTaskSubmitting.value = true;
        const isAdmin = Boolean(userStore.isAdmin);
        const identity = isAdmin ? '' : getExtractionIdentity();
        const username = isAdmin ? '' : (userStore.getUsername || userStore.getName || '').trim() || identity;
        try {
          if (extractionTaskMode.value === 'create') {
            const res = await createExtractionHistorySnapshot({
              project_id: extractProjectId.value,
              title,
              is_empty: true,
              user_id: identity,
              creator: identity,
              username,
            });
            if (!res.success || !res.data?.run_id) {
              message.error(res.message || '创建抽取任务失败');
              return false;
            }
            extractionTaskModalVisible.value = false;
            await fetchExtractionHistoryList();
            message.success('抽取任务已创建');
            // 直接跳转到新建的空任务，此时 checkout逻辑会清理工作区并重新加载
            checkoutExtractionRun(res.data.run_id);
            return true;
          }

          const res = await renameExtractionHistory({
            project_id: extractProjectId.value,
            run_id: extractionRenameTargetRunId.value,
            title,
            user_id: identity,
            creator: identity,
            username,
          });
          if (!res.success) {
            message.error(res.message || '重命名失败');
            return false;
          }
          extractionTaskModalVisible.value = false;
          await fetchExtractionHistoryList();
          window.dispatchEvent(new CustomEvent(EXTRACTION_HISTORY_REFRESH_EVENT));
          message.success('已保存');
          return true;
        } catch (error) {
          console.error('submitExtractionTask error:', error);
          message.error(extractionTaskMode.value === 'create' ? '创建抽取任务失败' : '重命名失败');
          return false;
        } finally {
          extractionTaskSubmitting.value = false;
        }
      };

      // 判断是否是当前激活的会话
      const isActiveSession = (sessionId: string) => {
        return currentRoute?.query?.session === sessionId;
      };

      const fetchChatHistoryList = async () => {
        try {
          const userId = userStore.getUserId || userStore.getUsername || userStore.getName || '';
          const username = userStore.getUsername || userStore.getName || '';
          if (!userId && !username) {
            chatHistoryList.value = {};
            chatSessionTitles.value = {};
            return;
          }
          const response = await getChatHistoryList(userStore.getToken, {
            user_id: userId,
            username,
            uid: userId,
            limit: 50,
          });
          if (response.code === 0) {
            chatHistoryList.value = response.data || {};
            const st = (response as { session_titles?: Record<string, string> }).session_titles;
            if (st && typeof st === 'object') {
              chatSessionTitles.value = { ...st };
            } else {
              chatSessionTitles.value = {};
            }
          } else {
            chatHistoryList.value = {};
            chatSessionTitles.value = {};
          }
        } catch (error) {
          console.error('获取历史对话失败:', error);
          chatHistoryList.value = {};
          chatSessionTitles.value = {};
        }
      };

      const CHAT_HISTORY_REFRESH_EVENT = 'finkg-chat-history-refresh';
      const CHAT_RESET_EVENT = 'finkg-chat-reset-to-new';

      const parseSessionTimestamp = (sessionId: string): number => {
        const sid = String(sessionId || '');
        const match = sid.match(/^session_(\d+)_/);
        if (!match) return 0;
        const ts = Number(match[1]);
        return Number.isFinite(ts) ? ts : 0;
      };

      const sortedChatHistoryEntries = computed(() => {
        const entries = Object.entries(chatHistoryList.value || {}) as [string, ChatMessage[]][];
        return entries.sort((a, b) => {
          const ta = parseSessionTimestamp(a[0]);
          const tb = parseSessionTimestamp(b[0]);
          if (tb !== ta) return tb - ta;
          return String(b[0]).localeCompare(String(a[0]));
        });
      });

      const getCustomTitle = (sessionId: string) =>
        (chatSessionTitles.value[sessionId] || '').trim();

      const fallbackTitleFromMessages = (session: ChatMessage[]): string => {
        const firstUserMsg = session.find((msg) => msg.role === 'user');
        return firstUserMsg ? String(firstUserMsg.content || '').trim() : '';
      };

      const displaySessionTitle = (sessionId: string, session: ChatMessage[]): string => {
        const base =
          getCustomTitle(sessionId) || fallbackTitleFromMessages(session) || '新对话';
        return base;
      };

      const sessionTitlePlain = (sessionId: string, session: ChatMessage[]): string =>
        getCustomTitle(sessionId) || fallbackTitleFromMessages(session) || '新对话';

      const openRenameDialog = (sessionId: string, session: ChatMessage[]) => {
        renameTargetSessionId.value = sessionId;
        renameTitleInput.value = sessionTitlePlain(sessionId, session);
        renameModalVisible.value = true;
      };

      const confirmRenameSession = async (): Promise<boolean> => {
        const title = renameTitleInput.value.trim();
        if (!title) {
          message.warning('请输入标题');
          return false;
        }
        const sid = renameTargetSessionId.value;
        if (!sid || renameSubmitting.value) return false;
        renameSubmitting.value = true;
        try {
          const userId = userStore.getUserId || userStore.getUsername || userStore.getName || '';
          const username = userStore.getUsername || userStore.getName || '';
          const res = await renameChatSession(userStore.getToken, {
            session_id: sid,
            title,
            user_id: userId || username,
            username,
            uid: userId,
          });
          if (res.code === 0) {
            chatSessionTitles.value = { ...chatSessionTitles.value, [sid]: title };
            message.success('已保存');
            renameModalVisible.value = false;
            await fetchChatHistoryList();
            return true;
          }
          message.error((res as { msg?: string }).msg || '重命名失败');
          return false;
        } catch (e) {
          console.error(e);
          message.error('重命名失败');
          return false;
        } finally {
          renameSubmitting.value = false;
        }
      };

      /** 侧栏「新建对话」：清空 URL 会话并通知对话页复位（不改变主菜单区域） */
      const startNewChatSession = () => {
        router.replace({ name: 'agent_index', query: {} }).finally(() => {
          window.dispatchEvent(new CustomEvent(CHAT_RESET_EVENT));
          window.dispatchEvent(new CustomEvent(CHAT_HISTORY_REFRESH_EVENT));
        });
      };

      // 加载聊天会话
      const loadChatSession = (sessionId: string) => {
        const target = {
          name: 'agent_index',
          query: { session: sessionId },
        };
        const sameName = router.currentRoute.value.name === target.name;
        const sameSession = router.currentRoute.value.query?.session === sessionId;
        if (!(sameName && sameSession)) {
          router.push(target);
        }
      };

      const removeChatSession = async (sessionId: string) => {
        const userId = userStore.getUserId || userStore.getUsername || userStore.getName || '';
        const username = userStore.getUsername || userStore.getName || '';
        if (!userId && !username) return;
        try {
          const response = await deleteChatSession(userStore.getToken, {
            session_id: sessionId,
            user_id: userId || username,
            username,
            uid: userId,
          });
          if (response.code === 0) {
            await fetchChatHistoryList();
            const currSession = String(router.currentRoute.value.query?.session || '');
            if (currSession === sessionId) {
              router.push({ name: 'agent_index' });
            }
          }
        } catch (error) {
          console.error('删除会话失败:', error);
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

      // 路由 path 变化时刷新侧栏列表（不包含 query，避免切换 session/run 重复打接口）
      watch(
        () => currentRoute?.path || '',
        () => {
          if (showChatHistory.value) {
            fetchChatHistoryList();
          }
          if (showExtractionHistory.value && extractProjectId.value) {
            fetchExtractionHistoryList();
          }
        },
        { flush: 'post' }
      );

      // 跟随页面路由变化，切换菜单选中状态（含 query/hash）
      watch(
        () => currentRoute?.fullPath || '',
        () => {
          updateMenu();
        }
      );

      function updateSelectedKeys() {
        const matched = currentRoute?.matched || [];
        state.openKeys = matched.map((item) => item.name as string);
        const activeMenu: string = (currentRoute?.meta?.activeMenu as string) || '';
        selectedKeys.value = activeMenu
          ? (activeMenu as string)
          : (currentRoute?.name as string) || '';

        if (userStore.isAdmin) {
          const childNames = ['project_manage_index', 'profile_user_manage'];
          if (childNames.includes(selectedKeys.value)) {
            if (!state.openKeys.includes('admin_manage_tool')) {
              state.openKeys.push('admin_manage_tool');
            }
            if (selectedKeys.value === 'profile_user_manage') {
              state.openKeys = state.openKeys.filter((k) => k !== 'profile');
            }
          }
        }
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
          const firstRouteName: string = (currentRoute?.matched?.[0]?.name as string) || '';
          menus.value = generatorMenuMix(asyncRouteStore.getMenus, firstRouteName, props.location);
          const activeMenu: string = (currentRoute?.matched?.[0]?.meta?.activeMenu as string) || '';
          headerMenuSelectKey.value = (activeMenu ? activeMenu : firstRouteName) || '';
        }
        updateSelectedKeys();
      }

      function clickMenuItem(key: string) {
        if (/http(s)?:/.test(key)) {
          window.open(key);
        } else {
          if (router.currentRoute.value.name !== key) {
            router.push({ name: key });
          }
        }
        emit('clickMenuItem' as any, key);
      }

      function menuExpanded(openKeys: string[]) {
        if (!openKeys) return;
        const latestOpenKey = openKeys.find((key) => state.openKeys.indexOf(key) === -1);
        const isExistChildren = findChildrenLen(latestOpenKey as string);
        const newKeys = isExistChildren ? (latestOpenKey ? [latestOpenKey] : []) : openKeys;
        if (
          newKeys.length !== state.openKeys.length ||
          newKeys.some((k, i) => k !== state.openKeys[i])
        ) {
          state.openKeys = newKeys;
        }
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

      const onRefreshChatHistoryList = () => {
        if (showChatHistory.value) {
          fetchChatHistoryList();
        }
      };

      const onRefreshExtractionHistoryList = () => {
        if (showExtractionHistory.value && extractProjectId.value) {
          fetchExtractionHistoryList();
        }
      };

      const loadMasterBuildTasks = (): MasterBuildTaskQueueItem[] => {
        try {
          const raw = localStorage.getItem(MASTER_BUILD_TASKS_KEY);
          const parsed = raw ? (JSON.parse(raw) as MasterBuildTaskQueueItem[]) : [];
          return Array.isArray(parsed) ? parsed.filter((x) => !!x?.task_id) : [];
        } catch {
          return [];
        }
      };

      const saveMasterBuildTasks = (tasks: MasterBuildTaskQueueItem[]) => {
        try {
          localStorage.setItem(MASTER_BUILD_TASKS_KEY, JSON.stringify(tasks || []));
        } catch {
          /* ignore */
        }
      };

      const showMasterBuildDoneCard = (task: MasterBuildTaskQueueItem) => {
        const pname = String(task.project_name || `项目${task.project_id || ''}`).trim();
        const runId = String(task.run_id || '').trim();
        notification.success({
          title: '抽取任务完成',
          content: `您的${pname}项目抽取已完成`,
          meta: '已在后台完成，可继续查看结果',
          duration: 5500,
          keepAliveOnHover: true,
          placement: 'top-right',
          action: task.project_id
            ? () =>
                h(
                  NButton,
                  {
                    size: 'small',
                    tertiary: true,
                    type: 'primary',
                    onClick: () => {
                      const query = runId ? { run: runId } : {};
                      router.push({
                        name: 'abstract_kg',
                        params: { projectId: task.project_id },
                        query,
                      });
                    },
                  },
                  { default: () => '查看结果' }
                )
            : undefined,
        });
      };

      const showMasterBuildErrorCard = (task: MasterBuildTaskQueueItem, errText: string) => {
        const pname = String(task.project_name || `项目${task.project_id || ''}`).trim();
        notification.error({
          title: '抽取任务失败',
          content: `${pname}抽取失败：${errText || '后台构建失败'}`,
          meta: '请稍后重试或检查后端日志',
          duration: 6000,
          keepAliveOnHover: true,
          placement: 'top-right',
        });
      };

      const pollMasterBuildTasks = async () => {
        if (masterTaskPolling) return;
        const queue = loadMasterBuildTasks();
        if (!queue.length) return;

        masterTaskPolling = true;
        try {
          const remained: MasterBuildTaskQueueItem[] = [];
          for (const task of queue) {
            const taskId = String(task.task_id || '').trim();
            if (!taskId) continue;
            try {
              const res = await getMasterAgentTaskStatus(taskId);
              if (!res.success || !res.data) {
                remained.push(task);
                continue;
              }

              const status = String(res.data.status || '').trim();
              const merged: MasterBuildTaskQueueItem = {
                ...task,
                status,
                progress: Number(res.data.progress || task.progress || 0),
                run_id: String(res.data.run_id || task.run_id || '').trim() || task.run_id,
              };

              if (status === 'success') {
                showMasterBuildDoneCard(merged);
                window.dispatchEvent(new CustomEvent(EXTRACTION_HISTORY_REFRESH_EVENT));
                continue;
              }

              if (status === 'error') {
                const err = String(res.data.error || res.data.message || '后台构建失败').trim();
                showMasterBuildErrorCard(merged, err);
                continue;
              }

              remained.push(merged);
            } catch (error) {
              console.error('轮询后台构建任务失败:', error);
              remained.push(task);
            }
          }
          saveMasterBuildTasks(remained);
        } finally {
          masterTaskPolling = false;
        }
      };

      const onMasterBuildTasksUpdated = () => {
        void pollMasterBuildTasks();
      };

      onMounted(() => {
        updateMenu();
        if (showChatHistory.value) {
          fetchChatHistoryList();
        }
        if (showExtractionHistory.value && extractProjectId.value) {
          fetchExtractionHistoryList();
        }
        window.addEventListener(CHAT_HISTORY_REFRESH_EVENT, onRefreshChatHistoryList);
        window.addEventListener(EXTRACTION_HISTORY_REFRESH_EVENT, onRefreshExtractionHistoryList);
        window.addEventListener(MASTER_BUILD_TASKS_UPDATED_EVENT, onMasterBuildTasksUpdated);
        void pollMasterBuildTasks();
        masterTaskPollTimer = window.setInterval(() => {
          void pollMasterBuildTasks();
        }, 4000);
      });

      onUnmounted(() => {
        window.removeEventListener(CHAT_HISTORY_REFRESH_EVENT, onRefreshChatHistoryList);
        window.removeEventListener(EXTRACTION_HISTORY_REFRESH_EVENT, onRefreshExtractionHistoryList);
        window.removeEventListener(MASTER_BUILD_TASKS_UPDATED_EVENT, onMasterBuildTasksUpdated);
        if (masterTaskPollTimer !== null) {
          window.clearInterval(masterTaskPollTimer);
          masterTaskPollTimer = null;
        }
      });

      return {
        mode: props.mode,
        ...toRefs(state),
        inverted,
        menus,
        bottomMenu,
        filteredMenus,
        filteredBottomMenu,
        filteredProfileChildrenMenu,
        selectedKeys,
        headerMenuSelectKey,
        getSelectedKeys,
        clickMenuItem,
        menuExpanded,
        showChatHistory,
        chatHistoryList,
        sortedChatHistoryEntries,
        isActiveSession,
        displaySessionTitle,
        sessionTitlePlain,
        renameModalVisible,
        renameTitleInput,
        renameSubmitting,
        openRenameDialog,
        confirmRenameSession,
        startNewChatSession,
        loadChatSession,
        removeChatSession,
        showExtractionHistory,
        extractionHistoryList,
        extractionTaskModalVisible,
        extractionTaskSubmitting,
        extractionTaskTitleInput,
        extractionTaskMode,
        isActiveExtractionRun,
        getExtractionTitle,
        checkoutExtractionRun,
        removeExtractionHistory,
        openRenameExtractionDialog,
        submitExtractionTask,
        profileMenuHasChildren,
        profileChildrenMenu,
        handleProfileMenuClick,
        handleProfileChildClick,
        currentRoute,
      };
    },
  });
</script>

<style scoped lang="scss">
  .aside-menu-wrapper {
    display: flex;
    flex-direction: column;
    min-height: 0;
    width: 100%;
  }

  /* 仅纵向侧栏：占满 Logo 以下剩余高度，才能把「配置工具」稳定撑在侧栏底部 */
  .aside-menu-wrapper--fill {
    flex: 1 1 auto;
  }

  /* 主菜单与历史区共用中间可滚动区域：历史紧跟主菜单，空白留在历史与「配置工具」之间 */
  .aside-menu-main {
    flex: 1 1 0%;
    min-height: 0;
    overflow-x: hidden;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
  }

  .menu-section {
    flex: 0 0 auto;
    color: #000;
  }

  .bottom-menu-section {
    flex-shrink: 0;
    border-top: 1px solid rgba(111, 109, 109, 0.1);
    background: inherit;
    z-index: 1;

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
    flex-shrink: 0;
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

      &--with-action {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
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

        .history-rename {
          flex-shrink: 0;
          font-size: 12px;
          color: rgba(45, 140, 240, 0.95);
          display: none;
        }

        .history-delete {
          flex-shrink: 0;
          font-size: 12px;
          color: rgba(230, 70, 70, 0.9);
          display: none;
        }

        &:hover {
          background: rgba(130, 130, 130, 0.1);
          color: rgb(17, 17, 18);
          border-radius: 5px;

          .history-icon {
            opacity: 1;
          }
          .history-delete,
          .history-rename {
            display: inline;
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
