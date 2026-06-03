<template>
  <div class="agent-page" :style="{ '--platform-primary': designStore.appTheme }">
    <div class="agent-page__bg" aria-hidden="true" />
    <div class="agent-page__inner">
      <section
        ref="workspaceRef"
        class="agent-workspace"
        :class="{ 'agent-workspace--resizing': isResizingSplit }"
        :style="{ '--kg-pane-width': `${leftPaneWidthPercent}%` }"
      >
        <aside class="kg-pane">
          <div class="kg-pane__header">
            <h2>图谱检索</h2>
            <p>先筛选图谱范围，再与右侧助手进行对照分析</p>
          </div>

          <div class="kg-filters">
            <n-select
              v-model:value="graphFilter.projectIds"
              :options="projectOptions"
              :loading="projectOptionsLoading"
              filterable
              clearable
              multiple
              :max-tag-count="3"
              size="small"
              label-field="label"
              value-field="value"
              placeholder="请选择一个或多个项目"
            />
            <div class="kg-filters__row">
              <n-input
                v-model:value="graphFilter.nodeKeyword"
                placeholder="节点关键词"
                clearable
                size="small"
              />
              <n-select
                v-model:value="graphFilter.nodeType"
                :options="nodeTypeOptions"
                size="small"
                class="kg-filters__type"
              />
            </div>
            <n-input
              v-model:value="graphFilter.edgeKeyword"
              placeholder="关系关键词"
              clearable
              size="small"
            />
            <div class="kg-filters__actions">
              <n-button size="small" type="primary" :loading="graphLoading" @click="loadGraphSource">
                加载图谱
              </n-button>
              <n-button size="small" tertiary :disabled="graphLoading" @click="resetGraphFilter">
                重置
              </n-button>
            </div>
          </div>

          <div class="kg-stats">
            <span>节点 {{ filteredNodes.length }}</span>
            <span>关系 {{ filteredEdges.length }}</span>
          </div>

          <div class="kg-canvas-shell">
            <div v-if="!graphLoading && !graphNodesRaw.length" class="kg-empty">当前无可展示图谱</div>
            <div v-else-if="!filteredNodes.length && !graphLoading" class="kg-empty">当前筛选条件下无图谱结果</div>
            <div
              v-show="filteredNodes.length > 0 || graphLoading"
              ref="kgCanvasShellRef"
              class="kg-canvas-stage"
            >
              <div class="kg-overlay-tools">
                <n-button
                  size="small"
                  circle
                  secondary
                  :disabled="!filteredNodes.length"
                  @click="zoomOutGraph"
                  title="缩小"
                >
                  <template #icon>
                    <n-icon :component="RemoveOutline" />
                  </template>
                </n-button>
                <n-button
                  size="small"
                  circle
                  secondary
                  :disabled="!filteredNodes.length"
                  @click="zoomInGraph"
                  title="放大"
                >
                  <template #icon>
                    <n-icon :component="AddOutline" />
                  </template>
                </n-button>
                <n-button
                  size="small"
                  circle
                  secondary
                  :disabled="!filteredNodes.length"
                  @click="resetGraphZoom"
                  title="重置缩放"
                >
                  <template #icon>
                    <n-icon :component="ScanOutline" />
                  </template>
                </n-button>
                <n-button
                  size="small"
                  circle
                  secondary
                  :disabled="!filteredNodes.length"
                  @click="toggleGraphFullscreen"
                  :title="isGraphFullscreen ? '退出全屏' : '全屏查看'"
                >
                  <template #icon>
                    <n-icon :component="isGraphFullscreen ? ContractOutline : ExpandOutline" />
                  </template>
                </n-button>
              </div>
              <div class="kg-zoom-indicator">缩放 {{ Math.round(graphZoomLevel * 100) }}%</div>
              <div ref="graphPanelRef" class="kg-canvas"></div>
            </div>
          </div>
        </aside>

        <div
          class="workspace-splitter"
          role="separator"
          aria-orientation="vertical"
          aria-label="调整左右区域宽度"
          @mousedown="startResizeSplit"
        >
          <span class="workspace-splitter__bar" aria-hidden="true"></span>
        </div>

        <section class="agent-chat-shell">
        <div class="chat-hero">
          <p class="chat-hero__meta">事件图谱 · 跨项目检索 · 会话记忆</p>
          <div class="chat-hero__main">
            <h1 class="chat-hero__title">智能图谱检索助手</h1>
            <p class="chat-hero__subtitle">
              左侧图谱筛选结果可作为参照，右侧对话支持深度推理与可选联网补强。
            </p>
          </div>
        </div>
        <div class="chat-container">
          <div class="chat-header">
            <div class="chat-header__brand">
              <div class="chat-header__icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path
                    d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"
                    stroke="currentColor"
                    stroke-width="1.25"
                  />
                  <path
                    d="M8.5 12.5l2 2 5-5"
                    stroke="currentColor"
                    stroke-width="1.25"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                </svg>
              </div>
              <div class="chat-header__main">
                <span class="chat-header__title">对话</span>
                <span class="chat-header__hint">Enter 发送 · Shift+Enter 换行</span>
              </div>
            </div>
            <div class="chat-actions">
              <n-button
                quaternary
                size="small"
                class="chat-actions__btn"
                :disabled="isLoading"
                @click="createNewChat"
              >
                <template #icon>
                  <n-icon>
                    <svg viewBox="0 0 24 24" fill="currentColor">
                      <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" />
                    </svg>
                  </n-icon>
                </template>
                新对话
              </n-button>
              <n-button quaternary size="small" class="chat-actions__btn" @click="clearAllMessages">
                <template #icon>
                  <n-icon>
                    <svg viewBox="0 0 24 24" fill="currentColor">
                      <path
                        d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"
                      />
                    </svg>
                  </n-icon>
                </template>
                清空
              </n-button>
            </div>
          </div>

          <div class="chat-messages" ref="messagesContainer">
            <div v-for="(m, index) in messages" :key="index" class="message" :class="m.type">
              <div class="message-side">
                <div class="message-role">{{ m.type === 'ai-message' ? '助手' : '我' }}</div>
                <div class="message-avatar">
                  <n-avatar
                    round
                    size="small"
                    :src="m.type === 'ai-message' ? aiAvatar : userAvatar"
                    :fallback-src="m.type === 'ai-message' ? aiAvatarFallback : userAvatarFallback"
                  />
                </div>
              </div>
              <div class="message-content">
                <div class="message-text">
                  <pre v-if="m.isTemplate">{{ m.content }}</pre>
                  <template v-else-if="m.type === 'ai-message'">
                    <div
                      v-if="m.deepThink && ((m.reasoning || '').trim() || m.streaming)"
                      class="reasoning-panel"
                    >
                      <button
                        type="button"
                        class="reasoning-panel__header"
                        @click="toggleReasoning(index)"
                      >
                        <span class="reasoning-panel__title">思考过程</span>
                        <span class="reasoning-panel__toggle">{{
                          m.reasoningCollapsed ? '展开' : '收起'
                        }}</span>
                      </button>
                      <div v-show="!m.reasoningCollapsed" class="reasoning-panel__body">
                        <pre v-if="(m.reasoning || '').trim()" class="reasoning-panel__pre">{{
                          m.reasoning
                        }}</pre>
                        <div v-else-if="m.streaming" class="reasoning-panel__placeholder">
                          <n-spin size="small" />
                          <span>思考中…</span>
                        </div>
                      </div>
                    </div>
                    <div v-if="m.streaming && !(m.content || '').trim()" class="ai-stream-placeholder">
                      <n-spin size="small" />
                      <span>正在生成回答…</span>
                    </div>
                    <div
                      v-else
                      v-html="purifyMarkdown(renderMarkdown(m.content))"
                      class="markdown-content"
                      :class="{ 'markdown-content--streaming': m.streaming && (m.content || '').trim() }"
                    ></div>
                    <div
                      v-if="m.webEvidenceCards && m.webEvidenceCards.length > 0 && !m.streaming"
                      class="payload-web-cards"
                    >
                      <article
                        v-for="(card, cidx) in m.webEvidenceCards"
                        :key="`${cidx}-${card.url}`"
                        class="payload-web-card"
                      >
                        <div class="payload-web-card__head">
                          <span v-if="card.chip" class="payload-web-card__chip">{{ card.chip }}</span>
                          <span class="payload-web-card__tag">网页摘要</span>
                        </div>
                        <h4 class="payload-web-card__title">{{ card.title }}</h4>
                        <p v-if="card.summary" class="payload-web-card__summary">{{ card.summary }}</p>
                        <a
                          :href="card.url"
                          target="_blank"
                          rel="noopener noreferrer"
                          class="payload-web-card__cta"
                        >
                          查看原文
                        </a>
                        <div class="payload-web-card__actions">
                          <n-button
                            size="tiny"
                            type="primary"
                            secondary
                            :disabled="!card.projectId"
                            :loading="injectingWebCardKey === cardInjectKey(card)"
                            @click="handleInjectWebCard(card)"
                          >
                            加入现有图谱
                          </n-button>
                        </div>
                        <div class="payload-web-card__url">{{ card.url }}</div>
                      </article>
                    </div>
                    <p
                      v-if="m.sourceFootnote && !m.streaming"
                      class="reply-source-footnote"
                    >
                      {{ m.sourceFootnote }}
                    </p>
                    <div
                      v-if="canOpenDiagnosticDrawer && !m.streaming && hasDiagnosticData(m.diagnosticPayload)"
                      class="diagnostic-trigger"
                    >
                      <n-button
                        text
                        size="tiny"
                        type="primary"
                        @click="openDiagnosticDrawer(m.diagnosticPayload)"
                      >
                        诊断详情
                      </n-button>
                    </div>
                  </template>
                  <span v-else>{{ m.content }}</span>
                </div>
                <div class="message-actions">
                  <n-button text size="tiny" @click="copyMessage(m.content)" class="copy-btn" style="margin-right: 8px" title="复制内容">
                    <template #icon>
                      <n-icon size="14">
                        <svg viewBox="0 0 24 24" fill="currentColor">
                          <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z" />
                        </svg>
                      </n-icon>
                    </template>
                  </n-button>
                  <n-button text size="tiny" @click="deleteMessage(index)" class="delete-btn" title="删除消息">
                    <template #icon>
                      <n-icon size="14">
                        <svg viewBox="0 0 24 24" fill="currentColor">
                          <path
                            d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"
                          />
                        </svg>
                      </n-icon>
                    </template>
                  </n-button>
                </div>
              </div>
            </div>
          </div>

          <div class="chat-input-area">
            <div class="composer-settings">
              <div class="composer-settings__items">
                <label
                  class="composer-chip"
                  :class="{ 'composer-chip--active': deepThink }"
                >
                  <span class="composer-chip__label">深度思考</span>
                  <n-switch v-model:value="deepThink" size="small" />
                </label>
                <label
                  class="composer-chip"
                  :class="{ 'composer-chip--active': enableWebSearch }"
                >
                  <span class="composer-chip__label">联网补强</span>
                  <n-switch v-model:value="enableWebSearch" size="small" />
                </label>
              </div>
            </div>
            <div class="composer">
              <n-input
                v-model:value="userInput"
                type="textarea"
                placeholder="输入问题，例如：某公司近期重大事件与关联实体？"
                :autosize="{ minRows: 3, maxRows: 10 }"
                @keydown.enter.exact.prevent="handleSendMessage"
                class="composer__input"
                ref="inputRef"
                :disabled="isLoading"
              />
              <n-button
                type="primary"
                class="composer__send"
                :disabled="!userInput.trim() || isLoading"
                @click="handleSendMessage"
                :loading="isLoading"
              >
                <template #icon>
                  <n-icon>
                    <svg viewBox="0 0 24 24" fill="currentColor">
                      <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                    </svg>
                  </n-icon>
                </template>
                发送
              </n-button>
            </div>
          </div>
        </div>
        </section>
      </section>
    </div>

    <n-drawer
      v-model:show="diagnosticDrawerVisible"
      placement="right"
      :width="420"
      :auto-focus="false"
    >
      <n-drawer-content title="问答诊断信息" closable>
        <div class="diagnostic-drawer">
          <p class="diagnostic-drawer__hint">
            管理员调试信息，仅用于排查检索与融合链路；不影响当前回答展示。
          </p>

          <section class="diagnostic-section">
            <h4>quality_hints</h4>
            <pre>{{ formatDiagnosticJson(activeDiagnosticPayload?.quality_hints) }}</pre>
          </section>

          <section class="diagnostic-section">
            <h4>web_search_meta</h4>
            <p v-if="activeDiagnosticPayload?.web_search_meta" class="diagnostic-web-hint">
              {{ webSearchMissHint(activeDiagnosticPayload?.web_search_meta) || '联网元数据可用于解释为何未合并网页摘要。' }}
            </p>
            <pre>{{ formatDiagnosticJson(activeDiagnosticPayload?.web_search_meta) }}</pre>
          </section>

          <section class="diagnostic-section">
            <h4>retrieval_debug</h4>
            <pre>{{ formatDiagnosticJson(activeDiagnosticPayload?.retrieval_debug) }}</pre>
          </section>
        </div>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script lang="ts" setup>
  import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
  import {
    AddOutline,
    ContractOutline,
    ExpandOutline,
    RemoveOutline,
    ScanOutline,
  } from '@vicons/ionicons5';
  import {
    NAvatar,
    NButton,
    NIcon,
    NInput,
    NSelect,
    NSpin,
    NSwitch,
    useDialog,
    useMessage,
  } from 'naive-ui';
  import { marked } from 'marked';
  import DOMPurify from 'dompurify';
  import { useRoute, useRouter } from 'vue-router';
  import { useUserStore } from '@/store/modules/user';
  import { useDesignSettingStore } from '@/store/modules/designSetting';
  import {
    getChatHistory,
    ChatMessage,
    getKgQaReplyStream,
    type KgQaParams,
  } from '@/api/chat/chat';
  import { getProjectList } from '@/api/project/project';
  import { injectMockEvent } from '@/api/evolution';
  import { getEdgesByProject, getNodesByProject } from '@/api/kg/extract';
  import echarts from '@/utils/lib/echarts';
  import {
    getNodeVisualColor,
    normalizeEdgeDisplayLabel,
    normalizeNodeCategoryFromNode,
    normalizeNodeDisplayName,
    resolveNodeVisualCategory,
    sortVisualCategoryNames,
  } from '@/utils/kg/graph';
  import aiAvatarImage from '@/assets/images/AI_asis.jpg';

  const message = useMessage();
  const dialog = useDialog();
  const route = useRoute();
  const router = useRouter();
  const userStore = useUserStore();
  const designStore = useDesignSettingStore();

  const userInput = ref<string>('');
  const kgCanvasShellRef = ref<HTMLElement | null>(null);
  const graphPanelRef = ref<HTMLElement | null>(null);
  const graphLoading = ref(false);
  const graphZoomLevel = ref(1);
  const isGraphFullscreen = ref(false);
  const graphFilter = ref({
    projectIds: [] as string[],
    nodeKeyword: '',
    nodeType: 'all' as 'all' | 'entity' | 'event',
    edgeKeyword: '',
  });
  const graphNodesRaw = ref<any[]>([]);
  const graphEdgesRaw = ref<any[]>([]);
  const filteredNodes = ref<any[]>([]);
  const filteredEdges = ref<any[]>([]);
  const workspaceRef = ref<HTMLElement | null>(null);
  const leftPaneWidthPercent = ref(46);
  const isResizingSplit = ref(false);
  const projectOptionsLoading = ref(false);
  const projectOptions = ref<Array<{ label: string; value: string }>>([]);
  const nodeTypeOptions = [
    { label: '全部类型', value: 'all' },
    { label: '实体', value: 'entity' },
    { label: '事件', value: 'event' },
  ];
  let graphChart: echarts.ECharts | null = null;
  let graphResizeObserver: ResizeObserver | null = null;
  const GRAPH_SERIES_ID = 'agent-kg-series';
  const GRAPH_MIN_ZOOM = 0.25;
  const GRAPH_MAX_ZOOM = 4;
  const GRAPH_SPOTLIGHT_POLL_ATTEMPTS = 6;
  const GRAPH_SPOTLIGHT_POLL_INTERVAL_MS = 1200;
  const GRAPH_SPOTLIGHT_DURATION_MS = 12000;
  const GRAPH_SPOTLIGHT_MAX_ITEMS = 24;
  const SPLIT_MIN_PERCENT = 30;
  const SPLIT_MAX_PERCENT = 62;
  const graphSpotlightNodeIds = ref<Set<string>>(new Set());
  const graphSpotlightEdgeIds = ref<Set<string>>(new Set());
  let focusGraphSpotlightTimer: number | null = null;
  let clearGraphSpotlightTimer: number | null = null;
  let renderedNodeIndexById = new Map<string, number>();
  let renderedEdgeIndexById = new Map<string, number>();

  const messages = ref<
    Array<{
      type: string;
      content: string;
      isTemplate?: boolean;
      streaming?: boolean;
      deepThink?: boolean;
      reasoning?: string;
      reasoningCollapsed?: boolean;
      /** 回答下方小号来源说明（通用 / 图谱 / 联网补强等） */
      sourceFootnote?: string;
      /** 结构化网页证据卡片（从后端 evidence 中提取） */
      webEvidenceCards?: Array<{
        title: string;
        url: string;
        summary: string;
        chip?: string;
        projectId?: string;
      }>;
      diagnosticPayload?: {
        quality_hints?: unknown;
        web_search_meta?: unknown;
        retrieval_debug?: unknown;
      };
    }>
  >([]);
  const messagesContainer = ref<HTMLElement>();
  const inputRef = ref<any>();
  const isLoading = ref<boolean>(false);
  const currentSessionId = ref<string>('');
  const deepThink = ref<boolean>(false);
  const enableWebSearch = ref<boolean>(false);
  const injectingWebCardKey = ref<string>('');
  const diagnosticDrawerVisible = ref<boolean>(false);
  const activeDiagnosticPayload = ref<{
    quality_hints?: unknown;
    web_search_meta?: unknown;
    retrieval_debug?: unknown;
  } | null>(null);

  const canOpenDiagnosticDrawer = computed<boolean>(() => Boolean(userStore.isAdmin));

  const WEB_SEARCH_STORAGE_KEY = 'finkg-agent-web-search';

  const normalizeText = (v: unknown): string => String(v ?? '').trim();

  const isStackedWorkspace = (): boolean => window.matchMedia('(max-width: 1280px)').matches;

  const applySplitByClientX = (clientX: number) => {
    const container = workspaceRef.value;
    if (!container) return;
    const rect = container.getBoundingClientRect();
    if (!rect.width) return;
    const rawPercent = ((clientX - rect.left) / rect.width) * 100;
    leftPaneWidthPercent.value = Math.min(
      SPLIT_MAX_PERCENT,
      Math.max(SPLIT_MIN_PERCENT, Number(rawPercent.toFixed(2)))
    );
  };

  const onSplitResizeMove = (evt: MouseEvent) => {
    if (!isResizingSplit.value) return;
    applySplitByClientX(evt.clientX);
  };

  const stopResizeSplit = () => {
    if (!isResizingSplit.value) return;
    isResizingSplit.value = false;
    document.body.style.userSelect = '';
    document.body.style.cursor = '';
  };

  const startResizeSplit = (evt: MouseEvent) => {
    if (isStackedWorkspace()) return;
    evt.preventDefault();
    isResizingSplit.value = true;
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'col-resize';
    applySplitByClientX(evt.clientX);
  };

  const isNodeTypeMatched = (node: any, type: 'all' | 'entity' | 'event'): boolean => {
    if (type === 'all') return true;
    const t = normalizeNodeCategoryFromNode(node);
    return type === 'entity' ? t === 0 : t === 1;
  };

  const ensureGraphChart = () => {
    if (!graphPanelRef.value) return null;
    if (!graphChart) {
      graphChart = echarts.init(graphPanelRef.value);
      graphChart.on('graphroam', syncGraphZoomFromChart);
    }
    return graphChart;
  };

  const syncGraphZoomFromChart = () => {
    if (!graphChart) return;
    const option = graphChart.getOption() as any;
    const rawZoom = option?.series?.[0]?.zoom;
    const zoom = Number(rawZoom);
    if (!Number.isFinite(zoom)) return;
    graphZoomLevel.value = Math.max(GRAPH_MIN_ZOOM, Math.min(GRAPH_MAX_ZOOM, zoom));
  };

  const applyGraphZoom = (targetZoom: number) => {
    if (!graphChart) return;
    const nextZoom = Math.max(GRAPH_MIN_ZOOM, Math.min(GRAPH_MAX_ZOOM, targetZoom));
    const currentZoom = graphZoomLevel.value || 1;
    if (!Number.isFinite(nextZoom) || Math.abs(nextZoom - currentZoom) < 0.001) return;

    graphChart.setOption({
      series: [
        {
          id: GRAPH_SERIES_ID,
          zoom: nextZoom,
        },
      ],
    });
    graphZoomLevel.value = nextZoom;
  };

  const zoomInGraph = () => {
    applyGraphZoom(graphZoomLevel.value * 1.2);
  };

  const zoomOutGraph = () => {
    applyGraphZoom(graphZoomLevel.value / 1.2);
  };

  const resetGraphZoom = () => {
    applyGraphZoom(1);
  };

  const toggleGraphFullscreen = async () => {
    const container = kgCanvasShellRef.value;
    if (!container) return;
    try {
      if (document.fullscreenElement === container) {
        await document.exitFullscreen();
      } else {
        await container.requestFullscreen();
      }
    } catch (err) {
      console.error('toggleGraphFullscreen failed:', err);
    }
  };

  const handleGraphFullscreenChange = () => {
    isGraphFullscreen.value = document.fullscreenElement === kgCanvasShellRef.value;
    graphChart?.resize();
  };

  const sleep = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));

  const buildEdgeIdentity = (edge: any): string => {
    const edgeId = String(edge?.id || '').trim();
    if (edgeId) return edgeId;
    const from = String(edge?.from || edge?.source || '').trim();
    const to = String(edge?.to || edge?.target || '').trim();
    const value = String(edge?.value || edge?.eventRel || edge?.type || '').trim();
    return `${from}->${to}::${value}`;
  };

  const centerGraphOnNodeIndex = (nodeIndex: number) => {
    if (!graphChart || nodeIndex < 0) return;
    try {
      const chartAny = graphChart as any;
      const seriesModel = chartAny?.getModel?.()?.getSeriesById?.(GRAPH_SERIES_ID);
      const dataList = seriesModel?.getData?.();
      const layout = dataList?.getItemLayout?.(nodeIndex);
      const x = Number(layout?.x ?? layout?.[0]);
      const y = Number(layout?.y ?? layout?.[1]);
      if (!Number.isFinite(x) || !Number.isFinite(y)) return;

      const rect = graphPanelRef.value?.getBoundingClientRect();
      const centerX = rect ? rect.width / 2 : 0;
      const centerY = rect ? rect.height / 2 : 0;

      graphChart.dispatchAction({
        type: 'graphRoam',
        seriesId: GRAPH_SERIES_ID,
        dx: centerX - x,
        dy: centerY - y,
      });
    } catch (err) {
      console.warn('centerGraphOnNodeIndex failed:', err);
    }
  };

  const spotlightGraphChanges = (nodeIds: string[], edgeIds: string[]) => {
    const nextNodeIds = nodeIds.slice(0, GRAPH_SPOTLIGHT_MAX_ITEMS);
    const nextEdgeIds = edgeIds.slice(0, GRAPH_SPOTLIGHT_MAX_ITEMS);
    graphSpotlightNodeIds.value = new Set(nextNodeIds);
    graphSpotlightEdgeIds.value = new Set(nextEdgeIds);
    renderFilteredGraph();

    if (focusGraphSpotlightTimer !== null) {
      window.clearTimeout(focusGraphSpotlightTimer);
      focusGraphSpotlightTimer = null;
    }

    focusGraphSpotlightTimer = window.setTimeout(() => {
      if (!graphChart) return;

      graphChart.dispatchAction({ type: 'downplay', seriesId: GRAPH_SERIES_ID });

      nextNodeIds.forEach((id) => {
        const nodeIndex = renderedNodeIndexById.get(id);
        if (nodeIndex == null) return;
        graphChart?.dispatchAction({
          type: 'highlight',
          seriesId: GRAPH_SERIES_ID,
          dataIndex: nodeIndex,
        });
      });

      nextEdgeIds.forEach((id) => {
        const edgeIndex = renderedEdgeIndexById.get(id);
        if (edgeIndex == null) return;
        graphChart?.dispatchAction({
          type: 'highlight',
          seriesId: GRAPH_SERIES_ID,
          dataType: 'edge',
          dataIndex: edgeIndex,
        });
      });

      let focusNodeIndex: number | undefined;
      if (nextNodeIds.length) {
        focusNodeIndex = renderedNodeIndexById.get(nextNodeIds[0]);
      } else if (nextEdgeIds.length) {
        const candidateEdge = filteredEdges.value.find(
          (edge: any) => buildEdgeIdentity(edge) === nextEdgeIds[0]
        );
        const fallbackNodeId = String(
          candidateEdge?.from || candidateEdge?.source || candidateEdge?.to || candidateEdge?.target || ''
        ).trim();
        if (fallbackNodeId) {
          focusNodeIndex = renderedNodeIndexById.get(fallbackNodeId);
        }
      }

      if (focusNodeIndex != null) {
        graphChart.dispatchAction({
          type: 'focusNodeAdjacency',
          seriesId: GRAPH_SERIES_ID,
          dataIndex: focusNodeIndex,
        });
        centerGraphOnNodeIndex(focusNodeIndex);
      }
    }, 180);

    if (clearGraphSpotlightTimer !== null) {
      window.clearTimeout(clearGraphSpotlightTimer);
      clearGraphSpotlightTimer = null;
    }
    clearGraphSpotlightTimer = window.setTimeout(() => {
      graphSpotlightNodeIds.value = new Set();
      graphSpotlightEdgeIds.value = new Set();
      renderFilteredGraph();
    }, GRAPH_SPOTLIGHT_DURATION_MS);
  };

  const ensureProjectVisibleInGraph = (projectId: string) => {
    if (!projectId) return;
    const currentIds = (graphFilter.value.projectIds || []).map((id) => String(id || '').trim()).filter(Boolean);
    if (!currentIds.length) {
      graphFilter.value.projectIds = [projectId];
      return;
    }
    if (currentIds.includes(projectId)) return;
    graphFilter.value.projectIds = [...currentIds, projectId];
  };

  const collectProjectGraphDelta = (
    beforeNodeIds: Set<string>,
    beforeEdgeIds: Set<string>,
    projectId: string
  ): { newNodeIds: string[]; newEdgeIds: string[] } => {
    const newNodeIds = graphNodesRaw.value
      .filter((node: any) => String(node?.project_id || '').trim() === projectId)
      .map((node: any) => String(node?.id || '').trim())
      .filter((id: string) => id && !beforeNodeIds.has(id));

    const newEdgeIds = graphEdgesRaw.value
      .filter((edge: any) => String(edge?.project_id || '').trim() === projectId)
      .map((edge: any) => buildEdgeIdentity(edge))
      .filter((id: string) => id && !beforeEdgeIds.has(id));

    return {
      newNodeIds: Array.from(new Set(newNodeIds)),
      newEdgeIds: Array.from(new Set(newEdgeIds)),
    };
  };

  const focusInjectedGraphChanges = async (
    projectId: string,
    beforeNodeIds: Set<string>,
    beforeEdgeIds: Set<string>,
    preferredNodeIds: string[] = [],
    preferredEdgeIds: string[] = []
  ): Promise<{ newNodeIds: string[]; newEdgeIds: string[] } | null> => {
    if (!projectId) return null;

    ensureProjectVisibleInGraph(projectId);
    graphFilter.value.nodeKeyword = '';
    graphFilter.value.edgeKeyword = '';
    graphFilter.value.nodeType = 'all';

    const normalizedPreferredNodeIds = Array.from(
      new Set((preferredNodeIds || []).map((id) => String(id || '').trim()).filter(Boolean))
    );
    const normalizedPreferredEdgeIds = Array.from(
      new Set((preferredEdgeIds || []).map((id) => String(id || '').trim()).filter(Boolean))
    );

    if (normalizedPreferredNodeIds.length || normalizedPreferredEdgeIds.length) {
      await loadGraphSource();
      spotlightGraphChanges(normalizedPreferredNodeIds, normalizedPreferredEdgeIds);
      return {
        newNodeIds: normalizedPreferredNodeIds,
        newEdgeIds: normalizedPreferredEdgeIds,
      };
    }

    for (let attempt = 0; attempt < GRAPH_SPOTLIGHT_POLL_ATTEMPTS; attempt += 1) {
      await loadGraphSource();
      const delta = collectProjectGraphDelta(beforeNodeIds, beforeEdgeIds, projectId);
      if (delta.newNodeIds.length || delta.newEdgeIds.length) {
        spotlightGraphChanges(delta.newNodeIds, delta.newEdgeIds);
        return delta;
      }
      if (attempt < GRAPH_SPOTLIGHT_POLL_ATTEMPTS - 1) {
        await sleep(GRAPH_SPOTLIGHT_POLL_INTERVAL_MS);
      }
    }
    return null;
  };

  const loadProjectOptions = async () => {
    projectOptionsLoading.value = true;
    try {
      const res = await getProjectList({
        creator: userStore.getUsername || '',
        view_scope: 'mine',
        page: 1,
        page_size: 500,
      });
      const list = Array.isArray(res?.projectList) ? res.projectList : [];
      projectOptions.value = list.map((item: any) => ({
        label: `${String(item?.project_name || '未命名项目')}（${String(item?.id || '')}）`,
        value: String(item?.id || ''),
      }));
    } catch (err) {
      console.error('loadProjectOptions error:', err);
      projectOptions.value = [];
    } finally {
      projectOptionsLoading.value = false;
    }
  };

  const initializeGraphProjects = async () => {
    await loadProjectOptions();
    const queryProjectId = String(route.query.project_id || route.query.projectId || '').trim();
    if (queryProjectId) {
      graphFilter.value.projectIds = [queryProjectId];
      await loadGraphSource();
      return;
    }
    graphFilter.value.projectIds = getAllProjectIdsFromOptions();
    await loadGraphSource();
  };

  const renderFilteredGraph = () => {
    const chart = ensureGraphChart();
    if (!chart) return;

    const nodes = filteredNodes.value || [];
    const edges = filteredEdges.value || [];
    if (!nodes.length) {
      chart.clear();
      graphZoomLevel.value = 1;
      renderedNodeIndexById = new Map<string, number>();
      renderedEdgeIndexById = new Map<string, number>();
      return;
    }

    const nodeMap = new Map(nodes.map((n: any) => [String(n?.id), n]));
    const degreeMap = new Map<string, number>();
    edges.forEach((e: any) => {
      const source = String(e?.from || e?.source || '').trim();
      const target = String(e?.to || e?.target || '').trim();
      if (source) degreeMap.set(source, (degreeMap.get(source) || 0) + 1);
      if (target) degreeMap.set(target, (degreeMap.get(target) || 0) + 1);
    });

    const visualCategoryNames = sortVisualCategoryNames(
      Array.from(new Set(nodes.map((n: any) => resolveNodeVisualCategory(n))))
    );
    const categoryIndexMap = new Map<string, number>(
      visualCategoryNames.map((name, index) => [name, index])
    );

    const categories = visualCategoryNames.map((name) => ({
      name,
      itemStyle: {
        color: getNodeVisualColor(name),
      },
    }));

    const graphData = nodes.map((n: any) => {
      const nodeId = String(n?.id || '');
      const isSpotlight = graphSpotlightNodeIds.value.has(nodeId);
      const categoryName = resolveNodeVisualCategory(n);
      const degree = degreeMap.get(nodeId) || 0;
      const baseSize = normalizeNodeCategoryFromNode(n) === 1 ? 42 : 30;
      return {
        id: nodeId,
        name: normalizeNodeDisplayName(n),
        value: n?.key || '',
        key: n?.key || '',
        categoryName,
        category: categoryIndexMap.get(categoryName) ?? 0,
        degree,
        symbolSize: Math.min(72, baseSize + Math.sqrt(degree) * 3 + (isSpotlight ? 6 : 0)),
        itemStyle: {
          color: getNodeVisualColor(categoryName),
          borderColor: isSpotlight ? '#f59e0b' : '#ffffff',
          borderWidth: isSpotlight ? 2.8 : 1.4,
          shadowBlur: isSpotlight ? 18 : 8,
          shadowColor: isSpotlight ? 'rgba(245, 158, 11, 0.48)' : 'rgba(15, 23, 42, 0.18)',
        },
      };
    });

    renderedNodeIndexById = new Map<string, number>(
      graphData.map((item: any, index: number) => [String(item.id), index])
    );

    const graphLinks = edges.map((e: any) => {
      const from = String(e?.from || e?.source || '').trim();
      const to = String(e?.to || e?.target || '').trim();
      const edgeId = buildEdgeIdentity(e);
      const isSpotlight = graphSpotlightEdgeIds.value.has(edgeId);
      const fromNode = nodeMap.get(from);
      const toNode = nodeMap.get(to);
      return {
        id: edgeId,
        source: from,
        target: to,
        displayLabel: normalizeEdgeDisplayLabel(e, fromNode, toNode),
        lineStyle: {
          width: isSpotlight ? 2.8 : 1.3,
          color: isSpotlight ? '#f59e0b' : undefined,
          opacity: isSpotlight ? 0.95 : 0.62,
        },
      };
    });

    renderedEdgeIndexById = new Map<string, number>(
      graphLinks.map((item: any, index: number) => [String(item.id), index])
    );

    const nodeCount = graphData.length;
    const repulsion = nodeCount <= 30 ? 480 : nodeCount <= 90 ? 330 : 220;
    const edgeLength = nodeCount <= 30 ? [100, 200] : nodeCount <= 90 ? [80, 160] : [60, 130];

    chart.setOption(
      {
        backgroundColor: 'transparent',
        tooltip: {
          formatter: (params: any) => {
            if (params.dataType === 'edge') {
              return `关系：${params.data?.displayLabel || '-'}<br/>起点：${params.data?.source || '-'}<br/>终点：${params.data?.target || '-'}`;
            }
            const d = params.data || {};
            return `节点：${d.name || '-'}<br/>类别：${d.categoryName || '-'}<br/>Key：${d.key || '-'}<br/>连接数：${d.degree || 0}`;
          },
        },
        legend: [
          {
            data: visualCategoryNames,
            top: 6,
            left: 'center',
            itemWidth: 10,
            itemHeight: 10,
            textStyle: {
              color: '#334155',
              fontSize: 12,
            },
          },
        ],
        series: [
          {
            id: GRAPH_SERIES_ID,
            type: 'graph',
            layout: 'force',
            roam: true,
            zoom: graphZoomLevel.value,
            draggable: true,
            data: graphData,
            links: graphLinks,
            categories,
            force: {
              repulsion,
              edgeLength,
              gravity: 0.08,
              friction: 0.16,
              layoutAnimation: true,
            },
            label: {
              show: true,
              position: 'right',
              color: '#334155',
              fontSize: 12,
            },
            edgeSymbol: ['none', 'arrow'],
            edgeSymbolSize: [3, 9],
            lineStyle: {
              color: 'source',
              width: 1.2,
              opacity: 0.56,
            },
            emphasis: {
              focus: 'adjacency',
              lineStyle: {
                width: 2.4,
                opacity: 0.95,
              },
            },
          },
        ],
      },
      true
    );
  };

  const applyGraphFilter = () => {
    const nodeKeyword = normalizeText(graphFilter.value.nodeKeyword).toLowerCase();
    const edgeKeyword = normalizeText(graphFilter.value.edgeKeyword).toLowerCase();
    const nodeType = graphFilter.value.nodeType;

    const baseNodes = graphNodesRaw.value.filter((n: any) => isNodeTypeMatched(n, nodeType));
    const keywordMatchedNodes = baseNodes.filter((n: any) => {
      if (!nodeKeyword) return true;
      const text = [
        n?.id,
        n?.value,
        n?.key,
        n?.name,
        n?.type,
        normalizeNodeDisplayName(n),
      ]
        .map((item) => normalizeText(item).toLowerCase())
        .join(' ');
      return text.includes(nodeKeyword);
    });

    const nodeIdSet = new Set(keywordMatchedNodes.map((n: any) => String(n?.id || '').trim()));
    const matchedEdges = graphEdgesRaw.value.filter((e: any) => {
      const from = String(e?.from || e?.source || '').trim();
      const to = String(e?.to || e?.target || '').trim();
      if (!nodeIdSet.has(from) || !nodeIdSet.has(to)) return false;
      if (!edgeKeyword) return true;
      const text = [e?.id, e?.value, e?.eventRel, e?.type, from, to]
        .map((item) => normalizeText(item).toLowerCase())
        .join(' ');
      return text.includes(edgeKeyword);
    });

    if (edgeKeyword) {
      const edgeNodeIdSet = new Set<string>();
      matchedEdges.forEach((e: any) => {
        edgeNodeIdSet.add(String(e?.from || e?.source || '').trim());
        edgeNodeIdSet.add(String(e?.to || e?.target || '').trim());
      });
      filteredNodes.value = keywordMatchedNodes.filter((n: any) => edgeNodeIdSet.has(String(n?.id || '').trim()));
    } else {
      filteredNodes.value = keywordMatchedNodes;
    }

    filteredEdges.value = matchedEdges;
    nextTick(() => {
      renderFilteredGraph();
      graphChart?.resize();
    });
  };

  const resetGraphFilter = async () => {
    graphFilter.value.projectIds = [];
    graphFilter.value.nodeKeyword = '';
    graphFilter.value.nodeType = 'all';
    graphFilter.value.edgeKeyword = '';
    clearGraphSource();
  };

  const getAllProjectIdsFromOptions = (): string[] =>
    projectOptions.value.map((item) => String(item.value || '').trim()).filter(Boolean);

  const sanitizeProjectIdsByOptions = (ids: string[]): string[] => {
    const allowed = new Set(getAllProjectIdsFromOptions());
    return Array.from(new Set((ids || []).map((id) => String(id || '').trim()).filter(Boolean))).filter(
      (id) => allowed.has(id)
    );
  };

  const clearGraphSource = () => {
    graphNodesRaw.value = [];
    graphEdgesRaw.value = [];
    filteredNodes.value = [];
    filteredEdges.value = [];
    graphChart?.clear();
    renderedNodeIndexById = new Map<string, number>();
    renderedEdgeIndexById = new Map<string, number>();
  };

  const loadGraphSource = async () => {
    const selectedProjectIds = sanitizeProjectIdsByOptions((graphFilter.value.projectIds || [])
      .map((id) => normalizeText(id))
      .filter(Boolean));

    if (!selectedProjectIds.length) {
      clearGraphSource();
      message.warning('请先选择项目');
      return;
    }

    graphLoading.value = true;
    try {
      const projectResults = await Promise.all(
        selectedProjectIds.map(async (projectId) => {
          const [nodeRes, edgeRes] = await Promise.all([
            getNodesByProject(projectId),
            getEdgesByProject(projectId),
          ]);
          const nodes = nodeRes?.success && nodeRes?.data?.nodes ? nodeRes.data.nodes : [];
          const edges = edgeRes?.success && edgeRes?.data?.edges ? edgeRes.data.edges : [];
          return {
            projectId,
            nodes,
            edges,
          };
        })
      );

      const mergedNodes = new Map<string, any>();
      const mergedEdges = new Map<string, any>();

      for (const result of projectResults) {
        for (const node of result.nodes) {
          const nodeId = String(node?.id || '').trim();
          if (!nodeId) continue;
          if (!mergedNodes.has(nodeId)) {
            mergedNodes.set(nodeId, {
              ...node,
              project_id: result.projectId,
            });
          }
        }
        for (const edge of result.edges) {
          const from = String(edge?.from || edge?.source || '').trim();
          const to = String(edge?.to || edge?.target || '').trim();
          const edgeKey = buildEdgeIdentity(edge);
          if (!from || !to || !edgeKey) continue;
          if (!mergedEdges.has(edgeKey)) {
            mergedEdges.set(edgeKey, {
              ...edge,
              id: edgeKey,
              project_id: result.projectId,
            });
          }
        }
      }

      graphNodesRaw.value = Array.from(mergedNodes.values());
      graphEdgesRaw.value = Array.from(mergedEdges.values());
      applyGraphFilter();
    } catch (err: any) {
      console.error('loadGraphSource error:', err);
      message.error(err?.message || '加载图谱失败');
      graphNodesRaw.value = [];
      graphEdgesRaw.value = [];
      filteredNodes.value = [];
      filteredEdges.value = [];
      graphChart?.clear();
    } finally {
      graphLoading.value = false;
    }
  };

  const aiAvatar = ref<string>(aiAvatarImage);
  const aiAvatarFallback = ref<string>(
    'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgdmlld0JveD0iMCAwIDEwMCAxMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIiByeD0iNTAiIGZpbGw9IiM0NTc2RjEiLz4KPGNpcmNsZSBjeD0iNTAiIGN5PSIzNSIgcj0iMTUiIGZpbGw9IndoaXRlIi8+CjxyZWN0IHg9IjMwIiB5PSI1NSIgd2lkdGg9IjQwIiBoZWlnaHQ9IjMwIiByeD0iOCIgZmlsbD0id2hpdGUiLz4KPGNpcmNsZSBjeD0iNDAiIGN5PSIzNSIgcj0iMyIgZmlsbD0iIzMzMzMzMyIvPgo8Y2lyY2xlIGN4PSI2MCIgY3k9IjM1IiByPSIzIiBmaWxsPSIjMzMzMzMzIi8+Cjwvc3ZnPgo='
  );

  const userAvatar = ref<string>(
    'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop&crop=face&q=80'
  );
  const userAvatarFallback = ref<string>(
    'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgdmlld0JveD0iMCAwIDEwMCAxMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIiByeD0iNTAiIGZpbGw9IiNENUVEQ0VFIi8+CjxjaXJjbGUgY3g9IjUwIiBjeT0iMzUiIHI9IjE1IiBmaWxsPSIjNkM3NzhBIi8+CjxwYXRoIGQ9Ik0yMCA3MEMyMCA1NSA0MCA0MCA1MCA0MEM2MCA0MCA4MCA1NSA4MCA3MEg4MkM4MiA1NCA2MiAzOCA1MCAzOEMzOCAzOCAxOCA1NCAxOCA3MEgyMFoiIGZpbGw9IiM2Qzc3OEEiLz4KPC9zdmc+'
  );

  marked.setOptions({
    breaks: true,
    gfm: true,
  });

  /** 将独占一行的「参考与证据 / 事件图谱 / 网页摘要」提升为标题，便于分区与附录内层级样式 */
  const promoteEvidenceSubsectionsInTail = (tail: string): string => {
    let t = tail.replace(/\r\n/g, '\n');
    t = t.replace(/^(\s*)(事件图谱)\s*$/m, '### $2');
    t = t.replace(/^(\s*)(网页摘要)\s*$/m, '### $2');
    return t;
  };

  const normalizeKgQnaMarkdown = (md: string): string => {
    let s = md.replace(/\r\n/g, '\n');
    if (/^##\s*参考与证据\s*$/m.test(s)) {
      const exec = /^##\s*参考与证据\s*$/m.exec(s);
      if (!exec || exec.index === undefined) return s;
      const cut = exec.index + exec[0].length;
      const head = s.slice(0, cut);
      const tail = promoteEvidenceSubsectionsInTail(s.slice(cut).trimStart());
      return `${head}\n\n${tail}`;
    }
    const loneRef = /^(\*{0,2}\s*)参考与证据(\s*\*{0,2})?\s*$/m;
    const rm = loneRef.exec(s);
    if (rm && rm.index !== undefined) {
      const before = s.slice(0, rm.index).trimEnd();
      const tail = promoteEvidenceSubsectionsInTail(s.slice(rm.index + rm[0].length).trimStart());
      return `${before}\n\n## 参考与证据\n\n${tail}`;
    }
    return s;
  };

  /** 独占一行的 http(s) 段落转为链接，便于点击（与附录双行「标题 + URL」形态一致） */
  const linkifyBareUrlParagraphs = (html: string): string =>
    html.replace(
      /<p>(https?:\/\/[^\s<]+)<\/p>/gi,
      '<p class="kg-bare-url-line"><a href="$1">$1</a></p>'
    );

  /** 若模型未写 ## 而输出成普通段落，则补成 h2，保证与正文分区 */
  const ensureReferenceH2 = (html: string): string => {
    if (/<h2[^>]*>\s*参考与证据\s*<\/h2>/i.test(html)) return html;
    return html.replace(
      /<p>\s*(?:<strong>)?参考与证据(?:<\/strong>)?\s*<\/p>/i,
      '<h2>参考与证据</h2>'
    );
  };

  const ANSWER_SECTION_LABELS = new Set([
    '结果',
    '核心结论',
    '结论',
    '关键结论',
    '总结',
    '简要结论',
    '要点',
    '关键要点',
    '分析',
    '影响分析',
    '原因分析',
    '操作建议',
    '建议',
    '风险提示',
    '风险',
    '依据',
    '说明',
    '解读',
    '观察',
    '后续关注',
    '关注点',
    '下一步',
  ]);

  const ANSWER_SECTION_SUFFIX_RE =
    /(?:结果|结论|分析|建议|要点|总结|提示|依据|说明|解读|观察|影响|关注点|下一步)$/;

  const normalizeAnswerSectionLabel = (text: string): string =>
    String(text || '')
      .replace(/<[^>]+>/g, ' ')
      .replace(/[*#`>\-]/g, ' ')
      .replace(/[\u{1F300}-\u{1FAFF}\u2600-\u27BF]/gu, ' ')
      .replace(/[：:]/g, '')
      .replace(/\s+/g, ' ')
      .trim();

  /** 在正文区把独占一行的短标签抬成小标题，例如“结果”“核心结论”。 */
  const promoteAnswerSubheadings = (html: string): string => {
    const mk = /<h2[^>]*>\s*参考与证据\s*<\/h2>/i.exec(html);
    const split = mk && mk.index !== undefined ? mk.index : html.length;
    const head = html.slice(0, split);
    const tail = html.slice(split);

    const promoted = head.replace(/<p>\s*([\s\S]*?)\s*<\/p>/gi, (full: string, inner: string) => {
      const plain = normalizeAnswerSectionLabel(inner);
      if (!plain) return full;
      if (plain.length > 14) return full;
      if (/[，。；！？,.!?]/.test(plain)) return full;
      const matched = ANSWER_SECTION_LABELS.has(plain) || ANSWER_SECTION_SUFFIX_RE.test(plain);
      if (!matched) return full;
      return `<h3 class="kg-answer-section-label">${inner.trim()}</h3>`;
    });

    return promoted + tail;
  };

  /** 仅在「参考与证据」标题之后，把附录内的纯文本小节抬成 h3（避免污染正文偶发段落） */
  const ensureSubheadingsAfterReference = (html: string): string => {
    const mk = /<h2[^>]*>\s*参考与证据\s*<\/h2>/i.exec(html);
    if (!mk || mk.index === undefined) return html;
    const split = mk.index + mk[0].length;
    const head = html.slice(0, split);
    let tail = html.slice(split);
    tail = tail.replace(/<p>\s*事件图谱\s*<\/p>/i, '<h3 class="kg-ev-section-label">事件图谱</h3>');
    tail = tail.replace(/<p>\s*网页摘要\s*<\/p>/i, '<h3 class="kg-ev-section-label">网页摘要</h3>');
    return head + tail;
  };

  /** 将模型输出的图谱证据引用转为可样式化的 HTML 气泡（在 marked 之后执行） */
  const decorateKgEvidenceHtml = (html: string): string => {
    let s = html;
    s = s.replace(
      /「证据(\d+)·([^」]+)」/g,
      '<span class="kg-evidence-chip">证据 $1 · $2</span>'
    );
    s = s.replace(/\[证据(\d+)\]\s*project_id=\d+/g, '<span class="kg-evidence-chip">证据 $1</span>');
    s = s.replace(
      /\[证据(\d+)\]\s*project_name=([^<\s\]]+)/g,
      '<span class="kg-evidence-chip">证据 $1 · $2</span>'
    );
    s = s.replace(/<p>证据(\d+)\s*[—\-–]/g, '<p><span class="kg-evidence-chip">证据 $1</span> —');
    return s;
  };

  const escapeHtml = (text: string): string =>
    String(text || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');

  /** 把「标题/链接/摘要」型网页证据段落转成推荐卡片 */
  const decorateWebEvidenceCards = (html: string): string => {
    const buildWebCard = (title: string, url: string, summary = '', chip = ''): string => {
      const titleSafe = escapeHtml(title || '相关网页');
      const summarySafe = escapeHtml(summary || '');
      const urlSafe = escapeHtml(url || '');
      return [
        '<div class="kg-web-card">',
        '<div class="kg-web-card__head">',
        chip,
        '<span class="kg-web-card__tag">网页摘要</span>',
        '</div>',
        `<div class="kg-web-card__title">${titleSafe}</div>`,
        summarySafe ? `<p class="kg-web-card__summary">${summarySafe}</p>` : '',
        `<a class="kg-web-card__cta" href="${urlSafe}" target="_blank" rel="noopener noreferrer">查看原文</a>`,
        `<div class="kg-web-card__url">${urlSafe}</div>`,
        '</div>',
      ].join('');
    };

    let s = html;

    // 容错：把「网页摘要 / 相关网页 / 标题+URL / 查看原文 / URL」散行结构整体折叠成卡片
    // 支持段落内已被 marked 自动转成 <a href> 的 URL，避免漏掉单条未卡片化情况。
    s = s.replace(
      /(?:<p>\s*网页摘要\s*<\/p>\s*)?(?:<p>\s*相关网页\s*<\/p>\s*)?<p>\s*([\s\S]*?)\s*<\/p>\s*<p>\s*查看原文\s*<\/p>\s*<p>\s*([\s\S]*?)\s*<\/p>\s*(?:<p>\s*([a-z0-9.-]+\.[a-z]{2,})\s*<\/p>)?/gi,
      (_full: string, titleLineRaw: string, ctaLineRaw: string) => {
        const hrefInTitle = String(titleLineRaw || '').match(/href\s*=\s*["'](https?:\/\/[^"']+)["']/i);
        const hrefInCta = String(ctaLineRaw || '').match(/href\s*=\s*["'](https?:\/\/[^"']+)["']/i);
        const titlePlain = String(titleLineRaw || '')
          .replace(/<br\s*\/?>/gi, '\n')
          .replace(/<[^>]+>/g, ' ')
          .replace(/\s+/g, ' ')
          .trim();
        const ctaPlain = String(ctaLineRaw || '')
          .replace(/<br\s*\/?>/gi, '\n')
          .replace(/<[^>]+>/g, ' ')
          .replace(/\s+/g, ' ')
          .trim();

        const urlInTitle = titlePlain.match(/https?:\/\/[^\s]+/i);
        const urlInCta = ctaPlain.match(/https?:\/\/[^\s]+/i);
        const url = String(
          (hrefInCta && hrefInCta[1]) ||
            (urlInCta && urlInCta[0]) ||
            (hrefInTitle && hrefInTitle[1]) ||
            (urlInTitle && urlInTitle[0]) ||
            ''
        ).trim();
        if (!url) return _full;
        const title = titlePlain.replace(url, '').trim() || '相关网页';
        return buildWebCard(title, url);
      }
    );

    // 容错：把「网页摘要 / 标题 / 摘要 / 查看原文 / URL」散行结构整体折叠成卡片
    s = s.replace(
      /(?:<p>\s*网页摘要\s*<\/p>\s*)?<p>\s*([^<]+?)\s*<\/p>\s*<p>\s*([\s\S]*?)\s*<\/p>\s*<p>\s*查看原文\s*<\/p>\s*<p>\s*(https?:\/\/[^\s<]+)\s*<\/p>\s*(?:<p>\s*([a-z0-9.-]+\.[a-z]{2,})\s*<\/p>)?/gi,
      (_full: string, titlePart: string, summaryPart: string, ctaUrl: string) => {
        const url = String(ctaUrl || '').trim();
        const title = String(titlePart || '').replace(/\s+/g, ' ').trim() || '相关网页';
        const summary = String(summaryPart || '').replace(/\s+/g, ' ').trim();
        if (!url) return _full;
        return buildWebCard(title, url, summary);
      }
    );

    s = s.replace(/<(p|li)>([\s\S]*?)<\/(p|li)>/gi, (full: string, _tag: string, inner: string) => {
      const hasStructuredKey = /(标题|摘要|链接|网址|来源|URL)\s*[:：]/i.test(inner);
      if (!hasStructuredKey) return full;

      const chipMatch = inner.match(/(<span class="kg-evidence-chip">[\s\S]*?<\/span>)/i);
      const chip = chipMatch ? chipMatch[1] : '';
      const plain = inner
        .replace(/<br\s*\/?>/gi, '\n')
        .replace(/<[^>]+>/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();

      const hrefMatch = inner.match(/href\s*=\s*["'](https?:\/\/[^"']+)["']/i);
      const linkMatch = plain.match(/https?:\/\/[^\s]+/i);
      const url = String((hrefMatch && hrefMatch[1]) || (linkMatch && linkMatch[0]) || '').trim();
      if (!url) return full;

      const extractField = (keys: string[]): string => {
        for (const key of keys) {
          const reg = new RegExp(
            `${key}\\s*[:：]\\s*([\\s\\S]*?)(?=(?:标题|摘要|链接|网址|来源|URL)\\s*[:：]|$)`,
            'i'
          );
          const m = plain.match(reg);
          if (m && m[1]) {
            const v = String(m[1]).trim();
            if (v) return v;
          }
        }
        return '';
      };

      let title = extractField(['标题']);
      let summary = extractField(['摘要']);

      if (!summary && title) {
        // 兼容有的模型把摘要写在「来源/链接」之后
        const afterLink = extractField(['链接', '网址', '来源', 'URL']);
        if (afterLink && !/^https?:\/\//i.test(afterLink)) summary = afterLink;
      }

      if (!title) {
        title = '相关网页';
      }

      return buildWebCard(title, url, summary, chip);
    });

    // 最终兜底：凡是出现「网页摘要」锚点，且后续块内存在 URL，就强制折叠成卡片。
    s = s.replace(
      /<p>\s*网页摘要\s*<\/p>\s*((?:(?:<(?:p|li)>)[\s\S]*?<\/(?:p|li)>\s*){1,8})/gi,
      (full: string, tailBlock: string) => {
        const lines = Array.from(tailBlock.matchAll(/<(?:p|li)>\s*([\s\S]*?)\s*<\/(?:p|li)>/gi))
          .map((m) => String(m[1] || ''))
          .map((raw) => ({
            raw,
            plain: raw
              .replace(/<br\s*\/?>/gi, '\n')
              .replace(/<[^>]+>/g, ' ')
              .replace(/\s+/g, ' ')
              .trim(),
          }))
          .filter((x) => x.plain.length > 0);

        if (!lines.length) return full;

        const extractUrl = (raw: string, plain: string): string => {
          const href = raw.match(/href\s*=\s*["'](https?:\/\/[^"']+)["']/i);
          if (href && href[1]) return String(href[1]).trim();
          const txt = plain.match(/https?:\/\/[^\s]+/i);
          return txt && txt[0] ? String(txt[0]).trim() : '';
        };

        let url = '';
        for (let i = 0; i < lines.length; i += 1) {
          const cur = lines[i];
          if (/^查看原文\s*$/i.test(cur.plain) && i + 1 < lines.length) {
            url = extractUrl(lines[i + 1].raw, lines[i + 1].plain);
            if (url) break;
          }
        }
        if (!url) {
          for (const line of lines) {
            url = extractUrl(line.raw, line.plain);
            if (url) break;
          }
        }
        if (!url) return full;

        const isMetaLine = (t: string): boolean => {
          if (!t) return true;
          if (t === '网页摘要' || t === '相关网页' || t === '查看原文') return true;
          if (/^[a-z0-9.-]+\.[a-z]{2,}$/i.test(t)) return true;
          if (/^https?:\/\//i.test(t)) return true;
          return false;
        };

        let title = '';
        let summary = '';
        for (const line of lines) {
          const cleaned = line.plain.replace(url, '').replace(/\s+/g, ' ').trim();
          if (isMetaLine(cleaned)) continue;
          if (!title) {
            title = cleaned;
            continue;
          }
          if (!summary) {
            summary = cleaned;
            break;
          }
        }

        return buildWebCard(title || '相关网页', url, summary);
      }
    );

    return s;
  };

  /** 兼容旧模型仍输出「## 回答」时的 HTML */
  const stripLegacyAnswerHeading = (html: string): string =>
    html.replace(/^\s*<h2[^>]*>\s*回答\s*<\/h2>\s*/i, '');

  /** 正文与「参考与证据」分区，便于分区样式 */
  const wrapKgQnaSections = (html: string): string => {
    const trimmed = html.trim();
    if (!trimmed) return '';
    const re = /<h2\b/i;
    const match = re.exec(trimmed);
    if (!match) {
      return `<div class="kg-qna-answer">${trimmed}</div>`;
    }
    const idx = match.index;
    const answer = trimmed.slice(0, idx).trim();
    const evidence = trimmed.slice(idx);
    const answerBlock = answer ? `<div class="kg-qna-answer">${answer}</div>` : '';
    return `${answerBlock}<div class="kg-qna-evidence">${evidence}</div>`;
  };

  /** 外链默认新标签打开（事件图谱问答中的 http(s) 引用） */
  const addExternalLinkAttributes = (html: string): string =>
    html.replace(/<a\s+([^>]+)>/gi, (full: string, inner: string) => {
      if (!/href\s*=\s*["']https?:/i.test(inner)) return full;
      if (/\btarget\s*=/i.test(inner)) return full;
      return `<a target="_blank" rel="noopener noreferrer" ${inner.trim()}>`;
    });

  const renderMarkdown = (content: string) => {
    if (!content) return '';
    let normalized = content.replace(/\n{3,}/g, '\n\n');
    normalized = normalizeKgQnaMarkdown(normalized);
    let parsed =
      typeof (marked as unknown as { parse?: (s: string) => string }).parse === 'function'
        ? (marked as unknown as { parse: (s: string) => string }).parse(normalized)
        : (marked as unknown as (s: string) => string)(normalized);
    let s = String(parsed);
    s = stripLegacyAnswerHeading(s);
    s = linkifyBareUrlParagraphs(s);
    s = ensureReferenceH2(s);
    s = promoteAnswerSubheadings(s);
    s = ensureSubheadingsAfterReference(s);
    s = decorateKgEvidenceHtml(s);
    s = decorateWebEvidenceCards(s);
    s = wrapKgQnaSections(s);
    s = addExternalLinkAttributes(s);
    return s;
  };

  const purifyMarkdown = (markdown: string): string => {
    return DOMPurify.sanitize(markdown, {
      ADD_TAGS: ['span', 'div'],
      ADD_ATTR: ['class', 'target', 'rel'],
    });
  };

  const WELCOME_TEXT =
    '您好，我是智能分析助手。您可以直接提问；我会在您可见的全部项目中检索图谱证据并作答，必要时给出通用说明。开启「联网补强」后，在证据偏弱时将按各项目已选公告样本锚定补充网页摘要（无需手动选项目）。可切换「深度思考」与详略。';

  /** 侧栏「历史对话」列表刷新（与 AsideMenu 约定事件名） */
  const CHAT_HISTORY_REFRESH_EVENT = 'finkg-chat-history-refresh';
  /** 侧栏「新建对话」清空页面状态（与 AsideMenu 约定） */
  const CHAT_RESET_EVENT = 'finkg-chat-reset-to-new';

  const generateSessionId = (): string => {
    return `session_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
  };

  const restoreWebSearchPrefs = () => {
    try {
      const raw = sessionStorage.getItem(WEB_SEARCH_STORAGE_KEY);
      if (!raw) return;
      const o = JSON.parse(raw) as { enable?: boolean };
      if (typeof o.enable === 'boolean') enableWebSearch.value = o.enable;
    } catch {
      /* ignore */
    }
  };

  watch(enableWebSearch, () => {
    try {
      sessionStorage.setItem(
        WEB_SEARCH_STORAGE_KEY,
        JSON.stringify({
          enable: enableWebSearch.value,
        })
      );
    } catch {
      /* ignore */
    }
  });

  const hasDiagnosticData = (payload: {
    quality_hints?: unknown;
    web_search_meta?: unknown;
    retrieval_debug?: unknown;
  } | null | undefined): boolean => {
    if (!payload || typeof payload !== 'object') return false;
    return [payload.quality_hints, payload.web_search_meta, payload.retrieval_debug].some((v) => {
      if (v === undefined || v === null) return false;
      if (typeof v === 'string') return v.trim().length > 0;
      if (Array.isArray(v)) return v.length > 0;
      if (typeof v === 'object') return Object.keys(v as Record<string, unknown>).length > 0;
      return true;
    });
  };

  const formatDiagnosticJson = (payload: unknown): string => {
    if (payload === undefined || payload === null || String(payload).trim() === '') {
      return '暂无数据';
    }
    if (typeof payload === 'string') return payload;
    try {
      return JSON.stringify(payload, null, 2);
    } catch {
      return String(payload);
    }
  };

  const openDiagnosticDrawer = (payload: {
    quality_hints?: unknown;
    web_search_meta?: unknown;
    retrieval_debug?: unknown;
  } | null | undefined) => {
    if (!canOpenDiagnosticDrawer.value || !hasDiagnosticData(payload)) return;
    activeDiagnosticPayload.value = {
      quality_hints: payload?.quality_hints,
      web_search_meta: payload?.web_search_meta,
      retrieval_debug: payload?.retrieval_debug,
    };
    diagnosticDrawerVisible.value = true;
  };

  const handleSendMessage = async () => {
    if (!userInput.value.trim() || isLoading.value) return;

    if (!currentSessionId.value) {
      currentSessionId.value = generateSessionId();
    }

    messages.value.push({
      type: 'user-message',
      content: userInput.value,
    });

    const currentInput = userInput.value;
    userInput.value = '';
    isLoading.value = true;

    messages.value.push({
      type: 'ai-message',
      content: '',
      streaming: true,
      ...(deepThink.value
        ? {
            deepThink: true,
            reasoning: '',
            reasoningCollapsed: false,
          }
        : {}),
    });
    const aiMsgIndex = messages.value.length - 1;

    try {
      const uid = userStore.getUserId || userStore.getUsername || userStore.getName || '';
      const kgPayload: KgQaParams = {
        user_id: uid,
        username: userStore.getUsername || userStore.getName || '',
        uid: userStore.getUserId || userStore.getUsername || '',
        is_admin: false,
        query: currentInput,
        session_id: currentSessionId.value,
        use_session_history: true,
        save_history: true,
        intent_mode: 'auto',
        allow_general_fallback: true,
        deep_think: deepThink.value,
        top_k_per_project: 0,
      };
      kgPayload.enable_web_search = enableWebSearch.value;
      kgPayload.web_search_mode = enableWebSearch.value ? 'always' : 'never';
      if (canOpenDiagnosticDrawer.value) {
        kgPayload.debug_retrieval = true;
      }
      const response = await getKgQaReplyStream(
        userStore.getToken,
        kgPayload,
        (chunk: string) => {
          const row = messages.value[aiMsgIndex];
          if (row) {
            row.content += chunk;
            scrollToBottom();
          }
        },
        deepThink.value
          ? (chunk: string) => {
              const row = messages.value[aiMsgIndex];
              if (row) {
                row.reasoning = (row.reasoning || '') + chunk;
                row.reasoningCollapsed = false;
                scrollToBottom();
              }
            }
          : undefined
      );
      if (response.code === 0) {
        if (response?.data?.session_id) {
          currentSessionId.value = String(response.data.session_id);
        }
        const row = messages.value[aiMsgIndex];
        if (row && !String(row.content || '').trim()) {
          row.content = formatKgQaReply(response.data);
        }
        if (row?.deepThink && response?.data?.reasoning != null) {
          row.reasoning = String(response.data.reasoning);
        }
        if (row && row.type === 'ai-message') {
          const cards = parseWebEvidenceCardsFromPayload(response.data);
          row.webEvidenceCards = cards;
          if (cards.length > 0) {
            row.content = stripWebSummarySectionFromMarkdown(String(row.content || ''));
          }
        }
        if (row && row.type === 'ai-message') {
          row.sourceFootnote = buildReplySourceFootnote(
            response.data,
            enableWebSearch.value
          );
          row.diagnosticPayload = {
            quality_hints: response?.data?.quality_hints,
            web_search_meta: response?.data?.web_search_meta,
            retrieval_debug: response?.data?.retrieval_debug,
          };
        }

        const evidenceProjectIds = sanitizeProjectIdsByOptions(
          pickEvidenceProjectIds(response.data, String(row?.content || ''))
        ).sort();
        graphFilter.value.projectIds = evidenceProjectIds;
        graphFilter.value.nodeKeyword = '';
        graphFilter.value.edgeKeyword = '';
        graphFilter.value.nodeType = 'all';
        if (evidenceProjectIds.length) {
          await loadGraphSource();
        } else {
          clearGraphSource();
        }

        window.dispatchEvent(new CustomEvent(CHAT_HISTORY_REFRESH_EVENT));
      } else {
        throw new Error(response.msg || '请求失败');
      }
    } catch (error) {
      console.error('API调用失败:', error);
      message.error('请求失败，请稍后重试');
      const row = messages.value[aiMsgIndex];
      if (row && row.type === 'ai-message' && !String(row.content || '').trim()) {
        row.content = '抱歉，服务暂时不可用，请稍后重试。';
      } else if (!messages.value[aiMsgIndex]) {
        messages.value.push({
          type: 'ai-message',
          content: '抱歉，服务暂时不可用，请稍后重试。',
        });
      }
    } finally {
      const doneRow = messages.value[aiMsgIndex];
      if (doneRow && doneRow.type === 'ai-message') {
        doneRow.streaming = false;
        if (
          doneRow.deepThink &&
          String(doneRow.reasoning || '').trim()
        ) {
          doneRow.reasoningCollapsed = true;
        }
      }
      isLoading.value = false;
      scrollToBottom();
    }
  };

  const toggleReasoning = (index: number) => {
    const row = messages.value[index];
    if (row?.type === 'ai-message' && row.deepThink) {
      row.reasoningCollapsed = !row.reasoningCollapsed;
    }
  };

  const formatKgQaReply = (data: any) => {
    if (!data) return '抱歉，未返回有效结果。';
    return String(data.answer || '').trim() || '抱歉，未返回有效结果。';
  };

  function stripWebSummarySectionFromMarkdown(content: string): string {
    let s = String(content || '').replace(/\r\n/g, '\n');
    if (!s.trim()) return s;
    s = s.replace(/^##\s*二[、.．]\s*公开市场信息的补充[\s\S]*?(?=^##\s+|\Z)/gim, '');
    s = s.replace(/^###\s*网页摘要[\s\S]*?(?=^###\s+|^##\s+|\Z)/gim, '');
    s = s.replace(/^\s*网页摘要\s*$/gim, '');
    s = s.replace(/^\s*查看原文\s*$/gim, '');
    s = s.replace(/^\s*https?:\/\/\S+\s*$/gim, '');
    return s.replace(/\n{3,}/g, '\n\n').trim();
  }

  function parseWebEvidenceCardsFromPayload(
    data: any
  ): Array<{ title: string; url: string; summary: string; chip?: string; projectId?: string }> {
    const getWebSourceChip = (rawUrl: string): string => {
      try {
        const host = new URL(rawUrl).hostname.trim().toLowerCase();
        if (!host) return '网页来源';
        return host.replace(/^www\./, '');
      } catch {
        return '网页来源';
      }
    };

    const evidence = Array.isArray(data?.evidence) ? data.evidence : [];
    const rows = evidence.filter((e: any) => {
      if (!e || typeof e !== 'object') return false;
      return e.source === 'constrained_web' || String(e.snippet || '').includes('[联网检索');
    });

    const cards: Array<{ title: string; url: string; summary: string; chip?: string; projectId?: string }> = [];
    const seen = new Set<string>();

    for (const e of rows) {
      const snippet = String(e?.snippet || '');
      let title = String(e?.page_title || '').trim();
      let url = String(e?.url || '').trim();
      const projectId = String(e?.project_id || '').trim();
      let summary = '';

      if (!title) {
        const mt = snippet.match(/标题\s*[:：]\s*([^\n]+)/);
        if (mt) title = String(mt[1] || '').trim();
      }
      if (!url) {
        const mu = snippet.match(/https?:\/\/[^\s\n]+/i);
        if (mu) url = String(mu[0] || '').trim();
      }
      const ms = snippet.match(/摘要\s*[:：]\s*([\s\S]*?)(?:\n────────\n|$)/);
      if (ms) {
        summary = String(ms[1] || '').replace(/\s+/g, ' ').trim();
      }

      if (!summary) {
        const snippetLines = snippet
          .split('\n')
          .map((line) => String(line || '').trim())
          .filter((line) => line && !/^标题\s*[:：]/.test(line) && !/^链接\s*[:：]/.test(line));
        summary = snippetLines.slice(0, 4).join(' ').trim();
      }

      const cardKey = `${projectId || '-'}|${url}`;
      if (!url || seen.has(cardKey)) continue;
      seen.add(cardKey);
      cards.push({
        title: title || '相关网页',
        url,
        summary,
        chip: getWebSourceChip(url),
        projectId,
      });
    }
    return cards;
  }

  const cardInjectKey = (card: { url: string; projectId?: string }): string =>
    `${String(card.projectId || '').trim()}|${String(card.url || '').trim()}`;

  const buildInjectContent = (card: {
    title: string;
    summary: string;
    url: string;
  }): string => {
    const title = String(card.title || '').trim();
    const summary = String(card.summary || '').trim();
    const url = String(card.url || '').trim();
    return [
      title ? `标题：${title}` : '',
      summary ? `摘要：${summary}` : '',
      url ? `来源链接：${url}` : '',
    ]
      .filter(Boolean)
      .join('\n');
  };

  const handleInjectWebCard = (card: {
    title: string;
    summary: string;
    url: string;
    chip?: string;
    projectId?: string;
  }) => {
    const projectId = String(card.projectId || '').trim();
    if (!projectId) {
      message.warning('该网页证据未关联到项目，暂时无法加入图谱');
      return;
    }

    const content = buildInjectContent(card);
    const title = String(card.title || '联网补强事件').trim() || '联网补强事件';
    dialog.warning({
      title: '确认加入现有图谱',
      content: `将把该网页摘要注入项目 ${projectId} 并触发增量图谱构建，是否继续？`,
      positiveText: '确认加入',
      negativeText: '取消',
      onPositiveClick: async () => {
        const key = cardInjectKey(card);
        const beforeNodeIds = new Set(
          graphNodesRaw.value
            .filter((node: any) => String(node?.project_id || '').trim() === projectId)
            .map((node: any) => String(node?.id || '').trim())
            .filter(Boolean)
        );
        const beforeEdgeIds = new Set(
          graphEdgesRaw.value
            .filter((edge: any) => String(edge?.project_id || '').trim() === projectId)
            .map((edge: any) => buildEdgeIdentity(edge))
            .filter(Boolean)
        );
        injectingWebCardKey.value = key;
        try {
          const injectRes: any = await injectMockEvent({
            project_id: projectId,
            title,
            content,
            url: card.url,
            source: card.chip || '联网网页摘要',
          });
          if (injectRes && injectRes.success === false) {
            throw new Error(injectRes.message || '加入图谱失败');
          }
          const preferredNodeIds = Array.isArray(injectRes?.new_node_ids)
            ? injectRes.new_node_ids
            : Array.isArray(injectRes?.data?.new_node_ids)
              ? injectRes.data.new_node_ids
              : [];
          const preferredEdgeIds = Array.isArray(injectRes?.new_edge_ids)
            ? injectRes.new_edge_ids
            : Array.isArray(injectRes?.data?.new_edge_ids)
              ? injectRes.data.new_edge_ids
              : [];
          const delta = await focusInjectedGraphChanges(
            projectId,
            beforeNodeIds,
            beforeEdgeIds,
            preferredNodeIds,
            preferredEdgeIds
          );
          if (delta) {
            message.success(
              `已定位并高亮新增图谱元素：节点 ${delta.newNodeIds.length} 个，关系 ${delta.newEdgeIds.length} 条。`
            );
          } else {
            message.success('已提交增量构建请求，图谱更新可能稍有延迟，请稍后点击“加载图谱”查看。');
          }
        } catch (err: any) {
          console.error('inject web card failed:', err);
          message.error(err?.message || '加入图谱失败，请稍后重试');
        } finally {
          if (injectingWebCardKey.value === key) {
            injectingWebCardKey.value = '';
          }
        }
      },
    });
  };

  /** 根据后端返回的意图、证据与联网元数据生成助手气泡底部小号说明 */
  function webSearchResultCount(meta: unknown): number {
    if (!meta || typeof meta !== 'object') return 0;
    const m = meta as Record<string, unknown>;
    const rc = m.result_count;
    if (typeof rc === 'number' && Number.isFinite(rc)) return rc;
    if (typeof rc === 'string') {
      const n = Number(rc);
      return Number.isFinite(n) ? n : 0;
    }
    return 0;
  }

  /**
   * 联网已执行但未合并摘要时，根据后端 web_search_meta 给出可读原因（与 constrained_web_search 对齐）。
   */
  function webSearchMissHint(meta: unknown): string {
    if (!meta || typeof meta !== 'object') return '';
    const m = meta as Record<string, unknown>;
    if (m.error === 'ddgs_not_installed' || m.error === 'duckduckgo_search_not_installed') {
      return ' 原因：服务端未安装联网依赖 ddgs。';
    }
    if (m.error === 'ddgs_all_backends_failed') {
      return ' 原因：DuckDuckGo/Bing 多线路均未返回结果（请检查网络、代理或稍后重试；服务端需可访问 html.duckduckgo.com）。';
    }
    if (m.error === 'ddgs_connect_refused') {
      return ' 原因：服务端到外网搜索引擎的连接被拒绝（WinError 10061），请检查代理端口与网络策略。';
    }
    if (typeof m.error === 'string' && m.error.trim()) {
      const t = m.error.length > 90 ? `${m.error.slice(0, 90)}…` : m.error;
      return ` 原因：${t}`;
    }
    const wf = m.web_failure_hint;
    if (wf === 'ddgs_empty') {
      return ' 原因：检索端未返回任何条目（请检查网络、代理或稍后重试）。';
    }
    if (wf === 'semantic_rerank_empty') {
      return ' 原因：检索端返回了候选网页，但二阶段重排后仍未选出可用摘要；可稍后重试或放宽问题范围。';
    }
    const pp = m.per_project;
    if (Array.isArray(pp) && pp.length > 0) {
      const rows = pp.filter((x) => x && typeof x === 'object') as Record<string, unknown>[];
      const projErrors = rows
        .map((r) => r.error)
        .filter((e): e is string => typeof e === 'string' && e.trim().length > 0);
      if (projErrors.length > 0) {
        if (projErrors.every((e) => e === 'ddgs_not_installed')) {
          return ' 原因：服务端未安装联网依赖 ddgs。';
        }
        if (projErrors.every((e) => e === 'ddgs_all_backends_failed')) {
          return ' 原因：DuckDuckGo/Bing 多线路均失败（请检查服务端网络/代理，确认可访问 html.duckduckgo.com）。';
        }
        if (projErrors.every((e) => e === 'ddgs_connect_refused')) {
          return ' 原因：服务端到外网搜索引擎连接被拒绝（WinError 10061），请检查代理端口与网络策略。';
        }
      }
      if (rows.some((r) => r.reason === 'empty_query_parts')) {
        return ' 原因：问题中的关键词未出现在已选公告样本里，无法生成锚定检索词。';
      }
      if (rows.length > 0 && rows.every((r) => r.reason === 'no_samples')) {
        return ' 原因：可见项目均未选取公告样本（无法锚定检索）。';
      }
      if (rows.some((r) => r.reason === 'no_samples')) {
        return ' 原因：部分项目未选取公告样本，锚定语料不足。';
      }
      const projHints = rows
        .map((r) => r.web_failure_hint)
        .filter((h): h is string => typeof h === 'string' && h.trim().length > 0);
      if (projHints.length > 0) {
        if (projHints.every((h) => h === 'ddgs_empty')) {
          return ' 原因：各项目检索端均未返回条目（网络或 DuckDuckGo 不可用）。';
        }
        if (projHints.every((h) => h === 'semantic_rerank_empty')) {
          return ' 原因：各项目均拿到了候选网页，但二阶段重排后没有选出可用摘要。';
        }
      }
    }
    return ' 原因：外部检索未返回条目或网络异常。';
  }

  function evidenceHasWeb(evidence: unknown[]): boolean {
    return evidence.some((e: any) => {
      if (!e || typeof e !== 'object') return false;
      return (
        e.source === 'constrained_web' ||
        String(e.snippet || '').includes('[联网检索·样本锚定]')
      );
    });
  }

  function historySnapshotRunIds(evidence: unknown[]): string[] {
    const ids: string[] = [];
    const seen = new Set<string>();
    for (const e of evidence as any[]) {
      if (!e || typeof e !== 'object') continue;
      if (String(e.source || '').trim() !== 'history_snapshot_match') continue;
      const rid = String(e.run_id || '').trim();
      if (!rid || seen.has(rid)) continue;
      seen.add(rid);
      ids.push(rid);
      if (ids.length >= 3) break;
    }
    return ids;
  }

  function buildReplySourceFootnote(data: any, requestWebSearch: boolean): string {
    if (!data || typeof data !== 'object') return '';
    const kgLookup = String(data.kg_lookup_status || '').trim();
    const coarse = String(data.intent_coarse || '');
    const intent = String(data.intent || '');
    const evidence = Array.isArray(data.evidence) ? data.evidence : [];
    const histRunIds = historySnapshotRunIds(evidence);
    const nWeb = webSearchResultCount(data.web_search_meta);
    const webFromEv = evidenceHasWeb(evidence);
    const mergedWebCountRaw =
      data?.web_search_meta && typeof data.web_search_meta === 'object'
        ? (data.web_search_meta as Record<string, unknown>).merged_into_final ??
          (data.web_search_meta as Record<string, unknown>).merged_result_count
        : 0;
    const mergedWebCount = Number(mergedWebCountRaw);
    const hasWebMerged = (Number.isFinite(mergedWebCount) && mergedWebCount > 0) || webFromEv;
    const attempted = Boolean(data.web_search_attempted);

    if (kgLookup === 'miss') {
      if (coarse === 'platform') {
        return '来源说明：已在全部项目中检索事件图谱，未找到与问题相关的证据；以下为平台操作引导。';
      }
      return '来源说明：已在全部项目中检索事件图谱，未找到与问题相关的证据，已转为通用知识回答。';
    }
    if (kgLookup === 'no_projects') {
      if (coarse === 'platform') {
        return '来源说明：当前无可检索的图谱项目；以下为平台操作引导。';
      }
      return '来源说明：当前账号下无可检索的图谱项目，回答来自通用知识。';
    }

    if (intent === 'kg_fallback_general') {
      return '来源说明：图谱侧证据不足或未命中项目，已自动回退为通用知识回答。';
    }
    if (coarse === 'general' || intent === 'general') {
      return '来源说明：通用知识回答（未使用您构建的事件图谱证据）。';
    }
    if (coarse === 'platform') {
      return '来源说明：平台能力与流程说明（未检索私有事件图谱）。';
    }

    const noEvidence = evidence.length === 0;
    if (noEvidence) {
      let s =
        '来源说明：按事件图谱问答流程作答；本轮在您可见项目中未检索到图谱证据。';
      if (requestWebSearch && attempted && !hasWebMerged) {
        s += ` 已尝试联网补强，本次未合并网页摘要。${webSearchMissHint(data.web_search_meta)}`;
      }
      return s;
    }

    if (hasWebMerged) {
      const histHint =
        histRunIds.length > 0
          ? ` 其中部分证据来自历史构建图谱(run_id=${histRunIds.join(', ')})。`
          : '';
      return `来源说明：依据您可见项目的事件图谱检索，并合并了样本锚定的公开网页摘要（非公告原文）。${histHint}`;
    }
    if (requestWebSearch && attempted && !hasWebMerged) {
      const histHint =
        histRunIds.length > 0
          ? ` 其中部分证据来自历史构建图谱(run_id=${histRunIds.join(', ')})。`
          : '';
      return `来源说明：依据您可见项目的事件图谱检索；已开启联网补强，本次未合并网页摘要。${webSearchMissHint(data.web_search_meta)}${histHint}`;
    }
    if (requestWebSearch && !attempted && !hasWebMerged) {
      const histHint =
        histRunIds.length > 0
          ? ` 其中部分证据来自历史构建图谱(run_id=${histRunIds.join(', ')})。`
          : '';
      return `来源说明：依据您可见项目的事件图谱检索（本轮未执行联网补强）。${histHint}`;
    }
    if (!requestWebSearch) {
      const histHint =
        histRunIds.length > 0
          ? ` 其中部分证据来自历史构建图谱(run_id=${histRunIds.join(', ')})。`
          : '';
      return `来源说明：依据您可见项目中构建的事件图谱检索。${histHint}`;
    }
    const histHint =
      histRunIds.length > 0
        ? ` 其中部分证据来自历史构建图谱(run_id=${histRunIds.join(', ')})。`
        : '';
    return `来源说明：依据您可见项目中构建的事件图谱检索（本次未合并公开网页摘要）。${histHint}`;
  }

  function pickEvidenceProjectIds(data: any, renderedContent = ''): string[] {
    if (!data || typeof data !== 'object') return [];
    const kgLookup = String(data.kg_lookup_status || '').trim();
    const coarse = String(data.intent_coarse || '').trim();
    const intent = String(data.intent || '').trim();
    if (kgLookup === 'miss' || kgLookup === 'no_projects') return [];
    if (coarse === 'general' || coarse === 'platform' || intent === 'general') return [];

    const evidence = Array.isArray(data.evidence) ? data.evidence : [];
    const result: string[] = [];
    const seen = new Set<string>();
    const pushProjectId = (raw: unknown) => {
      const pid = String(raw || '').trim();
      if (!pid || seen.has(pid)) return;
      seen.add(pid);
      result.push(pid);
    };

    const content = String(renderedContent || data.answer || '').trim();
    const referencePart = content.includes('参考与证据')
      ? content.slice(content.indexOf('参考与证据'))
      : content;
    const referencedEvidenceIndexes = new Set<number>();
    const evidenceNoReg = /(?:\[?证据\s*|证据)(\d+)\]?/g;
    let m: RegExpExecArray | null;
    while ((m = evidenceNoReg.exec(referencePart)) !== null) {
      const idx = Number(m[1]);
      if (Number.isFinite(idx) && idx > 0) {
        referencedEvidenceIndexes.add(idx);
      }
    }

    if (referencedEvidenceIndexes.size > 0) {
      Array.from(referencedEvidenceIndexes)
        .sort((a, b) => a - b)
        .forEach((idx) => {
          const ev = evidence[idx - 1];
          if (ev && typeof ev === 'object') {
            pushProjectId((ev as any).project_id || (ev as any).projectId);
          }
        });
      if (result.length) return result;
    }

    for (const ev of evidence) {
      if (!ev || typeof ev !== 'object') continue;
      const pid = String((ev as any).project_id || (ev as any).projectId || '').trim();
      const projectName = String((ev as any).project_name || (ev as any).projectName || '').trim();
      if (pid && referencePart.includes(pid)) {
        pushProjectId(pid);
      } else if (projectName && referencePart.includes(projectName)) {
        pushProjectId(pid);
      }
    }
    if (result.length) return result;

    return [];
  }

  const copyMessage = async (content: string) => {
    if (!content) {
      return;
    }
    if (navigator.clipboard && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(content);
        message.success('复制成功');
        return;
      } catch (e) {
        console.warn('navigator.clipboard 失败，尝试降级方案:', e);
      }
    }
    
    // 降级方案：使用 textarea 和 execCommand
    const textArea = document.createElement('textarea');
    textArea.value = content;
    // 避免页面滚动
    textArea.style.position = 'fixed';
    textArea.style.top = '-99999px';
    textArea.style.left = '-99999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
      const successful = document.execCommand('copy');
      if (successful) {
        message.success('复制成功');
      } else {
        message.error('复制失败，请手动复制');
      }
    } catch (err) {
      console.error('降级方案复制失败:', err);
      message.error('复制失败，请手动复制');
    } finally {
      document.body.removeChild(textArea);
    }
  };

  const deleteMessage = (index: number) => {
    messages.value.splice(index, 1);
    message.info('消息已删除');
  };

  const clearAllMessages = () => {
    if (messages.value.length === 0) {
      message.info('没有可清除的消息');
      return;
    }
    messages.value = [];
    currentSessionId.value = '';
    router.replace({ name: 'agent_index', query: {} });
    messages.value.push({ type: 'ai-message', content: WELCOME_TEXT });
    message.success('已清空当前窗口');
  };

  const createNewChat = () => {
    currentSessionId.value = '';
    messages.value = [];
    messages.value.push({
      type: 'ai-message',
      content: WELCOME_TEXT,
    });
    // 必须去掉 ?session=，否则 watch 会立刻把旧会话再拉回来
    router.replace({ name: 'agent_index', query: {} });
    message.success('已创建新对话');
    window.dispatchEvent(new CustomEvent(CHAT_HISTORY_REFRESH_EVENT));
    nextTick(() => scrollToBottom());
  };

  const loadChatHistory = async (sessionId: string) => {
    try {
      const response = await getChatHistory(userStore.getToken, { session_id: sessionId });
      if (response.code === 0) {
        currentSessionId.value = sessionId;
        messages.value = [];
        const history: ChatMessage[] = response.data;
        history.forEach((msg) => {
          const reasoning = String(msg.reasoning || '');
          const hasReasoning = reasoning.trim().length > 0;
          const payloadForRender = {
            answer: msg.content,
            evidence: Array.isArray(msg.evidence) ? msg.evidence : [],
            web_search_meta:
              msg.web_search_meta && typeof msg.web_search_meta === 'object'
                ? msg.web_search_meta
                : undefined,
            web_search_attempted: Boolean(msg.web_search_attempted),
            quality_hints: msg.quality_hints,
            kg_lookup_status: String(msg.kg_lookup_status || ''),
            intent_coarse: String(msg.intent_coarse || ''),
            intent: String(msg.intent || ''),
          };
          const webEvidenceCards =
            msg.role === 'assistant' ? parseWebEvidenceCardsFromPayload(payloadForRender) : [];
          messages.value.push({
            type: msg.role === 'user' ? 'user-message' : 'ai-message',
            content: msg.content,
            ...(msg.role === 'assistant'
              ? {
                  webEvidenceCards,
                  sourceFootnote: buildReplySourceFootnote(
                    payloadForRender,
                    Boolean(msg.web_search_attempted),
                  ),
                  diagnosticPayload: {
                    quality_hints: msg.quality_hints,
                    web_search_meta: msg.web_search_meta,
                  },
                }
              : {}),
            ...(msg.role === 'assistant' && (Boolean(msg.deep_think) || hasReasoning)
              ? {
                  deepThink: true,
                  reasoning,
                  reasoningCollapsed: hasReasoning,
                }
              : {}),
          });
        });
        message.success('历史对话已加载');
        scrollToBottom();
      } else {
        message.error('加载历史对话失败');
      }
    } catch (error) {
      console.error('加载历史对话失败:', error);
      message.error('加载历史对话失败');
    }
  };

  const scrollToBottom = () => {
    if (messagesContainer.value) {
      nextTick(() => {
        if (messagesContainer.value)
          messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
      });
    }
  };

  watch(userInput, () => {
    nextTick(() => {
      scrollToBottom();
    });
  });

  watch(
    () => route.query.session,
    (sessionId) => {
      if (sessionId && typeof sessionId === 'string') {
        loadChatHistory(sessionId);
      }
    },
    { immediate: true }
  );

  const applyResetFromSidebar = () => {
    currentSessionId.value = '';
    messages.value = [];
    messages.value.push({
      type: 'ai-message',
      content: WELCOME_TEXT,
    });
    nextTick(() => scrollToBottom());
  };

  onMounted(() => {
    restoreWebSearchPrefs();
    void initializeGraphProjects();
    window.addEventListener('mousemove', onSplitResizeMove);
    window.addEventListener('mouseup', stopResizeSplit);
    if (typeof ResizeObserver !== 'undefined') {
      graphResizeObserver = new ResizeObserver(() => {
        graphChart?.resize();
      });
      if (graphPanelRef.value) {
        graphResizeObserver.observe(graphPanelRef.value);
      }
      if (kgCanvasShellRef.value) {
        graphResizeObserver.observe(kgCanvasShellRef.value);
      }
    }
    document.addEventListener('fullscreenchange', handleGraphFullscreenChange);
    if (!route.query.session) {
      messages.value.push({
        type: 'ai-message',
        content: WELCOME_TEXT,
      });
    }
    window.addEventListener(CHAT_RESET_EVENT, applyResetFromSidebar);
  });

  onUnmounted(() => {
    window.removeEventListener('mousemove', onSplitResizeMove);
    window.removeEventListener('mouseup', stopResizeSplit);
    stopResizeSplit();
    window.removeEventListener(CHAT_RESET_EVENT, applyResetFromSidebar);
    document.removeEventListener('fullscreenchange', handleGraphFullscreenChange);
    if (focusGraphSpotlightTimer !== null) {
      window.clearTimeout(focusGraphSpotlightTimer);
      focusGraphSpotlightTimer = null;
    }
    if (clearGraphSpotlightTimer !== null) {
      window.clearTimeout(clearGraphSpotlightTimer);
      clearGraphSpotlightTimer = null;
    }
    graphResizeObserver?.disconnect();
    graphResizeObserver = null;
    graphChart?.dispose();
    graphChart = null;
    diagnosticDrawerVisible.value = false;
    activeDiagnosticPayload.value = null;
  });
</script>

<style scoped lang="scss">
  .agent-page {
    --biz-text: #111827;
    --biz-text-secondary: #6b7280;
    --biz-border: #e5e7eb;
    --biz-surface: #ffffff;
    --biz-page-bg: #f4f5f7;
    --biz-accent: var(--platform-primary, #2d8cf0);
    /* 用户气泡：浅底 + 深字（不支持 color-mix 时有纯色兜底） */
    --user-bubble-bg: #eef6fc;
    --user-bubble-fg: #164364;
    --user-bubble-border: #cfe8f6;
    --user-bubble-muted: #3d6a8c;
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    box-sizing: border-box;
    /* 铺满主内容可视区：顶栏/边距预留；多页签时可略减小可视高度，由外层 layout 滚动 */
    height: calc(100dvh - 100px);
    max-height: calc(100dvh - 100px);
    min-height: 420px;
    padding: 16px clamp(12px, 2.5vw, 28px) 20px;
  }

  .agent-page__bg {
    position: fixed;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    background: var(--biz-page-bg);
  }

  .agent-page__inner {
    position: relative;
    z-index: 1;
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    width: 100%;
    max-width: min(1400px, 100%);
    margin: 0 auto;
    box-sizing: border-box;
  }

  .agent-workspace {
    --kg-pane-width: 46%;
    flex: 1;
    min-height: 0;
    display: grid;
    grid-template-columns: minmax(360px, var(--kg-pane-width)) 12px minmax(520px, 1fr);
    gap: 0;
  }

  .agent-workspace--resizing {
    cursor: col-resize;
  }

  .workspace-splitter {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: col-resize;
    user-select: none;
  }

  .workspace-splitter::before {
    content: '';
    position: absolute;
    inset: 0;
    background: transparent;
  }

  .workspace-splitter__bar {
    width: 4px;
    height: 72px;
    border-radius: 999px;
    background: linear-gradient(180deg, #cbd5e1 0%, #94a3b8 100%);
    box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.24);
    transition: background 0.18s ease;
  }

  .workspace-splitter:hover .workspace-splitter__bar,
  .agent-workspace--resizing .workspace-splitter__bar {
    background: linear-gradient(180deg, #60a5fa 0%, #3b82f6 100%);
  }

  .kg-pane {
    min-height: 0;
    display: flex;
    flex-direction: column;
    border-radius: 12px;
    border: 1px solid var(--biz-border);
    background: var(--biz-surface);
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
    overflow: hidden;
  }

  .kg-pane__header {
    padding: 12px 14px 10px;
    border-bottom: 1px solid var(--biz-border);

    h2 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
      color: var(--biz-text);
    }

    p {
      margin: 4px 0 0;
      font-size: 12px;
      color: var(--biz-text-secondary);
    }
  }

  .kg-filters {
    padding: 12px 14px;
    border-bottom: 1px solid var(--biz-border);
    display: flex;
    flex-direction: column;
    gap: 8px;
    background: #f8fafc;
  }

  .kg-filters__row {
    display: grid;
    grid-template-columns: 1fr 120px;
    gap: 8px;
  }

  .kg-filters__type {
    min-width: 0;
  }

  .kg-filters__actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .kg-stats {
    padding: 8px 14px;
    border-bottom: 1px dashed #dbe3ef;
    font-size: 12px;
    color: #64748b;
    display: flex;
    gap: 14px;
  }

  .kg-canvas-shell {
    position: relative;
    flex: 1;
    min-height: 0;
    padding: 10px;
    background: #f8fbff;
  }

  .kg-canvas-stage {
    position: relative;
    width: 100%;
    height: 100%;
    min-height: 280px;
  }

  .kg-overlay-tools {
    position: absolute;
    top: 10px;
    right: 10px;
    z-index: 6;
    display: flex;
    align-items: center;
    gap: 8px;
    opacity: 0;
    transform: translateY(-6px);
    pointer-events: none;
    transition:
      opacity 0.18s ease,
      transform 0.18s ease;
  }

  .kg-canvas-stage:hover .kg-overlay-tools,
  .kg-canvas-stage:focus-within .kg-overlay-tools,
  .kg-canvas-stage:fullscreen .kg-overlay-tools {
    opacity: 1;
    transform: translateY(0);
    pointer-events: auto;
  }

  .kg-overlay-tools :deep(.n-button) {
    box-shadow: 0 8px 22px rgba(15, 23, 42, 0.16);
    border-color: rgba(148, 163, 184, 0.4);
    background: rgba(255, 255, 255, 0.96);
    backdrop-filter: blur(6px);
  }

  .kg-zoom-indicator {
    position: absolute;
    left: 12px;
    top: 10px;
    z-index: 5;
    padding: 2px 8px;
    border-radius: 8px;
    font-size: 12px;
    color: #475569;
    background: rgba(255, 255, 255, 0.86);
    border: 1px solid rgba(148, 163, 184, 0.26);
    pointer-events: none;
  }

  .kg-canvas {
    width: 100%;
    height: 100%;
    min-height: 280px;
    border: 1px solid #dbe3ef;
    border-radius: 10px;
    background:
      linear-gradient(rgba(148, 163, 184, 0.12) 1px, transparent 1px),
      linear-gradient(90deg, rgba(148, 163, 184, 0.12) 1px, transparent 1px),
      radial-gradient(circle at 14% 14%, #f8fbff 0%, #ffffff 56%, #f5f9ff 100%);
    background-size:
      24px 24px,
      24px 24px,
      auto;
  }

  .kg-canvas-stage:fullscreen {
    background: #f8fbff;
    padding: 14px;
    box-sizing: border-box;
    overflow: auto;
  }

  .kg-canvas-stage:fullscreen .kg-canvas {
    height: calc(100vh - 96px);
    min-height: 420px;
  }

  .kg-empty {
    height: 100%;
    min-height: 280px;
    border: 1px dashed #cbd5e1;
    border-radius: 10px;
    color: #94a3b8;
    font-size: 13px;
    display: grid;
    place-items: center;
    background: #ffffff;
  }

  .agent-chat-shell {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    border-radius: 12px;
    border: 1px solid var(--biz-border);
    background: var(--biz-surface);
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
    overflow: hidden;
  }

  @media (max-width: 1280px) {
    .agent-workspace {
      grid-template-columns: 1fr;
      grid-template-rows: minmax(360px, 44%) minmax(420px, 1fr);
    }

    .workspace-splitter {
      display: none;
    }
  }

  .chat-hero {
    flex-shrink: 0;
    padding: 14px 16px 12px;
    border-bottom: 1px solid var(--biz-border);
    background: var(--biz-surface);
  }

  .chat-hero__meta {
    margin: 0 0 6px;
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.01em;
    color: var(--biz-text-secondary);
    line-height: 1.4;
  }

  .chat-hero__main {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .chat-hero__title {
    margin: 0;
    font-size: clamp(1.15rem, 2.6vw, 1.35rem);
    font-weight: 600;
    letter-spacing: -0.02em;
    line-height: 1.3;
    color: var(--biz-text);
  }

  .chat-hero__subtitle {
    margin: 0;
    font-size: 13px;
    line-height: 1.55;
    color: var(--biz-text-secondary);
  }

  /* 占满卡片内剩余高度，仅消息区滚动 */
  .chat-container {
    flex: 1;
    min-height: 0;
    background: var(--biz-surface);
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .chat-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    border-bottom: 1px solid var(--biz-border);
    background: var(--biz-surface);
    flex-shrink: 0;
  }

  .chat-header__brand {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
  }

  .chat-header__icon {
    flex-shrink: 0;
    width: 36px;
    height: 36px;
    display: grid;
    place-items: center;
    border-radius: 8px;
    color: var(--biz-text-secondary);
    background: #f3f4f6;
    border: 1px solid var(--biz-border);

    svg {
      width: 20px;
      height: 20px;
    }
  }

  .chat-header__main {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }

  .chat-header__title {
    font-weight: 600;
    font-size: 14px;
    color: var(--biz-text);
    letter-spacing: -0.01em;
  }

  .chat-header__hint {
    font-size: 12px;
    color: #9ca3af;
  }

  .chat-actions {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-shrink: 0;
  }

  .chat-actions__btn {
    border-radius: 6px !important;
    font-weight: 500 !important;
    font-size: 13px !important;
    color: var(--biz-text-secondary) !important;

    &:hover {
      color: var(--biz-text) !important;
      background: #f3f4f6 !important;
    }
  }

  .chat-messages {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    background: #fafafa;

    scrollbar-width: thin;
    scrollbar-color: #d1d5db transparent;

    &::-webkit-scrollbar {
      width: 6px;
    }
    &::-webkit-scrollbar-thumb {
      background: #d1d5db;
      border-radius: 3px;
    }
  }

  .message {
    display: flex;
    align-items: flex-start;
    gap: 10px;

    .message-side {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
      flex-shrink: 0;
      width: 40px;
    }

    .message-role {
      font-size: 11px;
      font-weight: 500;
      color: #9ca3af;
      line-height: 1;
    }

    .message-avatar {
      :deep(.n-avatar) {
        border: 1px solid var(--biz-border);
      }
    }

    &.ai-message {
      .message-content {
        background: var(--biz-surface);
        border: 1px solid var(--biz-border);
        border-radius: 10px;
        box-shadow: none;
      }

      .message-text {
        line-height: 1.4;
      }
    }

    &.user-message {
      flex-direction: row-reverse;

      .message-role {
        color: #9ca3af;
      }

      .message-content {
        background: var(--user-bubble-bg);
        color: var(--user-bubble-fg);
        border-radius: 10px;
        border: 1px solid var(--user-bubble-border);
        box-shadow: none;
      }

      /* 覆盖全局 .message-text 的深色，否则会把用户字压成灰黑 */
      .message-text {
        color: var(--user-bubble-fg);
      }

      .markdown-content {
        color: var(--user-bubble-fg);

        h1,
        h2,
        h3,
        h4,
        h5,
        h6 {
          color: #0f2942;
        }

        blockquote {
          background: rgba(255, 255, 255, 0.72);
          border-left: 3px solid var(--biz-accent);
        }

        code {
          background: rgba(255, 255, 255, 0.85);
          color: #0c4a6e;
        }

        th {
          background: rgba(255, 255, 255, 0.75);
        }

        th,
        td {
          border-color: rgba(148, 163, 184, 0.55);
        }
      }

      .delete-btn {
        color: var(--user-bubble-muted);

        &:hover {
          color: var(--user-bubble-fg);
        }
      }
    }

    .message-content {
      padding: 10px 14px;
      max-width: min(92%, calc(100% - 48px));
      position: relative;
      display: flex;
      align-items: flex-start;
      gap: 8px;

      .message-text {
        white-space: pre-wrap;
        line-height: 1.45;
        flex: 1;
        font-size: 14px;
        color: var(--biz-text);

        .ai-stream-placeholder {
          display: flex;
          align-items: center;
          gap: 8px;
          color: var(--biz-text-secondary);
          min-height: 24px;
          font-size: 13px;
        }

        .reasoning-panel {
          margin-bottom: 10px;
          border-radius: 8px;
          border: 1px solid var(--biz-border);
          background: #f9fafb;
          overflow: hidden;
        }

        .reasoning-panel__header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          width: 100%;
          padding: 8px 12px;
          margin: 0;
          border: none;
          background: transparent;
          cursor: pointer;
          font-size: 12px;
          color: var(--biz-text-secondary);
          text-align: left;
          transition: background 0.12s ease;

          &:hover {
            background: #f3f4f6;
          }
        }

        .reasoning-panel__title {
          font-weight: 600;
          color: var(--biz-text);
        }

        .reasoning-panel__toggle {
          font-size: 12px;
          color: #9ca3af;
        }

        .reasoning-panel__body {
          padding: 0 12px 10px;
          border-top: 1px solid var(--biz-border);
        }

        .reasoning-panel__pre {
          margin: 8px 0 0;
          padding: 10px 12px;
          white-space: pre-wrap;
          word-break: break-word;
          font-family: inherit;
          font-size: 11px;
          line-height: 1.42;
          color: var(--biz-text);
          background: var(--biz-surface);
          border-radius: 6px;
          border: 1px solid var(--biz-border);
          max-height: min(280px, 40vh);
          overflow-y: auto;
        }

        .reasoning-panel__placeholder {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 0 2px;
          font-size: 12px;
          color: var(--biz-text-secondary);
        }

        > pre {
          margin: 6px 0;
          padding: 10px 12px;
          white-space: pre-wrap;
          font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
          font-size: 12px;
          line-height: 1.5;
          background: #f9fafb;
          border-radius: 6px;
          border: 1px solid var(--biz-border);
          overflow-x: auto;
        }

        .markdown-content {
          line-height: 1.4;
          font-size: 14px;
          color: #374151;

          > *:first-child {
            margin-top: 0 !important;
          }

          > *:last-child {
            margin-bottom: 0 !important;
          }

          h1,
          h2,
          h3,
          h4,
          h5,
          h6 {
            margin: 0.4em 0 0.2em;
            font-weight: 600;
            color: var(--biz-text);
            line-height: 1.28;

            &:first-child {
              margin-top: 0;
            }
          }

          h1 {
            font-size: 1.15em;
          }
          h2 {
            font-size: 1.08em;
          }

          h3 {
            font-size: 1.02em;
          }

          a {
            color: #2563eb;
            text-decoration: underline;
            text-underline-offset: 2px;
            word-break: break-all;
          }

          a:hover {
            color: #1d4ed8;
          }

          /* v-html 注入节点无组件 data 属性，须 :deep 穿透 scoped，否则样式不生效 */
          :deep(.kg-qna-answer) {
            position: relative;
            padding: 18px 20px 20px;
            border-radius: 14px;
            font-size: 14px;
            line-height: 1.42;
            color: var(--biz-text);
            background: linear-gradient(
              165deg,
              rgba(255, 255, 255, 0.98) 0%,
              rgba(248, 250, 252, 0.96) 55%,
              rgba(241, 245, 249, 0.88) 100%
            );
            border: 1px solid rgba(226, 232, 240, 0.95);
            box-shadow:
              0 2px 8px rgba(15, 23, 42, 0.05),
              inset 0 1px 0 rgba(255, 255, 255, 0.9);

            &::before {
              content: '';
              position: absolute;
              left: 0;
              top: 14px;
              bottom: 14px;
              width: 4px;
              border-radius: 4px;
              background: linear-gradient(180deg, #3b82f6 0%, #6366f1 45%, #8b5cf6 100%);
              opacity: 0.92;
            }

            > *:first-child {
              margin-top: 0 !important;
            }

            > *:last-child {
              margin-bottom: 0 !important;
            }

            > * + * {
              margin-top: 0.16em !important;
            }

            p {
              margin: 0;
              text-align: justify;
              text-justify: inter-ideograph;
            }

            p + p {
              margin-top: 0;
            }

            p:last-child {
              margin-bottom: 0;
            }

            strong {
              color: #1e293b;
              font-weight: 650;
            }

            :deep(.kg-answer-section-label) {
              display: flex;
              align-items: center;
              gap: 0.45em;
              margin: 0.22em 0 0.1em;
              font-size: 0.98em;
              line-height: 1.2;
              font-weight: 700;
              color: #0f172a;

              &::before {
                content: '';
                width: 0.5em;
                height: 0.5em;
                border-radius: 999px;
                background: linear-gradient(180deg, #3b82f6 0%, #2563eb 100%);
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
                flex: 0 0 auto;
              }
            }

            h1,
            h2,
            h3,
            h4,
            h5,
            h6 {
              margin: 0.18em 0 0.08em;
              line-height: 1.2;
            }

            ul,
            ol,
            blockquote,
            pre,
            table {
              margin-top: 0.18em;
              margin-bottom: 0.18em;
            }
          }

          :deep(.kg-qna-evidence) {
            margin-top: 1.35rem;
            padding: 16px 18px 18px;
            border-radius: 14px;
            border: 1px solid rgba(148, 163, 184, 0.42);
            background:
              linear-gradient(rgba(255, 255, 255, 0.55), rgba(255, 255, 255, 0.55)),
              repeating-linear-gradient(
                -12deg,
                transparent,
                transparent 10px,
                rgba(241, 245, 249, 0.55) 10px,
                rgba(241, 245, 249, 0.55) 11px
              ),
              linear-gradient(
                168deg,
                rgba(248, 250, 252, 0.99) 0%,
                rgba(226, 232, 240, 0.35) 100%
              );
            box-shadow:
              inset 0 1px 0 rgba(255, 255, 255, 0.85),
              0 2px 10px rgba(15, 23, 42, 0.06);

            h2:first-of-type {
              margin: 0 0 14px;
              padding: 6px 0 10px;
              border-bottom: 1px solid rgba(148, 163, 184, 0.45);
              font-size: 0.72rem;
              font-weight: 700;
              letter-spacing: 0.12em;
              color: #475569;
              text-transform: none;
            }

            h3,
            h3.kg-ev-section-label {
              display: inline-flex;
              align-items: center;
              margin: 16px 0 10px;
              padding: 5px 12px;
              font-size: 0.72rem;
              font-weight: 650;
              letter-spacing: 0.06em;
              color: #334155;
              background: rgba(255, 255, 255, 0.72);
              border: 1px solid rgba(148, 163, 184, 0.45);
              border-radius: 999px;
              box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            }

            h3:first-of-type,
            h3.kg-ev-section-label:first-of-type {
              margin-top: 0;
            }

            p,
            li {
              font-size: 0.86rem;
              line-height: 1.62;
              color: #475569;
            }

            p + p.kg-bare-url-line {
              margin-top: -0.35em;
              margin-bottom: 0.65em;
            }

            ul,
            ol {
              margin: 0.15em 0 0.45em;
              padding-left: 1.1em;
            }

            a {
              font-family:
                ui-monospace,
                SFMono-Regular,
                Menlo,
                Monaco,
                Consolas,
                'Liberation Mono',
                'Courier New',
                monospace;
              font-size: 0.84rem;
              color: #1d4ed8;
              text-decoration: none;
              border-bottom: 1px solid rgba(37, 99, 235, 0.35);
              word-break: break-all;
            }

            a:hover {
              color: #1e40af;
              border-bottom-color: rgba(30, 64, 175, 0.6);
            }

            .kg-evidence-chip {
              font-size: 11px;
            }

            :deep(.kg-web-card) {
              position: relative;
              margin: 10px 0 12px;
              padding: 12px 12px 10px;
              border-radius: 12px;
              border: 1px solid rgba(59, 130, 246, 0.28);
              background:
                radial-gradient(120% 140% at 100% 0%, rgba(59, 130, 246, 0.08) 0%, rgba(59, 130, 246, 0) 45%),
                linear-gradient(165deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.98));
              box-shadow:
                0 6px 18px rgba(15, 23, 42, 0.07),
                inset 0 1px 0 rgba(255, 255, 255, 0.92);
            }

            :deep(.kg-web-card__head) {
              display: flex;
              align-items: center;
              gap: 8px;
              margin-bottom: 8px;
              flex-wrap: wrap;
            }

            :deep(.kg-web-card__tag) {
              display: inline-flex;
              align-items: center;
              padding: 2px 8px;
              border-radius: 999px;
              font-size: 11px;
              font-weight: 600;
              letter-spacing: 0.02em;
              color: #1d4ed8;
              background: rgba(219, 234, 254, 0.9);
              border: 1px solid rgba(147, 197, 253, 0.75);
            }

            :deep(.kg-web-card__title) {
              margin: 0;
              font-size: 14px;
              line-height: 1.45;
              font-weight: 650;
              color: #0f172a;
            }

            :deep(.kg-web-card__summary) {
              margin: 8px 0 10px;
              font-size: 12px;
              line-height: 1.58;
              color: #475569;
            }

            :deep(.kg-web-card__cta) {
              display: inline-flex;
              align-items: center;
              padding: 4px 10px;
              border-radius: 999px;
              background: linear-gradient(180deg, #dbeafe 0%, #bfdbfe 100%);
              border: 1px solid rgba(147, 197, 253, 0.95);
              color: #1e40af;
              font-size: 12px;
              font-weight: 600;
              text-decoration: none;
              box-shadow: 0 1px 3px rgba(30, 64, 175, 0.12);
            }

            :deep(.kg-web-card__cta:hover) {
              color: #1e3a8a;
              border-color: rgba(96, 165, 250, 0.95);
            }

            :deep(.kg-web-card__url) {
              margin-top: 8px;
              font-family:
                ui-monospace,
                SFMono-Regular,
                Menlo,
                Monaco,
                Consolas,
                'Liberation Mono',
                'Courier New',
                monospace;
              font-size: 11px;
              line-height: 1.4;
              color: #64748b;
              word-break: break-all;
            }

            blockquote {
              margin: 0.4em 0;
              padding: 8px 10px;
              background: rgba(255, 255, 255, 0.55);
              border-left: 2px solid #94a3b8;
            }

            code {
              font-size: 0.82rem;
              background: rgba(255, 255, 255, 0.65);
            }
          }

          p {
            margin: 0;

            & + p {
              margin-top: 0;
            }

            &:last-child {
              margin-bottom: 0;
            }
          }

          /* marked 偶发产生空段落，避免大块空白 */
          p:empty {
            display: none;
            margin: 0;
            height: 0;
          }

          li {
            margin: 0;
            padding: 0;
            line-height: 1.4;
          }

          li + li {
            margin-top: 0.15em;
          }

          ul,
          ol {
            margin: 0.15em 0 0.35em;
            padding-left: 1.05em;
          }

          blockquote {
            margin: 0.35em 0;
            padding: 6px 10px;
            background: #f9fafb;
            border-left: 2px solid #d1d5db;
            border-radius: 4px;
          }

          hr {
            margin: 0.5em 0;
            border: none;
            border-top: 1px solid var(--biz-border);
          }

          code {
            background: #f3f4f6;
            padding: 1px 4px;
            border-radius: 3px;
            font-family: ui-monospace, monospace;
            font-size: 0.88em;
          }

          pre {
            margin: 0.35em 0;
            padding: 8px 10px;
            white-space: pre-wrap;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 12px;
            line-height: 1.38;
            background: #f9fafb;
            border-radius: 6px;
            border: 1px solid var(--biz-border);
            overflow-x: auto;
          }

          pre code {
            padding: 0;
            background: transparent;
            font-size: inherit;
          }

          table {
            width: 100%;
            border-collapse: collapse;
            margin: 4px 0;
            font-size: 13px;
          }

          th,
          td {
            padding: 5px 7px;
            border: 1px solid var(--biz-border);
          }

          th {
            background: #f9fafb;
          }

          :deep(.kg-evidence-chip) {
            display: inline-flex;
            align-items: center;
            vertical-align: middle;
            margin: 0 2px 2px 0;
            padding: 2px 10px;
            max-width: 100%;
            font-size: 12px;
            font-weight: 500;
            line-height: 1.35;
            color: #1e40af;
            background: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%);
            border: 1px solid #93c5fd;
            border-radius: 999px;
            box-shadow: 0 1px 2px rgba(30, 64, 175, 0.08);
            white-space: normal;
            word-break: break-word;
          }
        }

        .markdown-content--streaming {
          border-left: 2px solid var(--biz-accent);
          padding-left: 10px;
          margin-left: 0;
        }

        .payload-web-cards {
          margin-top: 10px;
          display: grid;
          gap: 10px;
        }

        .payload-web-card {
          padding: 12px;
          border-radius: 12px;
          border: 1px solid rgba(59, 130, 246, 0.3);
          background:
            radial-gradient(120% 140% at 100% 0%, rgba(59, 130, 246, 0.08) 0%, rgba(59, 130, 246, 0) 45%),
            linear-gradient(165deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.98));
          box-shadow:
            0 6px 18px rgba(15, 23, 42, 0.07),
            inset 0 1px 0 rgba(255, 255, 255, 0.92);
        }

        .payload-web-card__head {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;
          margin-bottom: 8px;
        }

        .payload-web-card__chip,
        .payload-web-card__tag {
          display: inline-flex;
          align-items: center;
          padding: 2px 8px;
          border-radius: 999px;
          font-size: 11px;
          font-weight: 600;
        }

        .payload-web-card__chip {
          color: #334155;
          background: rgba(255, 255, 255, 0.88);
          border: 1px solid rgba(148, 163, 184, 0.55);
        }

        .payload-web-card__tag {
          color: #1d4ed8;
          background: rgba(219, 234, 254, 0.9);
          border: 1px solid rgba(147, 197, 253, 0.75);
        }

        .payload-web-card__title {
          margin: 0;
          font-size: 14px;
          line-height: 1.45;
          font-weight: 650;
          color: #0f172a;
        }

        .payload-web-card__summary {
          margin: 8px 0 10px;
          font-size: 12px;
          line-height: 1.58;
          color: #475569;
        }

        .payload-web-card__cta {
          display: inline-flex;
          align-items: center;
          padding: 4px 10px;
          border-radius: 999px;
          background: linear-gradient(180deg, #dbeafe 0%, #bfdbfe 100%);
          border: 1px solid rgba(147, 197, 253, 0.95);
          color: #1e40af;
          font-size: 12px;
          font-weight: 600;
          text-decoration: none;
          box-shadow: 0 1px 3px rgba(30, 64, 175, 0.12);
        }

        .payload-web-card__cta:hover {
          color: #1e3a8a;
          border-color: rgba(96, 165, 250, 0.95);
        }

        .payload-web-card__actions {
          margin-top: 8px;
          display: flex;
          justify-content: flex-end;
        }

        .payload-web-card__url {
          margin-top: 8px;
          font-family:
            ui-monospace,
            SFMono-Regular,
            Menlo,
            Monaco,
            Consolas,
            'Liberation Mono',
            'Courier New',
            monospace;
          font-size: 11px;
          line-height: 1.4;
          color: #64748b;
          word-break: break-all;
        }

        .reply-source-footnote {
          margin: 8px 0 0;
          padding: 0;
          font-size: 11px;
          line-height: 1.4;
          color: #94a3b8;
        }

        .diagnostic-trigger {
          margin-top: 4px;
        }
      }

      .message-actions {
        opacity: 0;
        transition: opacity 0.15s ease;
        flex-shrink: 0;
      }

      &:hover .message-actions {
        opacity: 1;
      }
    }
  }

  .diagnostic-drawer {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .diagnostic-drawer__hint {
    margin: 0;
    font-size: 12px;
    line-height: 1.5;
    color: #64748b;
  }

  .diagnostic-section {
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 10px;
    background: #f8fafc;

    h4 {
      margin: 0 0 8px;
      font-size: 13px;
      font-weight: 700;
      color: #0f172a;
    }

    pre {
      margin: 0;
      max-height: 220px;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 12px;
      line-height: 1.5;
      color: #334155;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 8px;
    }
  }

  .diagnostic-web-hint {
    margin: 0 0 8px;
    font-size: 12px;
    line-height: 1.5;
    color: #475569;
  }

  .chat-input-area {
    border-top: 1px solid var(--biz-border);
    background: var(--biz-surface);
    flex-shrink: 0;
  }

  .composer-settings {
    padding: 12px 16px 8px;
  }

  .composer-settings__items {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }

  .composer-chip {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    border-radius: 6px;
    cursor: pointer;
    user-select: none;
    background: #f9fafb;
    border: 1px solid var(--biz-border);
    transition:
      border-color 0.15s,
      background 0.15s;

    &:hover {
      border-color: #d1d5db;
      background: #f3f4f6;
    }
  }

  .composer-chip--active {
    border-color: #bfdbfe;
    background: #eff6ff;
  }

  .composer-chip__label {
    font-size: 13px;
    font-weight: 500;
    color: var(--biz-text-secondary);
  }

  .composer-settings__hint {
    margin: 8px 0 0;
    font-size: 11px;
    line-height: 1.5;
    color: #9ca3af;
    max-width: 100%;
  }

  .composer {
    display: flex;
    gap: 10px;
    align-items: stretch;
    padding: 4px 16px 16px;

    .composer__input {
      flex: 1;

      :deep(.n-input-wrapper) {
        border-radius: 8px;
        border: 1px solid var(--biz-border);
        background: var(--biz-surface);
        box-shadow: none;
        transition: border-color 0.15s;
      }

      :deep(.n-input-wrapper:focus-within) {
        border-color: var(--biz-accent);
        box-shadow: 0 0 0 1px var(--biz-accent);
      }

      :deep(.n-input__textarea-el) {
        font-size: 14px;
        line-height: 1.55;
      }
    }

    .composer__send {
      flex-shrink: 0;
      align-self: flex-end;
      min-width: 88px;
      height: 44px;
      padding: 0 16px;
      border-radius: 8px;
      font-weight: 600;
      font-size: 14px;
      letter-spacing: 0;
      background: var(--biz-accent) !important;
      border: none !important;
      box-shadow: none;

      &:hover:not(:disabled) {
        filter: brightness(1.06);
      }

      &:disabled {
        opacity: 0.4;
      }
    }
  }

  @media (max-width: 768px) {
    .agent-page {
      height: calc(100dvh - 88px);
      max-height: calc(100dvh - 88px);
      min-height: 320px;
      padding: 14px 12px 16px;
    }

    .agent-chat-shell {
      border-radius: 10px;
    }

    .message .message-content {
      max-width: min(94%, calc(100% - 40px));
    }

    .composer {
      flex-direction: column;
      align-items: stretch;

      .composer__send {
        align-self: stretch;
        width: 100%;
      }
    }
  }

  @supports (color: color-mix(in srgb, black 50%, white)) {
    .agent-page {
      --user-bubble-bg: color-mix(in srgb, var(--platform-primary, #2d8cf0) 12%, #ffffff);
      --user-bubble-border: color-mix(in srgb, var(--platform-primary, #2d8cf0) 28%, #e2e8f0);
    }
  }
</style>
