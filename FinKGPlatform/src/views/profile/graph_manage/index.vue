<template>
  <div class="graph-manage-page">
    <n-card :bordered="false" class="graph-manage-card">
      <div class="page-header">
        <div>
          <h2>图谱管理</h2>
          <p>管理员可查看全局图谱项目信息与图谱规模统计。</p>
        </div>
        <n-tag type="info" round>共 {{ pagination.itemCount }} 个项目</n-tag>
      </div>

      <div class="toolbar">
        <n-space align="center" :size="12" wrap>
          <n-input
            v-model:value="keyword"
            clearable
            placeholder="搜索项目名称/描述/创建人"
            style="width: 320px"
            @keyup.enter="handleSearch"
          />
          <n-button type="primary" :loading="loading" @click="handleSearch">
            <template #icon>
              <n-icon><SearchOutline /></n-icon>
            </template>
            搜索
          </n-button>
          <n-button :loading="loading" @click="refreshList">
            <template #icon>
              <n-icon><RefreshOutline /></n-icon>
            </template>
            刷新
          </n-button>
        </n-space>
      </div>

      <n-data-table
        remote
        class="graph-manage-table"
        :columns="columns"
        :data="tableData"
        :loading="loading"
        :pagination="pagination"
        :row-key="rowKey"
        :bordered="false"
        :single-line="false"
        @update:page="handlePageChange"
        @update:page-size="handlePageSizeChange"
      />
    </n-card>

    <n-modal
      v-model:show="workflowReportModalVisible"
      preset="card"
      style="width: 860px; max-width: 96vw"
      title="图谱构建报告"
      :bordered="false"
      :mask-closable="true"
    >
      <div class="workflow-report-modal-body">
        <n-space vertical size="large" style="width: 100%">
          <n-spin :show="loadingWorkflowReport" size="small">
            <template v-if="latestWorkflowMeta">
              <n-descriptions label-placement="left" :column="1" size="small" bordered>
                <n-descriptions-item label="项目名称">
                  <n-text>{{ activeReportProjectName || '-' }}</n-text>
                </n-descriptions-item>
                <n-descriptions-item label="run_id">
                  <n-text>{{ String(latestWorkflowMeta.run_id || activeWorkflowRunId || '-') }}</n-text>
                </n-descriptions-item>
                <n-descriptions-item label="来源">
                  <n-text>
                    {{ activeWorkflowReportSource }}
                  </n-text>
                </n-descriptions-item>
              </n-descriptions>

              <div v-if="qualityReportMetrics.length" class="quality-report-card">
                <div class="quality-report-card__header">
                  <h4>质量报告核心指标</h4>
                  <span class="quality-report-card__hint">来源：workflow_meta.quality_report</span>
                </div>
                <div class="quality-report-grid">
                  <div
                    v-for="item in qualityReportMetrics"
                    :key="`detail-${item.key}`"
                    class="quality-report-grid__item"
                  >
                    <div class="quality-report-grid__label">{{ item.label }}</div>
                    <div class="quality-report-grid__value">{{ item.value }}</div>
                  </div>
                </div>
              </div>

              <n-alert v-else type="warning" closable>
                当前 run 没有 quality_report 字段，建议重跑一次图谱构建流程以生成完整报告。
              </n-alert>

              <n-card size="small" title="workflow_meta 结构化详情" :bordered="true">
                <n-space vertical size="small" style="width: 100%">
                  <n-empty
                    v-if="!workflowMetaFormSections.length"
                    description="当前 workflow_meta 暂无可结构化展示字段"
                  />
                  <n-card
                    v-for="section in workflowMetaFormSections"
                    :key="section.key"
                    size="small"
                    :title="section.title"
                    :bordered="true"
                    class="workflow-form-section"
                  >
                    <n-descriptions label-placement="left" :column="1" size="small" bordered>
                      <n-descriptions-item
                        v-for="item in section.items"
                        :key="`${section.key}-${item.label}`"
                        :label="item.label"
                      >
                        <n-text class="workflow-form-value">{{ item.value }}</n-text>
                      </n-descriptions-item>
                    </n-descriptions>
                  </n-card>

                  <details class="workflow-raw-toggle">
                    <summary>查看原始 JSON（调试）</summary>
                    <n-scrollbar style="max-height: 320px; margin-top: 8px">
                      <pre class="workflow-report-json">{{ prettyJson(latestWorkflowMeta) }}</pre>
                    </n-scrollbar>
                  </details>
                </n-space>
              </n-card>
            </template>
            <n-empty
              v-else
              description="暂无可查看的构建报告，请先执行图谱构建后重试。"
            />
          </n-spin>
        </n-space>
      </div>
      <template #footer>
        <n-space justify="end">
          <n-button @click="workflowReportModalVisible = false">关闭</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
  import { computed, h, onMounted, reactive, ref } from 'vue';
  import type { DataTableColumns } from 'naive-ui';
  import { NButton, NTag } from 'naive-ui';
  import { SearchOutline, RefreshOutline } from '@vicons/ionicons5';
  import { getProjectList, type ProjectItem } from '@/api/project/project';
  import {
    getEdgesByProject,
    getExtractionHistoryList,
    getNodesByProject,
    getWorkflowReportByRun,
    type WorkflowMeta,
  } from '@/api/kg/extract';
  import { useUserStore } from '@/store/modules/user';
  import { useMessage } from 'naive-ui';

  interface GraphManageRow {
    id: string;
    project_name: string;
    project_desc: string;
    creator: string;
    create_time: string;
    nodes_count: number;
    edges_count: number;
  }

  const userStore = useUserStore();
  const message = useMessage();

  const loading = ref(false);
  const keyword = ref('');
  const tableData = ref<GraphManageRow[]>([]);
  const loadingReportProjectId = ref('');
  const workflowReportModalVisible = ref(false);
  const loadingWorkflowReport = ref(false);
  const activeWorkflowRunId = ref('');
  const activeWorkflowReportSource = ref('历史任务回放');
  const activeReportProjectName = ref('');
  const latestWorkflowMeta = ref<WorkflowMeta | null>(null);

  interface QualityReport {
    grade?: string;
    overall_score?: number | string;
    node_property_fill_rate?: number | string;
    edge_property_fill_rate?: number | string;
    semantic_relation_ratio?: number | string;
    conflict_count?: number | string;
  }

  interface WorkflowMetaFormItem {
    label: string;
    value: string;
  }

  interface WorkflowMetaFormSection {
    key: string;
    title: string;
    items: WorkflowMetaFormItem[];
  }

  const latestQualityReport = computed<QualityReport | null>(() =>
    normalizeQualityReport(latestWorkflowMeta.value?.quality_report)
  );

  const pagination = reactive({
    page: 1,
    pageSize: 10,
    itemCount: 0,
    pageSizes: [10, 20, 50],
    showSizePicker: true,
  });

  const rowKey = (row: GraphManageRow) => row.id;

  function toNumberSafe(value: unknown): number | null {
    if (typeof value === 'number' && Number.isFinite(value)) return value;
    if (typeof value === 'string' && value.trim()) {
      const n = Number(value);
      return Number.isFinite(n) ? n : null;
    }
    return null;
  }

  function normalizeQualityReport(raw: unknown): QualityReport | null {
    if (!raw || typeof raw !== 'object') return null;
    const q = raw as Record<string, unknown>;
    const stats =
      q.stats && typeof q.stats === 'object' ? (q.stats as Record<string, unknown>) : null;
    const report: QualityReport = {
      grade: typeof q.grade === 'string' ? q.grade : undefined,
      overall_score: q.overall_score as number | string | undefined,
      node_property_fill_rate: q.node_property_fill_rate as number | string | undefined,
      edge_property_fill_rate: q.edge_property_fill_rate as number | string | undefined,
      semantic_relation_ratio: q.semantic_relation_ratio as number | string | undefined,
      conflict_count: (q.conflict_count ?? stats?.conflict_count) as number | string | undefined,
    };
    const hasAny = [
      report.grade,
      report.overall_score,
      report.node_property_fill_rate,
      report.edge_property_fill_rate,
      report.semantic_relation_ratio,
      report.conflict_count,
    ].some((v) => v !== undefined && v !== null && String(v).trim() !== '');
    return hasAny ? report : null;
  }

  function formatQualityValue(key: string, value: unknown): string {
    if (value === undefined || value === null || String(value).trim() === '') return '-';
    if (key === 'grade') return String(value);
    const n = toNumberSafe(value);
    if (n === null) return String(value);
    if (key === 'conflict_count') return `${Math.round(n)}`;
    if (n >= 0 && n <= 1) return `${(n * 100).toFixed(1)}%`;
    return `${n}`;
  }

  function getByPath(source: Record<string, any>, path: string): unknown {
    if (!path) return undefined;
    return path.split('.').reduce((acc: any, key) => {
      if (acc === undefined || acc === null) return undefined;
      if (key === 'length' && (Array.isArray(acc) || typeof acc === 'string')) {
        return acc.length;
      }
      return acc[key];
    }, source);
  }

  function formatWorkflowFieldValue(value: unknown): string {
    if (value === undefined || value === null) return '-';
    if (typeof value === 'boolean') return value ? '是' : '否';
    if (typeof value === 'number') {
      if (!Number.isFinite(value)) return '-';
      if (Number.isInteger(value)) return `${value}`;
      return value.toFixed(4).replace(/0+$/, '').replace(/\.$/, '');
    }
    if (Array.isArray(value)) {
      if (!value.length) return '0';
      return value.map((x) => String(x ?? '-')).join(', ');
    }
    const text = String(value).trim();
    return text || '-';
  }

  function formatPercentFromRatio(value: unknown): string {
    const n = toNumberSafe(value);
    if (n === null) return '-';
    if (n >= 0 && n <= 1) return `${(n * 100).toFixed(1)}%`;
    return `${n.toFixed(1)}%`;
  }

  function buildWorkflowMetaSection(
    key: string,
    title: string,
    fields: Array<{ label: string; path: string; formatter?: (value: unknown) => string }>,
    wm: Record<string, any>
  ): WorkflowMetaFormSection {
    const items = fields
      .map((field) => {
        const raw = getByPath(wm, field.path);
        const value = field.formatter ? field.formatter(raw) : formatWorkflowFieldValue(raw);
        return { label: field.label, value };
      })
      .filter((item) => item.value !== '-');

    return { key, title, items };
  }

  const qualityReportMetrics = computed(() => {
    const q = latestQualityReport.value;
    if (!q) return [] as Array<{ key: string; label: string; value: string }>;
    return [
      { key: 'grade', label: '等级', value: formatQualityValue('grade', q.grade) },
      {
        key: 'overall_score',
        label: '综合得分',
        value: formatQualityValue('overall_score', q.overall_score),
      },
      {
        key: 'node_property_fill_rate',
        label: '节点属性填充率',
        value: formatQualityValue('node_property_fill_rate', q.node_property_fill_rate),
      },
      {
        key: 'edge_property_fill_rate',
        label: '边属性填充率',
        value: formatQualityValue('edge_property_fill_rate', q.edge_property_fill_rate),
      },
      {
        key: 'semantic_relation_ratio',
        label: '语义关系占比',
        value: formatQualityValue('semantic_relation_ratio', q.semantic_relation_ratio),
      },
      {
        key: 'conflict_count',
        label: '冲突数',
        value: formatQualityValue('conflict_count', q.conflict_count),
      },
    ];
  });

  const workflowMetaFormSections = computed<WorkflowMetaFormSection[]>(() => {
    const wm = (latestWorkflowMeta.value || {}) as Record<string, any>;
    if (!wm || typeof wm !== 'object') return [];

    const sections: WorkflowMetaFormSection[] = [
      buildWorkflowMetaSection(
        'build-plan',
        '构建计划',
        [
          { label: '构建模式', path: 'build_plan.mode' },
          { label: '持久化策略', path: 'build_plan.persistence_mode' },
          { label: '样本数量', path: 'build_plan.sample_count' },
          { label: '批处理大小', path: 'build_plan.sample_batch_size' },
        ],
        wm
      ),
      buildWorkflowMetaSection(
        'quality-score',
        '质量评分',
        [
          { label: '综合得分', path: 'quality_score.overall_score' },
          {
            label: '覆盖度',
            path: 'quality_score.dimensions.coverage',
            formatter: formatPercentFromRatio,
          },
          {
            label: '一致性',
            path: 'quality_score.dimensions.consistency',
            formatter: formatPercentFromRatio,
          },
          {
            label: '时效性',
            path: 'quality_score.dimensions.freshness',
            formatter: formatPercentFromRatio,
          },
          {
            label: '结构完整性',
            path: 'quality_score.dimensions.structural',
            formatter: formatPercentFromRatio,
          },
          { label: '节点数', path: 'quality_score.metrics.node_count' },
          { label: '关系数', path: 'quality_score.metrics.edge_count' },
          { label: '样本数', path: 'quality_score.metrics.sample_count' },
          { label: '冲突数', path: 'quality_score.metrics.conflict_count' },
        ],
        wm
      ),
      buildWorkflowMetaSection(
        'run-flags',
        '运行状态',
        [
          { label: '需要陈旧清理', path: 'needs_stale_cleanup' },
          { label: '已执行陈旧清理', path: 'stale_cleanup_executed' },
          { label: '已应用冲突缓解', path: 'conflict_mitigation_applied' },
        ],
        wm
      ),
    ];

    return sections.filter((section) => section.items.length > 0);
  });

  const prettyJson = (obj: unknown) => {
    try {
      return JSON.stringify(obj, null, 2);
    } catch {
      return String(obj || '-');
    }
  };

  const columns = computed<DataTableColumns<GraphManageRow>>(() => [
    {
      title: '项目名称',
      key: 'project_name',
      minWidth: 180,
      ellipsis: { tooltip: true },
    },
    {
      title: '项目描述',
      key: 'project_desc',
      minWidth: 260,
      ellipsis: { tooltip: true },
      render(row) {
        return row.project_desc || '-';
      },
    },
    {
      title: '创建人',
      key: 'creator',
      width: 130,
      render(row) {
        return row.creator || '-';
      },
    },
    {
      title: '创建时间',
      key: 'create_time',
      width: 180,
      render(row) {
        return row.create_time || '-';
      },
    },
    {
      title: '项目涉及节点数量',
      key: 'nodes_count',
      width: 160,
      align: 'center',
      render(row) {
        return h(
          NTag,
          { type: 'success', size: 'small', bordered: false },
          { default: () => String(row.nodes_count ?? 0) }
        );
      },
    },
    {
      title: '项目涉及关系数量',
      key: 'edges_count',
      width: 160,
      align: 'center',
      render(row) {
        return h(
          NTag,
          { type: 'warning', size: 'small', bordered: false },
          { default: () => String(row.edges_count ?? 0) }
        );
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      align: 'center',
      render(row) {
        return h(
          NButton,
          {
            size: 'small',
            type: 'primary',
            secondary: true,
            loading: loadingReportProjectId.value === row.id,
            onClick: () => handleOpenWorkflowReport(row),
          },
          { default: () => '查看构建报告' }
        );
      },
    },
  ]);

  const resolveLatestRunIdForProject = async (projectId: string): Promise<string> => {
    try {
      const listRes = await getExtractionHistoryList(projectId);
      if (!listRes.success || listRes.status !== 200) return '';
      const items = listRes.data?.items || [];
      const first = items.find((x) => String(x?.run_id || '').trim());
      return first ? String(first.run_id) : '';
    } catch (err) {
      console.error('resolveLatestRunIdForProject failed:', err);
      return '';
    }
  };

  const handleOpenWorkflowReport = async (row: GraphManageRow) => {
    const projectId = String(row.id || '').trim();
    if (!projectId) {
      message.warning('项目ID无效，无法查看构建报告');
      return;
    }

    loadingReportProjectId.value = projectId;
    loadingWorkflowReport.value = true;
    latestWorkflowMeta.value = null;
    activeWorkflowRunId.value = '';
    activeWorkflowReportSource.value = '历史任务回放';
    activeReportProjectName.value = row.project_name || projectId;

    try {
      const latestRunId = await resolveLatestRunIdForProject(projectId);
      if (!latestRunId) {
        message.warning('该项目暂无可查看的构建记录，请先执行图谱构建流程');
        return;
      }

      const reportRes = await getWorkflowReportByRun(projectId, latestRunId);
      if (!reportRes.success || reportRes.status !== 200 || !reportRes.data?.workflow_meta) {
        message.warning('未找到可展示的构建报告，请稍后重试');
        return;
      }

      latestWorkflowMeta.value = reportRes.data.workflow_meta as WorkflowMeta;
      activeWorkflowRunId.value = String(reportRes.data.run_id || latestRunId);
      workflowReportModalVisible.value = true;
    } catch (err: any) {
      console.error('handleOpenWorkflowReport failed:', err);
      message.error(err?.message || '查看构建报告失败');
    } finally {
      loadingWorkflowReport.value = false;
      if (loadingReportProjectId.value === projectId) {
        loadingReportProjectId.value = '';
      }
    }
  };

  const fetchProjectStats = async (projectId: string): Promise<{ nodes_count: number; edges_count: number }> => {
    try {
      const [nodesRes, edgesRes] = await Promise.all([
        getNodesByProject(projectId),
        getEdgesByProject(projectId),
      ]);
      const nodesCount = Number(nodesRes?.data?.count ?? nodesRes?.data?.nodes?.length ?? 0);
      const edgesCount = Number(edgesRes?.data?.count ?? edgesRes?.data?.edges?.length ?? 0);
      return {
        nodes_count: Number.isFinite(nodesCount) ? nodesCount : 0,
        edges_count: Number.isFinite(edgesCount) ? edgesCount : 0,
      };
    } catch {
      return { nodes_count: 0, edges_count: 0 };
    }
  };

  const loadTableData = async () => {
    loading.value = true;
    try {
      const response = await getProjectList({
        creator: userStore.getUsername || '',
        view_scope: userStore.isAdmin ? 'all' : 'mine',
        keyword: keyword.value.trim() || undefined,
        search_type: keyword.value.trim() ? 'all' : undefined,
        page: pagination.page,
        page_size: pagination.pageSize,
      });

      const list = Array.isArray(response?.projectList) ? response.projectList : [];
      const rows = await Promise.all(
        list.map(async (item: ProjectItem) => {
          const id = String(item?.id || '').trim();
          const stats = id ? await fetchProjectStats(id) : { nodes_count: 0, edges_count: 0 };
          return {
            id,
            project_name: String(item?.project_name || '').trim() || '-',
            project_desc: String(item?.project_desc || '').trim(),
            creator: String(item?.creator || '').trim(),
            create_time: String(item?.create_time || '').trim(),
            nodes_count: stats.nodes_count,
            edges_count: stats.edges_count,
          };
        })
      );

      tableData.value = rows;
      pagination.itemCount = Number(response?.total || 0);
    } catch (err: any) {
      console.error('load graph manage list failed:', err);
      message.error(err?.message || '加载图谱管理列表失败');
      tableData.value = [];
      pagination.itemCount = 0;
    } finally {
      loading.value = false;
    }
  };

  const handleSearch = async () => {
    pagination.page = 1;
    await loadTableData();
  };

  const refreshList = async () => {
    await loadTableData();
  };

  const handlePageChange = async (page: number) => {
    pagination.page = page;
    await loadTableData();
  };

  const handlePageSizeChange = async (pageSize: number) => {
    pagination.pageSize = pageSize;
    pagination.page = 1;
    await loadTableData();
  };

  onMounted(async () => {
    await loadTableData();
  });
</script>

<style scoped lang="scss">
  .graph-manage-page {
    padding: 16px;
  }

  .graph-manage-card {
    border-radius: 14px;
  }

  .page-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 14px;

    h2 {
      margin: 0;
      font-size: 22px;
      line-height: 1.25;
      color: #0f172a;
    }

    p {
      margin: 6px 0 0;
      font-size: 13px;
      color: #64748b;
    }
  }

  .toolbar {
    margin-bottom: 12px;
  }

  .graph-manage-table {
    :deep(.n-data-table__pagination) {
      justify-content: center;
    }
  }

  .workflow-report-modal-body {
    max-height: 70vh;
    overflow-y: auto;
  }

  .quality-report-card {
    border: 1px solid rgba(59, 130, 246, 0.25);
    border-radius: 12px;
    padding: 12px;
    background: linear-gradient(160deg, rgba(239, 246, 255, 0.92), rgba(248, 250, 252, 0.98));
  }

  .quality-report-card__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 10px;

    h4 {
      margin: 0;
      font-size: 14px;
      color: #0f172a;
    }
  }

  .quality-report-card__hint {
    font-size: 12px;
    color: #64748b;
  }

  .quality-report-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 8px;
  }

  .quality-report-grid__item {
    border-radius: 10px;
    padding: 8px 10px;
    background: #ffffff;
    border: 1px solid rgba(148, 163, 184, 0.2);
  }

  .quality-report-grid__label {
    font-size: 12px;
    color: #64748b;
    margin-bottom: 4px;
  }

  .quality-report-grid__value {
    font-size: 14px;
    font-weight: 600;
    color: #0f172a;
  }

  .workflow-form-value {
    white-space: pre-wrap;
    line-height: 1.6;
  }

  .workflow-raw-toggle {
    border: 1px dashed rgba(148, 163, 184, 0.6);
    border-radius: 10px;
    padding: 8px 10px;
    background: #f8fafc;
  }

  .workflow-raw-toggle summary {
    cursor: pointer;
    font-size: 13px;
    color: #334155;
    user-select: none;
  }

  .workflow-report-json {
    margin: 0;
    font-size: 12px;
    line-height: 1.55;
    color: #0f172a;
    white-space: pre-wrap;
    word-break: break-word;
  }
</style>
