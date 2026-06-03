<template>
  <div class="graph-editor-page">
    <n-page-header class="page-header" title="图谱编辑" @back="goBack">
      <template #subtitle> 项目 ID：{{ projectId }} </template>
    </n-page-header>

    <n-card class="main-card" :bordered="false">
      <div ref="editorLayoutRef" class="editor-layout" :class="{ 'is-resizing': isResizingPanels }">
        <!-- 左侧：图谱 -->
        <div class="graph-panel">
          <div class="panel-header">
            <span>事件图谱</span>
            <n-space>
              <n-button
                size="small"
                tertiary
                :disabled="!latestEvolutionResult"
                @click="evolutionDrawerVisible = true"
              >
                本次自动演进结果
              </n-button>
              <n-button size="small" type="primary" secondary @click="handleMockEvent">⚡ 演示：注入突发事件</n-button>
              <n-button size="small" :loading="loading" @click="loadGraph">刷新</n-button>
            </n-space>
          </div>
          <div v-if="!hasData" class="empty-tip">
            <n-empty description="暂无图谱数据，请先在构建流程中完成抽取" />
          </div>
          <div v-else ref="graphPreviewRef" class="graph-preview-shell">
            <div class="graph-overlay-tools">
              <n-button
                size="small"
                circle
                secondary
                :disabled="!hasData"
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
                :disabled="!hasData"
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
                :disabled="!hasData"
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
                :disabled="!hasData"
                @click="toggleGraphFullscreen"
                :title="isGraphFullscreen ? '退出全屏' : '全屏查看'"
              >
                <template #icon>
                  <n-icon :component="isGraphFullscreen ? ContractOutline : ExpandOutline" />
                </template>
              </n-button>
            </div>
            <div class="graph-zoom-indicator">缩放 {{ Math.round(graphZoomLevel * 100) }}%</div>
            <div ref="graphChartRef" class="graph-chart"></div>
          </div>
        </div>

        <div
          class="panel-splitter"
          title="拖拽调整左右区域宽度"
          @mousedown.prevent="startResizePanels"
        >
          <span class="panel-splitter__grip" />
        </div>

        <!-- 右侧：表单 -->
        <div class="form-panel" :style="{ width: `${formPanelWidth}px` }">
          <div class="panel-header">
            <span>{{ selectedType === 'node' ? '节点属性' : '关系属性' }}</span>
            <n-button v-if="selected" size="tiny" quaternary @click="selected = null">关闭</n-button>
          </div>
          <div v-if="!selected" class="empty-tip">
            <n-empty description="点击左侧图谱中的节点或关系进行编辑" size="small" />
          </div>
          <template v-else>
            <!-- 节点表单 -->
            <n-form
              v-if="selectedType === 'node'"
              ref="nodeFormRef"
              :model="nodeForm"
              label-placement="top"
              label-width="auto"
              size="small"
            >
              <n-form-item label="ID">
                <n-input :value="nodeForm.id" disabled />
              </n-form-item>
              <n-form-item label="名称 (value)">
                <n-input v-model:value="nodeForm.value" placeholder="节点名称" />
              </n-form-item>
              <n-form-item label="类型">
                <n-select
                  v-model:value="nodeForm.type"
                  :options="[
                    { label: '实体', value: 0 },
                    { label: '事件', value: 1 },
                  ]"
                />
              </n-form-item>
              <n-form-item label="Key">
                <n-input v-model:value="nodeForm.key" placeholder="可选" />
              </n-form-item>
              <n-form-item label="扩展属性">
                <div class="property-editor">
                  <div class="property-editor__list">
                    <div
                      v-for="item in nodePropertyEntries"
                      :key="item.id"
                      class="property-editor__row"
                    >
                      <n-input
                        v-model:value="item.key"
                        placeholder="属性名，例如 source"
                        class="property-editor__key"
                      />
                      <n-input
                        v-model:value="item.value"
                        placeholder="属性值"
                        class="property-editor__value"
                      />
                      <n-button
                        size="tiny"
                        circle
                        quaternary
                        class="property-editor__view"
                        title="查看完整内容"
                        @click="openPropertyValueDialog('节点', item.key, item.value)"
                      >
                        <template #icon>
                          <n-icon :component="EyeOutline" />
                        </template>
                      </n-button>
                      <n-button
                        size="tiny"
                        circle
                        quaternary
                        type="error"
                        class="property-editor__remove"
                        title="删除属性"
                        @click="removeNodePropertyEntry(item.id)"
                      >
                        <template #icon>
                          <n-icon :component="TrashOutline" />
                        </template>
                      </n-button>
                    </div>
                    <div v-if="!nodePropertyEntries.length" class="property-editor__empty">
                      暂无扩展属性，点击下方按钮新增
                    </div>
                  </div>
                  <div class="property-editor__actions">
                    <n-button size="tiny" secondary @click="addNodePropertyEntry">
                      新增属性
                    </n-button>
                  </div>
                </div>
              </n-form-item>
              <n-form-item>
                <n-space>
                  <n-button type="primary" :loading="saving" @click="saveNode">保存</n-button>
                  <n-button :loading="completing" @click="runAttributeCompletion('node')">
                    属性补全
                  </n-button>
                  <n-button type="error" secondary :loading="deleting" @click="handleDeleteNode">
                    删除节点
                  </n-button>
                </n-space>
              </n-form-item>
            </n-form>

            <!-- 边表单 -->
            <n-form
              v-else-if="selectedType === 'edge'"
              ref="edgeFormRef"
              :model="edgeForm"
              label-placement="top"
              label-width="auto"
              size="small"
            >
              <n-form-item label="ID">
                <n-input :value="edgeForm.id" disabled />
              </n-form-item>
              <n-form-item label="起点">
                <n-input :value="edgeForm.from" disabled />
              </n-form-item>
              <n-form-item label="终点">
                <n-input :value="edgeForm.to" disabled />
              </n-form-item>
              <n-form-item label="关系名称 (value)">
                <n-input v-model:value="edgeForm.value" placeholder="关系名称" />
              </n-form-item>
              <n-form-item label="eventRel">
                <n-input v-model:value="edgeForm.eventRel" placeholder="可选" />
              </n-form-item>
              <n-form-item label="扩展属性">
                <div class="property-editor">
                  <div class="property-editor__list">
                    <div
                      v-for="item in edgePropertyEntries"
                      :key="item.id"
                      class="property-editor__row"
                    >
                      <n-input
                        v-model:value="item.key"
                        placeholder="属性名，例如 confidence"
                        class="property-editor__key"
                      />
                      <n-input
                        v-model:value="item.value"
                        placeholder="属性值"
                        class="property-editor__value"
                      />
                      <n-button
                        size="tiny"
                        circle
                        quaternary
                        class="property-editor__view"
                        title="查看完整内容"
                        @click="openPropertyValueDialog('关系', item.key, item.value)"
                      >
                        <template #icon>
                          <n-icon :component="EyeOutline" />
                        </template>
                      </n-button>
                      <n-button
                        size="tiny"
                        circle
                        quaternary
                        type="error"
                        class="property-editor__remove"
                        title="删除属性"
                        @click="removeEdgePropertyEntry(item.id)"
                      >
                        <template #icon>
                          <n-icon :component="TrashOutline" />
                        </template>
                      </n-button>
                    </div>
                    <div v-if="!edgePropertyEntries.length" class="property-editor__empty">
                      暂无扩展属性，点击下方按钮新增
                    </div>
                  </div>
                  <div class="property-editor__actions">
                    <n-button size="tiny" secondary @click="addEdgePropertyEntry">
                      新增属性
                    </n-button>
                  </div>
                </div>
              </n-form-item>
              <n-form-item>
                <n-space>
                  <n-button type="primary" :loading="saving" @click="saveEdge">保存</n-button>
                  <n-button :loading="completing" @click="runAttributeCompletion('edge')">
                    属性补全
                  </n-button>
                  <n-button type="error" secondary :loading="deleting" @click="handleDeleteEdge">
                    删除关系
                  </n-button>
                </n-space>
              </n-form-item>
            </n-form>
          </template>
        </div>
      </div>
    </n-card>

    <n-drawer v-model:show="evolutionDrawerVisible" placement="right" :width="420" :mask-closable="true">
      <n-drawer-content title="本次自动演进结果" closable>
        <template v-if="latestEvolutionResult">
          <div class="evo-summary-grid">
            <div class="evo-summary-item">
              <div class="evo-summary-label">新增事件样本</div>
              <div class="evo-summary-value">{{ latestEvolutionResult.sampleCount }}</div>
            </div>
            <div class="evo-summary-item">
              <div class="evo-summary-label">新增节点</div>
              <div class="evo-summary-value">{{ latestEvolutionResult.newNodes.length }}</div>
            </div>
            <div class="evo-summary-item">
              <div class="evo-summary-label">新增关系</div>
              <div class="evo-summary-value">{{ latestEvolutionResult.newEdges.length }}</div>
            </div>
            <div class="evo-summary-item">
              <div class="evo-summary-label">更新时间</div>
              <div class="evo-summary-value evo-time">{{ latestEvolutionResult.time || '-' }}</div>
            </div>
          </div>

          <div class="evo-section">
            <div class="evo-section-title">新增节点</div>
            <div v-if="!latestEvolutionResult.newNodes.length" class="evo-empty">本轮未识别到新增节点</div>
            <div v-else class="evo-list">
              <div
                v-for="node in latestEvolutionResult.newNodes"
                :key="`node-${node.id}`"
                class="evo-list-item evo-list-item--node"
              >
                <div class="evo-item-main">{{ node.name }}</div>
                <div class="evo-item-sub">ID: {{ node.id }}</div>
              </div>
            </div>
          </div>

          <div class="evo-section">
            <div class="evo-section-title">新增关系</div>
            <div v-if="!latestEvolutionResult.newEdges.length" class="evo-empty">本轮未识别到新增关系</div>
            <div v-else class="evo-list">
              <div
                v-for="edge in latestEvolutionResult.newEdges"
                :key="`edge-${edge.id}`"
                class="evo-list-item evo-list-item--edge"
              >
                <div class="evo-item-main">{{ edge.label }}</div>
                <div class="evo-item-sub">ID: {{ edge.id }}</div>
              </div>
            </div>
          </div>
        </template>
        <n-empty v-else description="暂无自动演进结果，请等待下一次增量更新。" />
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup lang="ts">
  import { ref, computed, watch, onMounted, onUnmounted, nextTick, h } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { useMessage, useNotification, useDialog, NInput, NTag, NIcon } from 'naive-ui';
  import {
    AddOutline,
    RemoveOutline,
    ScanOutline,
    ExpandOutline,
    ContractOutline,
    EyeOutline,
    TrashOutline,
  } from '@vicons/ionicons5';
  import { injectMockEvent, getEvolutionStatus, ackEvolutionNotification } from '@/api/evolution';
  import echarts from '@/utils/lib/echarts';
  import {
    EDGE_COLOR,
    getNodeVisualColor,
    normalizeEdgeDisplayLabel,
    normalizeNodeCategoryFromNode,
    normalizeNodeDisplayName,
    resolveNodeVisualCategory,
    sortVisualCategoryNames,
  } from '@/utils/kg/graph';
  import {
    getNodesByProject,
    getEdgesByProject,
    updateNode,
    updateEdge,
    deleteNode,
    deleteEdge,
    attributeCompletion,
  } from '@/api/kg/extract';

  const route = useRoute();
  const router = useRouter();
  const message = useMessage();
  const notification = useNotification();
  const dialog = useDialog();

  const projectId = computed(() => route.params.projectId as string);

  const editorLayoutRef = ref<HTMLElement | null>(null);
  const graphPreviewRef = ref<HTMLElement | null>(null);
  const graphChartRef = ref<HTMLElement | null>(null);
  const graphZoomLevel = ref(1);
  const isGraphFullscreen = ref(false);
  let graphChart: ReturnType<typeof echarts.init> | null = null;

  const nodes = ref<any[]>([]);
  const edges = ref<any[]>([]);
  const loading = ref(false);
  const saving = ref(false);
  const deleting = ref(false);
  const evolutionDrawerVisible = ref(false);
  const formPanelWidth = ref(360);
  const isResizingPanels = ref(false);

  const latestEvolutionResult = ref<{
    sampleCount: number;
    time: string;
    logId: number;
    newNodes: Array<{ id: string; name: string }>;
    newEdges: Array<{ id: string; label: string; from?: string; to?: string }>;
  } | null>(null);

  let pollingTimer: any = null;
  let graphResizeObserver: ResizeObserver | null = null;
  let clearEvolutionHighlightTimer: number | null = null;
  let focusEvolutionTimer: number | null = null;
  let renderedNodeIndexById = new Map<string, number>();
  let renderedEdgeIndexById = new Map<string, number>();
  const evolutionHighlightNodeIds = ref<Set<string>>(new Set());
  const evolutionHighlightEdgeIds = ref<Set<string>>(new Set());

  const presetMockEvents: Array<{ key: string; title: string; content: string }> = [
    {
      key: '半导体',
      title: '半导体设备订单回暖，产业链景气度上行',
      content:
        '多家半导体设备企业披露最新订单数据，显示先进制程与成熟制程产线投资同步回暖。市场预期设备、材料与封测环节将出现联动增长，相关上市公司盈利修复节奏有望加快。',
    },
    {
      key: '芯片',
      title: '国产芯片发布新一代 AI 加速方案，算力板块活跃',
      content:
        '国内厂商发布面向大模型推理场景的新一代芯片方案，强调能效比与软硬件协同优化。受此影响，芯片设计、服务器整机与算力基础设施相关个股盘中表现活跃。',
    },
    {
      key: '新能源',
      title: '新能源车渗透率持续提升，电池与储能需求共振',
      content:
        '行业数据显示新能源车渗透率维持高位，同时工商业储能项目加速落地。市场关注锂电材料、逆变器与电网配套环节的订单兑现情况，板块交易热度明显抬升。',
    },
    {
      key: '金属',
      title: '有色金属价格走强，上游资源股关注度提升',
      content:
        '受海外库存变化与需求预期改善影响，铜、铝等有色金属期现价格阶段性走强。机构认为资源端供给约束仍在，冶炼与加工环节利润分化将进一步加大。',
    },
    {
      key: '石油',
      title: '国际油价波动加剧，石油产业链迎来估值重估',
      content:
        '在地缘因素与产量政策扰动下，国际油价出现高位震荡。市场对油气开采、油服与炼化板块的盈利弹性预期提升，相关公司估值中枢存在上移可能。',
    },
  ];

  const GRAPH_SERIES_ID = 'graph-editor-series';
  const GRAPH_MIN_ZOOM = 0.25;
  const GRAPH_MAX_ZOOM = 4;
  const MIN_FORM_PANEL_WIDTH = 300;
  const MIN_GRAPH_PANEL_WIDTH = 420;
  const PANEL_SPLITTER_WIDTH = 12;

  function edgeIdentity(edge: any): string {
    const eid = String(edge?.id || '').trim();
    if (eid) return eid;
    return `${String(edge?.from || '')}->${String(edge?.to || '')}::${String(edge?.value || edge?.eventRel || '')}`;
  }

  function buildEvolutionDelta(beforeNodes: any[], beforeEdges: any[], sampleCount: number, time: string, logId: number) {
    const beforeNodeIds = new Set((beforeNodes || []).map((n: any) => String(n?.id || '').trim()).filter(Boolean));
    const beforeEdgeIds = new Set((beforeEdges || []).map((e: any) => edgeIdentity(e)).filter(Boolean));

    const newNodes = (nodes.value || [])
      .filter((n: any) => {
        const id = String(n?.id || '').trim();
        return id && !beforeNodeIds.has(id);
      })
      .map((n: any) => ({
        id: String(n?.id || ''),
        name: normalizeNodeDisplayName(n),
      }));

    const newEdges = (edges.value || [])
      .filter((e: any) => {
        const key = edgeIdentity(e);
        return key && !beforeEdgeIds.has(key);
      })
      .map((e: any) => ({
        id: String(e?.id || edgeIdentity(e)),
        label: normalizeEdgeDisplayLabel(e),
        from: String(e?.from || ''),
        to: String(e?.to || ''),
      }));

    latestEvolutionResult.value = {
      sampleCount: Number(sampleCount || 0),
      time: String(time || ''),
      logId: Number(logId || 0),
      newNodes,
      newEdges,
    };
  }

  async function pollStatus() {
    if (!projectId.value) return;
    try {
      const res = await getEvolutionStatus(projectId.value);
      if (res && res.has_new_update) {
        const beforeNodes = [...nodes.value];
        const beforeEdges = [...edges.value];
        await loadGraph();
        buildEvolutionDelta(
          beforeNodes,
          beforeEdges,
          Number(res.sample_count || 0),
          String(res.time || ''),
          Number(res.log_id || 0)
        );
        focusGraphToEvolutionChanges();
        evolutionDrawerVisible.value = true;
        notification.success({
          title: '✨ 图谱动态演进完成！',
          content: `系统检测到新事件接入（共 ${res.sample_count || 1} 篇），并在后台自动完成了图谱增量构建。新增节点 ${latestEvolutionResult.value?.newNodes.length || 0} 个，新增关系 ${latestEvolutionResult.value?.newEdges.length || 0} 条。`,
          duration: 6000,
        });
        await ackEvolutionNotification(res.log_id);
      }
    } catch (e) {
      // ignore
    }
  }

  function centerGraphOnNodeIndex(nodeIndex: number) {
    if (!graphChart) return;
    if (nodeIndex < 0) return;
    try {
      const chartAny = graphChart as any;
      const seriesModel = chartAny?.getModel?.()?.getSeriesByIndex?.(0);
      const dataList = seriesModel?.getData?.();
      const layout = dataList?.getItemLayout?.(nodeIndex);
      const x = Number(layout?.x ?? layout?.[0]);
      const y = Number(layout?.y ?? layout?.[1]);
      if (!Number.isFinite(x) || !Number.isFinite(y)) return;

      const rect = graphChartRef.value?.getBoundingClientRect();
      const centerX = rect ? rect.width / 2 : 0;
      const centerY = rect ? rect.height / 2 : 0;

      graphChart.dispatchAction({
        type: 'graphRoam',
        seriesIndex: 0,
        dx: centerX - x,
        dy: centerY - y,
      });
    } catch (err) {
      console.warn('centerGraphOnNodeIndex failed:', err);
    }
  }

  function syncGraphZoomFromChart() {
    if (!graphChart) return;
    const option = graphChart.getOption() as any;
    const rawZoom = option?.series?.[0]?.zoom;
    const zoom = Number(rawZoom);
    if (!Number.isFinite(zoom)) return;
    graphZoomLevel.value = Math.max(GRAPH_MIN_ZOOM, Math.min(GRAPH_MAX_ZOOM, zoom));
  }

  function applyGraphZoom(targetZoom: number) {
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
  }

  function zoomInGraph() {
    applyGraphZoom(graphZoomLevel.value * 1.2);
  }

  function zoomOutGraph() {
    applyGraphZoom(graphZoomLevel.value / 1.2);
  }

  function resetGraphZoom() {
    applyGraphZoom(1);
  }

  async function toggleGraphFullscreen() {
    const container = graphPreviewRef.value;
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
  }

  function focusGraphToEvolutionChanges() {
    const result = latestEvolutionResult.value;
    if (!result || !graphChart) return;

    const nodeIds = result.newNodes
      .map((item) => String(item.id || '').trim())
      .filter(Boolean);
    const edgeIds = result.newEdges
      .map((item) => String(item.id || '').trim())
      .filter(Boolean);
    if (!nodeIds.length && !edgeIds.length) return;

    evolutionHighlightNodeIds.value = new Set(nodeIds);
    evolutionHighlightEdgeIds.value = new Set(edgeIds);
    renderGraph();

    if (focusEvolutionTimer !== null) {
      window.clearTimeout(focusEvolutionTimer);
      focusEvolutionTimer = null;
    }

    focusEvolutionTimer = window.setTimeout(() => {
      if (!graphChart) return;

      graphChart.dispatchAction({ type: 'downplay', seriesIndex: 0 });

      nodeIds.forEach((id) => {
        const nodeIndex = renderedNodeIndexById.get(id);
        if (nodeIndex == null) return;
        graphChart?.dispatchAction({
          type: 'highlight',
          seriesIndex: 0,
          dataIndex: nodeIndex,
        });
      });

      edgeIds.forEach((id) => {
        const edgeIndex = renderedEdgeIndexById.get(id);
        if (edgeIndex == null) return;
        graphChart?.dispatchAction({
          type: 'highlight',
          seriesIndex: 0,
          dataType: 'edge',
          dataIndex: edgeIndex,
        });
      });

      let focusNodeIndex: number | undefined = undefined;
      if (nodeIds.length) {
        focusNodeIndex = renderedNodeIndexById.get(nodeIds[0]);
      } else {
        const fallbackNodeId = String(result.newEdges[0]?.from || result.newEdges[0]?.to || '').trim();
        if (fallbackNodeId) {
          focusNodeIndex = renderedNodeIndexById.get(fallbackNodeId);
        }
      }

      if (focusNodeIndex != null) {
        graphChart.dispatchAction({
          type: 'focusNodeAdjacency',
          seriesIndex: 0,
          dataIndex: focusNodeIndex,
        });
        centerGraphOnNodeIndex(focusNodeIndex);
      }
    }, 180);

    if (clearEvolutionHighlightTimer !== null) {
      window.clearTimeout(clearEvolutionHighlightTimer);
      clearEvolutionHighlightTimer = null;
    }
    clearEvolutionHighlightTimer = window.setTimeout(() => {
      evolutionHighlightNodeIds.value = new Set();
      evolutionHighlightEdgeIds.value = new Set();
      renderGraph();
    }, 10000);
  }

  function handleMockEvent() {
    const eventTitle = ref('');
    const eventContent = ref('');
    const activePresetKey = ref('');

    const applyPresetEvent = (presetKey: string) => {
      const preset = presetMockEvents.find((item) => item.key === presetKey);
      if (!preset) return;
      activePresetKey.value = preset.key;
      eventTitle.value = preset.title;
      eventContent.value = preset.content;
    };

    dialog.info({
      title: '注入突发事件',
      positiveText: '提交事件',
      negativeText: '取消',
      content: () =>
        h('div', { class: 'mock-event-dialog' }, [
          h(
            'div',
            { class: 'mock-event-dialog__tip' },
            '请输入事件标题和事件内容，提交后系统会自动触发增量演进。'
          ),
          h(NInput, {
            value: eventTitle.value,
            placeholder: '请输入事件标题',
            maxlength: 120,
            showCount: true,
            'onUpdate:value': (v: string) => {
              eventTitle.value = v;
            },
          }),
          h(
            'div',
            { class: 'mock-event-dialog__presets' },
            presetMockEvents.map((item) =>
              h(
                NTag,
                {
                  key: item.key,
                  size: 'small',
                  type: activePresetKey.value === item.key ? 'primary' : 'default',
                  round: true,
                  bordered: activePresetKey.value !== item.key,
                  class: 'mock-event-dialog__preset-tag',
                  onClick: () => applyPresetEvent(item.key),
                },
                { default: () => item.key }
              )
            )
          ),
          h(NInput, {
            value: eventContent.value,
            type: 'textarea',
            rows: 6,
            placeholder: '请输入事件正文内容',
            maxlength: 5000,
            showCount: true,
            style: 'margin-top: 8px;',
            'onUpdate:value': (v: string) => {
              eventContent.value = v;
            },
          }),
        ]),
      onPositiveClick: async () => {
        const title = String(eventTitle.value || '').trim();
        const content = String(eventContent.value || '').trim();
        if (!title) {
          message.warning('请先输入事件标题');
          return false;
        }
        if (!content) {
          message.warning('请先输入事件内容');
          return false;
        }

        try {
          message.loading('正在发送突发事件...', { duration: 2000 });
          await injectMockEvent({
            project_id: projectId.value,
            title,
            content,
          });
          message.success('注入成功！系统已捕获新事件并正在后台静默处理，请稍候...', {
            duration: 5000,
          });
        } catch (e: any) {
          message.error(e?.message || '注入失败');
        }
      },
    });
  }
  const completing = ref(false);

  const selected = ref<'node' | 'edge' | null>(null);
  const selectedNode = ref<any>(null);
  const selectedEdge = ref<any>(null);

  const selectedType = computed(() => selected.value);

  const nodeForm = ref({
    id: '',
    value: '',
    type: 0 as 0 | 1,
    key: '',
    properties: {} as Record<string, unknown>,
  });
  const edgeForm = ref({
    id: '',
    from: '',
    to: '',
    value: '',
    eventRel: '',
    properties: {} as Record<string, unknown>,
  });

  type PropertyEntry = { id: number; key: string; value: string };
  let propertyEntrySeed = 0;
  const nodePropertyEntries = ref<PropertyEntry[]>([]);
  const edgePropertyEntries = ref<PropertyEntry[]>([]);

  function createPropertyEntry(key = '', value = ''): PropertyEntry {
    propertyEntrySeed += 1;
    return {
      id: propertyEntrySeed,
      key,
      value,
    };
  }

  function normalizePropertyValue(value: unknown): string {
    if (value == null) return '';
    if (typeof value === 'object') {
      try {
        return JSON.stringify(value);
      } catch {
        return String(value);
      }
    }
    return String(value);
  }

  function setPropertyEntriesFromObject(
    entriesRef: typeof nodePropertyEntries,
    properties: Record<string, unknown> | undefined
  ) {
    const source = properties || {};
    const nextEntries = Object.entries(source).map(([key, value]) =>
      createPropertyEntry(String(key), normalizePropertyValue(value))
    );
    entriesRef.value = nextEntries;
  }

  function collectPropertiesFromEntries(
    entries: PropertyEntry[],
    targetLabel: '节点' | '关系'
  ): Record<string, unknown> | null {
    const result: Record<string, unknown> = {};
    const keySet = new Set<string>();
    for (const item of entries) {
      const key = String(item.key || '').trim();
      const value = String(item.value || '');
      if (!key && !value.trim()) continue;
      if (!key) {
        message.error(`${targetLabel}扩展属性存在空的属性名，请补全后再保存`);
        return null;
      }
      if (keySet.has(key)) {
        message.error(`${targetLabel}扩展属性存在重复属性名：${key}`);
        return null;
      }
      keySet.add(key);
      result[key] = value;
    }
    return result;
  }

  function openPropertyValueDialog(targetType: '节点' | '关系', key: string, value: string) {
    const safeKey = String(key || '').trim() || '未命名属性';
    const safeValue = String(value || '');
    dialog.info({
      title: `${targetType}扩展属性 - ${safeKey}`,
      positiveText: '关闭',
      content: () =>
        h(
          'div',
          {
            style:
              'max-height: 52vh; overflow-y: auto; white-space: pre-wrap; line-height: 1.6; color: #1f2937; background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:10px 12px;',
          },
          safeValue || '-'
        ),
    });
  }

  function addNodePropertyEntry() {
    nodePropertyEntries.value.push(createPropertyEntry());
  }

  function removeNodePropertyEntry(id: number) {
    nodePropertyEntries.value = nodePropertyEntries.value.filter((item) => item.id !== id);
  }

  function addEdgePropertyEntry() {
    edgePropertyEntries.value.push(createPropertyEntry());
  }

  function removeEdgePropertyEntry(id: number) {
    edgePropertyEntries.value = edgePropertyEntries.value.filter((item) => item.id !== id);
  }

  watch(selectedNode, (n) => {
    if (n) {
      nodeForm.value = {
        id: n.id,
        value: n.value || '',
        type: normalizeNodeCategoryFromNode(n),
        key: n.key || '',
        properties: { ...(n.properties || {}) },
      };
      setPropertyEntriesFromObject(nodePropertyEntries, n.properties || {});
    }
  });

  watch(selectedEdge, (e) => {
    if (e) {
      edgeForm.value = {
        id: e.id,
        from: e.from,
        to: e.to,
        value: e.value || '',
        eventRel: e.eventRel || '',
        properties: { ...(e.properties || {}) },
      };
      setPropertyEntriesFromObject(edgePropertyEntries, e.properties || {});
    }
  });

  const hasData = computed(() => nodes.value.length > 0 || edges.value.length > 0);

  const goBack = () => {
    router.push({ name: 'abstract_kg', params: { projectId: projectId.value } });
  };

  async function loadGraph() {
    if (!projectId.value) return;
    loading.value = true;
    try {
      const [nodesRes, edgesRes] = await Promise.all([
        getNodesByProject(projectId.value),
        getEdgesByProject(projectId.value),
      ]);
      if (nodesRes.success && nodesRes.data) {
        nodes.value = nodesRes.data.nodes || [];
      } else {
        nodes.value = [];
      }
      if (edgesRes.success && edgesRes.data) {
        edges.value = edgesRes.data.edges || [];
      } else {
        edges.value = [];
      }
      // hasData 刚变为 true 时图表容器才挂载，同步调用 renderGraph 会导致 ref 为空，必须等 DOM 更新
      await nextTick();
      renderGraph();
      await nextTick();
      scheduleGraphResize();
    } catch (err: any) {
      message.error(err?.message || '加载图谱失败');
    } finally {
      loading.value = false;
    }
  }

  function renderGraph() {
    if (!graphChartRef.value) return;
    if (!graphChart) {
      graphChart = echarts.init(graphChartRef.value);
      graphChart.on('graphroam', syncGraphZoomFromChart);
    }

    const nodeMap = new Map(nodes.value.map((n: any) => [n.id, n]));

    const degreeMap = new Map<string, number>();
    edges.value.forEach((e: any) => {
      const source = String(e.from || '');
      const target = String(e.to || '');
      if (source) degreeMap.set(source, (degreeMap.get(source) || 0) + 1);
      if (target) degreeMap.set(target, (degreeMap.get(target) || 0) + 1);
    });

    const visualCategoryNames = sortVisualCategoryNames(
      Array.from(new Set(nodes.value.map((n: any) => resolveNodeVisualCategory(n))))
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

    const data = nodes.value.map((n: any) => {
      const nodeId = String(n.id || '');
      const isEvolutionHighlight = evolutionHighlightNodeIds.value.has(nodeId);
      const basicCategory = normalizeNodeCategoryFromNode(n);
      const categoryName = resolveNodeVisualCategory(n);
      const degree = degreeMap.get(nodeId) || 0;
      const baseSize = basicCategory === 1 ? 44 : 32;
      const symbolSize = Math.min(
        70,
        baseSize + Math.sqrt(degree) * 3.2 + (isEvolutionHighlight ? 6 : 0)
      );

      return {
        id: nodeId,
        name: normalizeNodeDisplayName(n),
        category: categoryIndexMap.get(categoryName) ?? 0,
        categoryName,
        value: n.key || '',
        key: n.key || '',
        rawValue: n.value || n.id,
        properties: n.properties || {},
        symbolSize,
        degree,
        itemStyle: {
          color: getNodeVisualColor(categoryName),
          borderColor: isEvolutionHighlight ? '#f59e0b' : '#ffffff',
          borderWidth: isEvolutionHighlight ? 2.8 : 1.5,
          shadowBlur: isEvolutionHighlight ? 18 : 10,
          shadowColor: isEvolutionHighlight ? 'rgba(245, 158, 11, 0.48)' : 'rgba(15, 23, 42, 0.18)',
        },
      };
    });

    renderedNodeIndexById = new Map<string, number>(
      data.map((item: any, index: number) => [String(item.id), index])
    );

    const links = edges.value.map((e: any) => {
      const edgeId = String(e.id || edgeIdentity(e));
      const isEvolutionHighlight = evolutionHighlightEdgeIds.value.has(edgeId);
      const fromNode = nodeMap.get(e.from);
      const toNode = nodeMap.get(e.to);
      const displayLabel = normalizeEdgeDisplayLabel(e, fromNode, toNode);
      return {
        id: edgeId,
        source: e.from,
        target: e.to,
        value: e.value || e.type || '',
        eventRel: e.eventRel || '',
        type: e.type || '',
        isEvolutionHighlight,
        displayLabel,
        label: {
          show: false,
          formatter: displayLabel,
          fontSize: 11,
          color: '#1f2937',
          backgroundColor: 'rgba(255, 255, 255, 0.9)',
          borderRadius: 3,
          padding: [2, 6],
        },
        lineStyle: {
          width: isEvolutionHighlight ? 2.8 : 1.4,
          curveness: 0.12,
          color: isEvolutionHighlight ? '#f59e0b' : EDGE_COLOR,
          opacity: isEvolutionHighlight ? 0.95 : 0.6,
        },
      };
    });

    renderedEdgeIndexById = new Map<string, number>(
      links.map((item: any, index: number) => [String(item.id), index])
    );

    const nodeCount = data.length;
    const repulsion = nodeCount <= 30 ? 520 : nodeCount <= 90 ? 360 : 250;
    const edgeLength = nodeCount <= 30 ? [120, 220] : nodeCount <= 90 ? [90, 180] : [60, 130];

    graphChart.setOption({
      backgroundColor: 'transparent',
      tooltip: {
        backgroundColor: 'rgba(255, 255, 255, 0.96)',
        borderWidth: 1,
        borderColor: 'rgba(148, 163, 184, 0.45)',
        textStyle: { color: '#0f172a', fontSize: 12 },
        extraCssText: 'box-shadow:0 10px 20px rgba(15, 23, 42, 0.12);',
        formatter: (params: any) => {
          if (params.dataType === 'edge') {
            return `关系：${params.data?.displayLabel || params.data?.value || '-'}<br/>起点：${params.data?.source || '-'}<br/>终点：${params.data?.target || '-'}`;
          }
          const d = params.data || {};
          return `节点：${d.name || '-'}<br/>类别：${d.categoryName || '-'}<br/>Key：${d.key || '-'}<br/>连接数：${d.degree || 0}`;
        },
      },
      legend: [
        {
          data: visualCategoryNames,
          top: 4,
          left: 'center',
          itemWidth: 12,
          itemHeight: 12,
          textStyle: {
            color: '#334155',
            fontSize: 12,
          },
          selectedMode: true,
        },
      ],
      series: [
        {
          id: GRAPH_SERIES_ID,
          type: 'graph',
          layout: 'force',
          roam: true,
          zoom: 1,
          draggable: true,
          data,
          links,
          categories,
          force: {
            repulsion,
            edgeLength,
            gravity: 0.08,
            friction: 0.15,
            layoutAnimation: true,
          },
          label: {
            show: true,
            position: 'right',
            fontSize: 12,
            color: '#334155',
            formatter: (params: any) => {
              const name = String(params.data?.name || '-');
              return name.length > 14 ? `${name.slice(0, 13)}…` : name;
            },
          },
          labelLayout: {
            hideOverlap: true,
          },
          edgeSymbol: ['none', 'arrow'],
          edgeSymbolSize: [3, 10],
          lineStyle: {
            color: 'source',
            opacity: 0.6,
            width: 1.2,
          },
          emphasis: {
            focus: 'adjacency',
            scale: true,
            lineStyle: {
              width: 2.4,
              opacity: 0.95,
            },
            label: {
              show: true,
              fontSize: 13,
              fontWeight: 600,
              color: '#0f172a',
            },
            edgeLabel: {
              show: true,
            },
          },
          blur: {
            itemStyle: {
              opacity: 0.18,
            },
            lineStyle: {
              opacity: 0.08,
            },
            label: {
              opacity: 0.08,
            },
          },
          select: {
            itemStyle: {
              borderWidth: 2.3,
              borderColor: '#0f172a',
            },
          },
          selectedMode: 'single',
          animationDurationUpdate: 450,
          animationEasingUpdate: 'quarticOut',
          edgeLabel: {
            show: false,
            color: '#1f2937',
            fontSize: 11,
            formatter: (params: any) => params.data?.displayLabel || '',
            backgroundColor: 'rgba(255, 255, 255, 0.9)',
            borderRadius: 3,
            padding: [2, 5],
          },
        },
      ],
      graphic: [
        {
          type: 'text',
          left: 16,
          top: 14,
          style: {
            text: '点击节点可聚焦邻接关系；点击边可在右侧编辑属性',
            fill: 'rgba(71, 85, 105, 0.9)',
            font: '12px sans-serif',
          },
          silent: true,
        },
      ],
    }, true);
    graphZoomLevel.value = 1;

    graphChart.off('click');
    graphChart.on('click', (params: any) => {
      if (!params || !params.dataType || !params.data) return;
      
      if (params.dataType === 'node') {
        const n = nodes.value.find((x: any) => x.id === params.data.id);
        if (n) {
          selected.value = 'node';
          selectedNode.value = n;
          selectedEdge.value = null;
        }
      } else if (params.dataType === 'edge') {
        const linkId = params.data?.id;
        const e = edges.value.find((x: any) => x.id === linkId);
        if (!e && params.data?.source != null) {
          const from = typeof params.data.source === 'object' ? params.data.source : params.data.source;
          const to = typeof params.data.target === 'object' ? params.data.target : params.data.target;
          const val = params.data?.value || '';
          const found = edges.value.find(
            (x: any) => x.from === from && x.to === to && (x.value === val || !val)
          );
          if (found) {
            selected.value = 'edge';
            selectedEdge.value = found;
            selectedNode.value = null;
          }
        } else if (e) {
          selected.value = 'edge';
          selectedEdge.value = e;
          selectedNode.value = null;
        }
      }
    });
  }

  const handleGraphResize = () => {
    normalizeFormPanelWidth();
    graphChart?.resize();
  };

  function normalizeFormPanelWidth() {
    const container = editorLayoutRef.value;
    if (!container) return;
    const containerWidth = container.getBoundingClientRect().width;
    const maxFormWidth = Math.max(
      MIN_FORM_PANEL_WIDTH,
      containerWidth - MIN_GRAPH_PANEL_WIDTH - PANEL_SPLITTER_WIDTH
    );
    formPanelWidth.value = Math.max(MIN_FORM_PANEL_WIDTH, Math.min(formPanelWidth.value, maxFormWidth));
  }

  function setFormPanelWidthByClientX(clientX: number) {
    const container = editorLayoutRef.value;
    if (!container) return;
    const rect = container.getBoundingClientRect();
    const nextWidth = rect.right - clientX;
    const maxFormWidth = Math.max(
      MIN_FORM_PANEL_WIDTH,
      rect.width - MIN_GRAPH_PANEL_WIDTH - PANEL_SPLITTER_WIDTH
    );
    formPanelWidth.value = Math.max(MIN_FORM_PANEL_WIDTH, Math.min(nextWidth, maxFormWidth));
  }

  const onPanelResizeMouseMove = (event: MouseEvent) => {
    if (!isResizingPanels.value) return;
    setFormPanelWidthByClientX(event.clientX);
    scheduleGraphResize();
  };

  const stopResizePanels = () => {
    if (!isResizingPanels.value) return;
    isResizingPanels.value = false;
    document.removeEventListener('mousemove', onPanelResizeMouseMove);
    document.removeEventListener('mouseup', stopResizePanels);
    scheduleGraphResize();
  };

  function startResizePanels(event: MouseEvent) {
    if (!editorLayoutRef.value) return;
    isResizingPanels.value = true;
    setFormPanelWidthByClientX(event.clientX);
    document.addEventListener('mousemove', onPanelResizeMouseMove);
    document.addEventListener('mouseup', stopResizePanels);
  }

  const scheduleGraphResize = () => {
    // Let flex/layout settle first so ECharts receives the final container size.
    window.requestAnimationFrame(() => {
      graphChart?.resize();
      window.setTimeout(() => graphChart?.resize(), 40);
    });
  };

  const handleFullscreenChange = () => {
    isGraphFullscreen.value = document.fullscreenElement === graphPreviewRef.value;
    scheduleGraphResize();
  };

  async function saveNode() {
    const props = collectPropertiesFromEntries(nodePropertyEntries.value, '节点');
    if (!props) {
      return;
    }
    saving.value = true;
    try {
      const res = await updateNode({
        project_id: projectId.value,
        node_id: nodeForm.value.id,
        value: nodeForm.value.value,
        type: nodeForm.value.type,
        key: nodeForm.value.key,
        properties: props,
      });
      if (res.success) {
        message.success('保存成功');
        const idx = nodes.value.findIndex((n: any) => n.id === nodeForm.value.id);
        if (idx >= 0) {
          nodes.value[idx] = {
            ...nodes.value[idx],
            value: nodeForm.value.value,
            type: nodeForm.value.type,
            key: nodeForm.value.key,
            properties: props,
          };
        }
        renderGraph();
      } else {
        message.error(res.message || '保存失败');
      }
    } catch (err: any) {
      message.error(err?.message || '保存失败');
    } finally {
      saving.value = false;
    }
  }

  async function runAttributeCompletion(type: 'node' | 'edge') {
    const id = type === 'node' ? nodeForm.value.id : edgeForm.value.id;
    if (!id) return;
    completing.value = true;
    try {
      const res = await attributeCompletion({
        project_id: projectId.value,
        target_type: type,
        target_id: id,
        apply_update: false,
      });
      if (res.success && res.data?.completed_properties) {
        const props = res.data.completed_properties;
        if (type === 'node') {
          nodeForm.value.properties = props;
          setPropertyEntriesFromObject(nodePropertyEntries, props);
        } else {
          edgeForm.value.properties = props;
          setPropertyEntriesFromObject(edgePropertyEntries, props);
        }
        message.success('属性补全完成，请确认后保存');
      } else {
        message.error(res.message || '属性补全失败');
      }
    } catch (err: any) {
      message.error(err?.message || '属性补全失败');
    } finally {
      completing.value = false;
    }
  }

  async function saveEdge() {
    const props = collectPropertiesFromEntries(edgePropertyEntries.value, '关系');
    if (!props) {
      return;
    }
    saving.value = true;
    try {
      const res = await updateEdge({
        project_id: projectId.value,
        edge_id: edgeForm.value.id,
        value: edgeForm.value.value,
        eventRel: edgeForm.value.eventRel,
        properties: props,
      });
      if (res.success) {
        message.success('保存成功');
        const idx = edges.value.findIndex((e: any) => e.id === edgeForm.value.id);
        if (idx >= 0) {
          edges.value[idx] = {
            ...edges.value[idx],
            value: edgeForm.value.value,
            eventRel: edgeForm.value.eventRel,
            properties: props,
          };
        }
        renderGraph();
      } else {
        message.error(res.message || '保存失败');
      }
    } catch (err: any) {
      message.error(err?.message || '保存失败');
    } finally {
      saving.value = false;
    }
  }

  function handleDeleteNode() {
    const nodeId = String(nodeForm.value.id || '').trim();
    if (!nodeId) {
      message.warning('请先选中要删除的节点');
      return;
    }

    dialog.warning({
      title: '确认删除节点',
      content: '删除节点会同时删除与该节点相连的所有关系。此操作不可撤销，是否继续？',
      positiveText: '确认删除',
      negativeText: '取消',
      onPositiveClick: async () => {
        deleting.value = true;
        try {
          const res = await deleteNode({ project_id: projectId.value, node_id: nodeId });
          if (!res.success) {
            message.error(res.message || '删除节点失败');
            return;
          }

          nodes.value = nodes.value.filter((n: any) => String(n.id) !== nodeId);
          edges.value = edges.value.filter(
            (e: any) => String(e.from) !== nodeId && String(e.to) !== nodeId
          );
          selected.value = null;
          selectedNode.value = null;
          selectedEdge.value = null;
          renderGraph();

          const removedEdges = Number(res.data?.deleted_related_edges_count || 0);
          const isolated = (res.data?.isolated_node_ids || []) as string[];
          message.success(`节点删除成功（已同步删除 ${removedEdges} 条关联关系）`);
          if (isolated.length) {
            message.info(`删除后有 ${isolated.length} 个节点成为孤立节点，可按需继续清理。`);
          }
        } catch (err: any) {
          message.error(err?.message || '删除节点失败');
        } finally {
          deleting.value = false;
        }
      },
    });
  }

  function handleDeleteEdge() {
    const edgeId = String(edgeForm.value.id || '').trim();
    if (!edgeId) {
      message.warning('请先选中要删除的关系');
      return;
    }

    dialog.warning({
      title: '确认删除关系',
      content: '删除关系不会自动删除两端节点。此操作不可撤销，是否继续？',
      positiveText: '确认删除',
      negativeText: '取消',
      onPositiveClick: async () => {
        deleting.value = true;
        try {
          const res = await deleteEdge({ project_id: projectId.value, edge_id: edgeId });
          if (!res.success) {
            message.error(res.message || '删除关系失败');
            return;
          }

          edges.value = edges.value.filter((e: any) => String(e.id) !== edgeId);
          selected.value = null;
          selectedNode.value = null;
          selectedEdge.value = null;
          renderGraph();

          const isolated = (res.data?.isolated_node_ids || []) as string[];
          message.success('关系删除成功');
          if (isolated.length) {
            message.info(`删除后有 ${isolated.length} 个节点成为孤立节点，可按需继续清理。`);
          }
        } catch (err: any) {
          message.error(err?.message || '删除关系失败');
        } finally {
          deleting.value = false;
        }
      },
    });
  }

  onMounted(() => {
    loadGraph();
    normalizeFormPanelWidth();
    window.addEventListener('resize', handleGraphResize);
    document.addEventListener('fullscreenchange', handleFullscreenChange);

    if (typeof ResizeObserver !== 'undefined') {
      graphResizeObserver = new ResizeObserver(() => {
        scheduleGraphResize();
      });
      if (graphPreviewRef.value) {
        graphResizeObserver.observe(graphPreviewRef.value);
      }
      if (graphChartRef.value) {
        graphResizeObserver.observe(graphChartRef.value);
      }
    }

    scheduleGraphResize();
    pollingTimer = setInterval(pollStatus, 5000);
  });

  onUnmounted(() => {
    stopResizePanels();
    window.removeEventListener('resize', handleGraphResize);
    document.removeEventListener('fullscreenchange', handleFullscreenChange);
    graphResizeObserver?.disconnect();
    graphResizeObserver = null;
    graphChart?.dispose();
    graphChart = null;
    if (pollingTimer) clearInterval(pollingTimer);
    if (clearEvolutionHighlightTimer !== null) {
      window.clearTimeout(clearEvolutionHighlightTimer);
      clearEvolutionHighlightTimer = null;
    }
    if (focusEvolutionTimer !== null) {
      window.clearTimeout(focusEvolutionTimer);
      focusEvolutionTimer = null;
    }
  });
</script>

<style scoped lang="scss">
  .graph-editor-page {
    min-height: 100%;
    padding: 20px;
    background: linear-gradient(135deg, #f5f7fb 0%, #edf5ff 50%, #f5fbff 100%);
    box-sizing: border-box;
  }

  .page-header {
    margin-bottom: 12px;
  }

  .main-card {
    border-radius: 18px;
    box-shadow: 0 18px 45px rgba(15, 23, 42, 0.06);
  }

  .editor-layout {
    display: flex;
    gap: 0;
    min-height: 500px;
    height: clamp(520px, calc(100vh - 220px), 860px);
  }

  .editor-layout.is-resizing,
  .editor-layout.is-resizing * {
    cursor: col-resize !important;
    user-select: none;
  }

  .graph-panel,
  .form-panel {
    display: flex;
    flex-direction: column;
    border-radius: 8px;
    background: #fafafa;
  }

  .graph-panel {
    flex: 1;
    min-width: 0;
    min-height: 0;
  }

  .form-panel {
    flex-shrink: 0;
    height: 100%;
    max-height: none;
    overflow-y: auto;
    margin-left: 10px;
  }

  .panel-splitter {
    width: 12px;
    height: calc(100% - 16px);
    margin: 8px 0;
    border-radius: 8px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: col-resize;
    transition: background-color 0.2s ease;
    background: transparent;
  }

  .panel-splitter:hover {
    background: rgba(148, 163, 184, 0.14);
  }

  .panel-splitter__grip {
    width: 4px;
    height: 48px;
    border-radius: 99px;
    background: linear-gradient(180deg, #cbd5e1 0%, #94a3b8 100%);
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.55);
  }

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    font-weight: 600;
    font-size: 14px;
  }

  .graph-chart {
    flex: 1;
    min-height: 0;
    height: 100%;
    margin: 0;
    border: 1px solid #dbe3ef;
    border-radius: 12px;
    background:
      linear-gradient(rgba(148, 163, 184, 0.15) 1px, transparent 1px),
      linear-gradient(90deg, rgba(148, 163, 184, 0.15) 1px, transparent 1px),
      radial-gradient(circle at 14% 14%, #f8fbff 0%, #ffffff 56%, #f5f9ff 100%);
    background-size:
      24px 24px,
      24px 24px,
      auto;
    box-shadow:
      inset 0 0 0 1px rgba(255, 255, 255, 0.85),
      0 12px 26px rgba(15, 23, 42, 0.08);
  }

  .graph-preview-shell {
    position: relative;
    margin: 0 12px 12px;
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }

  .graph-overlay-tools {
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

  .graph-preview-shell:hover .graph-overlay-tools,
  .graph-preview-shell:focus-within .graph-overlay-tools,
  .graph-preview-shell:fullscreen .graph-overlay-tools {
    opacity: 1;
    transform: translateY(0);
    pointer-events: auto;
  }

  .graph-overlay-tools :deep(.n-button) {
    box-shadow: 0 8px 22px rgba(15, 23, 42, 0.16);
    border-color: rgba(148, 163, 184, 0.4);
    background: rgba(255, 255, 255, 0.96);
    backdrop-filter: blur(6px);
  }

  .graph-zoom-indicator {
    position: absolute;
    left: 14px;
    top: 12px;
    z-index: 5;
    padding: 2px 8px;
    border-radius: 8px;
    font-size: 12px;
    color: #475569;
    background: rgba(255, 255, 255, 0.86);
    border: 1px solid rgba(148, 163, 184, 0.26);
    pointer-events: none;
  }

  .graph-preview-shell:fullscreen {
    background: #f8fbff;
    padding: 14px;
    box-sizing: border-box;
    margin: 0;
    overflow: auto;
  }

  .graph-preview-shell:fullscreen .graph-chart {
    height: calc(100vh - 96px);
    min-height: 420px;
  }

  .empty-tip {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 300px;
  }

  .form-panel :deep(.n-form) {
    padding: 0 16px 16px;
  }

  .evo-summary-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 14px;
  }

  .evo-summary-item {
    border: 1px solid #dbe7f7;
    border-radius: 10px;
    padding: 10px 12px;
    background: linear-gradient(160deg, #f7fbff 0%, #eef6ff 100%);
  }

  .evo-summary-label {
    font-size: 12px;
    color: #64748b;
    margin-bottom: 4px;
  }

  .evo-summary-value {
    font-size: 18px;
    font-weight: 700;
    color: #0f172a;
  }

  .evo-time {
    font-size: 13px;
    font-weight: 600;
    line-height: 1.4;
  }

  .evo-section {
    margin-top: 14px;
  }

  .evo-section-title {
    font-size: 13px;
    font-weight: 700;
    color: #334155;
    margin-bottom: 8px;
  }

  .evo-empty {
    color: #94a3b8;
    font-size: 12px;
    padding: 8px 0;
  }

  .evo-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-height: 220px;
    overflow-y: auto;
    padding-right: 2px;
  }

  .evo-list-item {
    border-radius: 10px;
    padding: 8px 10px;
    border: 1px solid #dbe7f7;
    background: #f8fbff;
  }

  .evo-list-item--node {
    border-left: 4px solid #0ea5e9;
  }

  .evo-list-item--edge {
    border-left: 4px solid #10b981;
  }

  .evo-item-main {
    font-size: 13px;
    font-weight: 600;
    color: #1e293b;
    line-height: 1.4;
  }

  .evo-item-sub {
    margin-top: 2px;
    font-size: 11px;
    color: #64748b;
    word-break: break-all;
  }

  .mock-event-dialog {
    width: 100%;
  }

  .mock-event-dialog__tip {
    margin-bottom: 10px;
    font-size: 12px;
    color: #64748b;
    line-height: 1.5;
  }

  .mock-event-dialog__presets {
    margin-top: 10px;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .mock-event-dialog__preset-tag {
    cursor: pointer;
    user-select: none;
  }

  .property-editor {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .property-editor__list {
    max-height: 220px;
    overflow-y: auto;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: #f8fafc;
    padding: 8px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .property-editor__row {
    display: grid;
    grid-template-columns: minmax(110px, 34%) 1fr auto auto;
    gap: 8px;
    align-items: center;
  }

  .property-editor__key {
    min-width: 0;
  }

  .property-editor__value {
    min-width: 0;
  }

  .property-editor__actions {
    display: flex;
    justify-content: flex-start;
  }

  .property-editor__empty {
    padding: 8px;
    color: #94a3b8;
    font-size: 12px;
  }

  .property-editor__remove {
    width: 26px;
    height: 26px;
    min-width: 26px;
  }

  .property-editor__view {
    width: 26px;
    height: 26px;
    min-width: 26px;
  }

  .property-editor__remove :deep(svg) {
    font-size: 14px;
  }

  .property-editor__view :deep(svg) {
    font-size: 14px;
  }
</style>
