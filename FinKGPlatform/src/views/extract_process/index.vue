<template>
  <div class="extract-process-page">
    <n-page-header class="page-header" title="事件图谱构建流程" @back="goBack">
      <template #subtitle> 项目 ID：{{ projectId }} </template>
    </n-page-header>

    <n-card class="main-card" :bordered="false">
      <div class="content-wrapper">
        <!-- 步骤 1：样本数据选择 -->
        <section class="section-card">
          <div class="section-header">
            <div>
              <h3>样本数据</h3>
              <p>管理本项目参与图谱构建的公告样本。</p>
            </div>
            <div class="section-actions">
              <n-button size="small" @click="handleOpenSelectFromRepo"> 从操作库中选择 </n-button>
              <n-button
                size="small"
                type="error"
                secondary
                :disabled="!checkedProjectAnnouncementIds.length"
                :loading="deletingAnnouncements"
                @click="handleBatchDeleteSamples"
              >
                批量删除（已选 {{ checkedProjectAnnouncementIds.length }} 条）
              </n-button>
              <n-button
                size="small"
                @click="refreshProjectAnnouncements"
                :loading="loadingProjectAnnouncements"
              >
                刷新已选公告
              </n-button>
              <!-- <n-button size="small" tertiary @click="announcementManageVisible = true">
                管理公告 ID
              </n-button> -->
            </div>
          </div>

          <n-data-table
            :columns="selectedColumnsWithSelection"
            :data="paginatedAnnouncements"
            :loading="loadingProjectAnnouncements"
            :bordered="false"
            size="small"
            :row-key="rowKey"
            :checked-row-keys="checkedProjectAnnouncementIds"
            @update:checked-row-keys="handleUpdateCheckedProjectAnnouncementIds"
            :row-props="sampleRowProps"
            :max-height="300"
            :scroll-x="1200"
          />

          <!-- 分页器 -->
          <div class="pagination-container" v-if="projectAnnouncements.length > 0">
            <n-space justify="center" align="center" class="pagination-wrapper">
              <n-button
                :disabled="announcementPage === 1"
                @click="changeAnnouncementPage(1)"
                size="small"
                type="tertiary"
                secondary
              >
                首页
              </n-button>
              <n-button
                :disabled="announcementPage === 1"
                @click="changeAnnouncementPage(announcementPage - 1)"
                size="small"
                secondary
              >
                上一页
              </n-button>
              <span class="page-info">
                第 {{ announcementPage }} 页 / 共
                {{ Math.ceil(projectAnnouncements.length / announcementPageSize) || 1 }} 页 （共
                {{ projectAnnouncements.length }} 条）
              </span>
              <n-button
                :disabled="
                  announcementPage >= Math.ceil(projectAnnouncements.length / announcementPageSize)
                "
                @click="changeAnnouncementPage(announcementPage + 1)"
                size="small"
                secondary
              >
                下一页
              </n-button>
              <n-button
                @click="
                  changeAnnouncementPage(
                    Math.ceil(projectAnnouncements.length / announcementPageSize) || 1
                  )
                "
                size="small"
                type="tertiary"
                secondary
              >
                末页
              </n-button>
            </n-space>
          </div>
        </section>

        <!-- 步骤 2：一键构建（仅 Master Agent） -->
        <section class="section-card">
          <div class="section-header">
            <div>
              <h3>一键构建</h3>
              <p>基于已选公告由 Master Agent 完成节点抽取、关系抽取、冲突检测与图组装。</p>
            </div>
            <div class="section-actions">
              <n-button
                v-if="canViewQualityReport"
                size="small"
                secondary
                :loading="loadingWorkflowReport"
                :disabled="oneClickBuilding"
                @click="handleOpenWorkflowReport"
              >
                查看图谱构建报告
              </n-button>
              <n-button
                v-if="canUseAiQualityAnalysis"
                size="small"
                tertiary
                @click="handleOpenAiQualityAnalysis"
              >
                AI智能分析
              </n-button>
              <n-button
                v-if="canReopenBuildProgress"
                size="small"
                tertiary
                @click="showBuildProgressModal"
              >
                查看构建进度
              </n-button>
              <n-button
                type="primary"
                strong
                :loading="oneClickBuilding && buildRunMode === 'full'"
                :disabled="!projectAnnouncements.length || oneClickBuilding"
                @click="handleOneClickBuild"
              >
                一键构建（Master Agent）
              </n-button>
            </div>
          </div>

          <n-alert type="info" closable style="margin-bottom: 10px">
            构建过程请在弹窗中查看进度：前半程为<strong>节点抽取</strong>，进入关系阶段后切换为<strong>关系抽取</strong>进度。
          </n-alert>

          <n-alert v-if="!projectAnnouncements.length" type="warning" closable>
            请先为当前项目配置至少一条公告数据后再进行一键构建。
          </n-alert>

          <div v-if="canViewQualityReport && qualityReportMetrics.length" class="quality-report-card">
            <div class="quality-report-card__header">
              <h4>质量报告</h4>
              <span class="quality-report-card__hint">来源：workflow_meta.quality_report</span>
            </div>
            <div class="quality-report-grid">
              <div
                v-for="item in qualityReportMetrics"
                :key="item.key"
                class="quality-report-grid__item"
              >
                <div class="quality-report-grid__label">{{ item.label }}</div>
                <div class="quality-report-grid__value">{{ item.value }}</div>
              </div>
            </div>
          </div>

          <n-alert
            v-else-if="canViewQualityReport && hasBuildCompleted && qualityReportMissing"
            type="warning"
            closable
            style="margin-top: 10px"
          >
            本次构建已完成，但后端未返回 workflow_meta.quality_report，暂无法展示质量报告卡片。
          </n-alert>

          <div v-else class="status-row">
            <div class="status-item">
              <span class="label">节点数量：</span>
              <span class="value">{{ nodesCount }}</span>
            </div>
            <div class="status-item">
              <span class="label">当前状态：</span>
              <span class="value">{{ nodeStatusText }}</span>
            </div>
          </div>

          <div class="status-row" style="margin-top: 8px">
            <div class="status-item">
              <span class="label">冲突情况：</span>
              <span class="value">{{ totalConflictCount > 0 ? `检测到 ${totalConflictCount} 条冲突` : '未检测到冲突' }}</span>
            </div>
          </div>

          <template v-if="hasNodes || nodesTableData.length">
            <h4 class="subsection-title">抽取节点列表</h4>
            <n-data-table
              :columns="extractedNodesColumns"
              :row-props="extractedNodeRowProps"
              :data="paginatedNodesTable"
              :bordered="false"
              size="small"
              :max-height="320"
              :scroll-x="1100"
            />
            <div v-if="nodesTableData.length > 0" class="pagination-container">
              <n-pagination
                v-model:page="nodeTablePage"
                :page-size="nodeTablePageSize"
                :item-count="nodesTableData.length"
                show-size-picker
                :page-sizes="[5, 10, 20]"
                @update:page-size="onNodePageSizeChange"
              />
            </div>
          </template>
        </section>

        <!-- 关系结果（由一键构建写入，仅展示） -->
        <section class="section-card">
          <div class="section-header">
            <div>
              <h3>关系抽取结果</h3>
              <p>由一键构建自动生成，无需单独触发关系抽取。</p>
            </div>
          </div>

          <n-alert v-if="!hasEdges && !edgesTableData.length" type="warning" closable>
            尚未完成一键构建或当前项目尚无关系数据。
          </n-alert>

          <div v-else class="status-row">
            <div class="status-item">
              <span class="label">关系数量：</span>
              <span class="value">{{ edgesCount }}</span>
            </div>
            <div class="status-item">
              <span class="label">当前状态：</span>
              <span class="value">{{ edgeStatusText }}</span>
            </div>
          </div>

          <template v-if="hasEdges || edgesTableData.length">
            <h4 class="subsection-title">抽取关系列表</h4>
            <n-data-table
              :columns="extractedEdgesColumns"
              :row-props="extractedEdgeRowProps"
              :data="paginatedEdgesTable"
              :bordered="false"
              size="small"
              :max-height="320"
              :scroll-x="1200"
            />
            <div v-if="edgesTableData.length > 0" class="pagination-container">
              <n-pagination
                v-model:page="edgeTablePage"
                :page-size="edgeTablePageSize"
                :item-count="edgesTableData.length"
                show-size-picker
                :page-sizes="[5, 10, 20]"
                @update:page-size="onEdgePageSizeChange"
              />
            </div>
          </template>
        </section>

        <!-- 步骤 4：事件图谱预览（Neo4j） -->
        <section class="section-card">
          <div class="section-header">
            <div>
              <h3>事件图谱预览</h3>
              <p>一键构建完成后可自动从 Neo4j 拉取并渲染图谱。</p>
            </div>
            <div class="section-actions">
              <n-button
                size="small"
                type="primary"
                secondary
                :loading="loadingGraph"
                :disabled="!hasEdges"
                @click="refreshNeo4jGraph(true)"
              >
                刷新图谱
              </n-button>
              <n-button
                size="small"
                type="primary"
                :disabled="!hasEdges"
                @click="goToGraphEditor"
              >
                编辑图谱
              </n-button>
            </div>
          </div>

          <n-alert v-if="!hasEdges" type="warning" closable>
            当前项目尚无关系数据，请先完成「一键构建」。
          </n-alert>

          <template v-else>
            <div ref="graphPreviewRef" class="graph-preview-shell">
              <div class="status-row graph-status-row">
                <div class="status-item">
                  <span class="label">图谱节点：</span>
                  <span class="value">{{ graphNodesCount }}</span>
                </div>
                <div class="status-item">
                  <span class="label">图谱关系：</span>
                  <span class="value">{{ graphEdgesCount }}</span>
                </div>
                <div class="status-item">
                  <span class="label">当前状态：</span>
                  <span class="value">{{ graphStatusText }}</span>
                </div>
                <div class="status-item">
                  <span class="label">缩放：</span>
                  <span class="value">{{ Math.round(graphZoomLevel * 100) }}%</span>
                </div>
              </div>
              <div class="graph-overlay-tools" v-show="hasEdges">
                <n-button
                  size="small"
                  circle
                  secondary
                  :disabled="!hasEdges"
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
                  :disabled="!hasEdges"
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
                  :disabled="!hasEdges"
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
                  :disabled="!hasEdges"
                  @click="toggleGraphFullscreen"
                  :title="isGraphFullscreen ? '退出全屏' : '全屏查看'"
                >
                  <template #icon>
                    <n-icon :component="isGraphFullscreen ? ContractOutline : ExpandOutline" />
                  </template>
                </n-button>
              </div>
              <div ref="graphChartRef" class="graph-chart"></div>
            </div>
          </template>
        </section>
      </div>
    </n-card>

    <!-- 一键构建：节点 / 关系阶段进度 -->
    <n-modal
      v-model:show="buildProgressModalVisible"
      preset="card"
      style="width: 480px"
      title="一键构建进度"
      :closable="true"
      :mask-closable="true"
      :bordered="false"
    >
      <n-space vertical size="large" style="width: 100%" class="build-progress-shell">
        <div class="build-progress-top">
          <div class="build-phase-pills">
            <span
              class="phase-pill"
              :class="{ active: buildPhase === 'nodes', done: isNodeStageDone }"
            >
              节点抽取
            </span>
            <span
              class="phase-pill"
              :class="{ active: buildPhase === 'relations', done: isRelationStageDone }"
            >
              关系构建
            </span>
          </div>
          <div class="build-progress-metric">{{ animatedBuildProgressPercent }}%</div>
        </div>

        <div>
          <n-text strong style="font-size: 16px">{{ buildPhaseTitle }}</n-text>
          <n-text depth="3" class="build-progress-label">
            {{ buildProgressLabel }}
          </n-text>
          <n-text depth="3" class="build-progress-hint">
            {{ buildStageHint }}
          </n-text>
        </div>
        <n-progress
          class="build-progress-bar"
          type="line"
          :percentage="animatedBuildProgressPercent"
          indicator-placement="inside"
          :color="buildProgressColor"
          processing
        />

        <div v-if="canViewQualityReport && buildProgressPercent >= 100 && qualityReportMetrics.length" class="quality-report-card quality-report-card--compact">
          <div class="quality-report-card__header">
            <h4>质量报告</h4>
          </div>
          <div class="quality-report-grid">
            <div
              v-for="item in qualityReportMetrics"
              :key="`modal-${item.key}`"
              class="quality-report-grid__item"
            >
              <div class="quality-report-grid__label">{{ item.label }}</div>
              <div class="quality-report-grid__value">{{ item.value }}</div>
            </div>
          </div>
        </div>
      </n-space>
    </n-modal>

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
              当前 run 没有 quality_report 字段，建议重跑一次一键构建以生成完整报告。
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
            description="暂无可查看的构建报告，请先执行一键构建或切换到有 run_id 的构建结果。"
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

    <n-modal
      v-model:show="aiAnalysisModalVisible"
      preset="card"
      style="width: 760px; max-width: 92vw"
      title="AI智能分析报告"
      :bordered="false"
      :mask-closable="true"
    >
      <n-space vertical size="large" style="width: 100%" class="ai-analysis-content">
        <n-text depth="3" class="ai-analysis-source">分析来源：workflow_meta + AI Agent</n-text>

        <n-empty v-if="!latestWorkflowMeta" description="暂无可分析的 workflow_meta，请先构建图谱后重试" />

        <template v-else>
          <n-spin :show="loadingAiAnalysis" size="small">
            <n-card size="small" :bordered="true" class="ai-analysis-card">
              <n-scrollbar style="max-height: 360px" class="ai-analysis-scroll">
                <pre class="workflow-report-json ai-analysis-report">{{ aiAnalysisText || '正在生成分析报告...' }}</pre>
              </n-scrollbar>
            </n-card>
          </n-spin>
        </template>
      </n-space>
      <template #footer>
        <n-space justify="end">
          <n-button @click="aiAnalysisModalVisible = false">关闭</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 公告 ID 管理弹窗 -->
    <!-- <n-modal
      v-model:show="announcementManageVisible"
      preset="card"
      style="width: 680px"
      title="项目公告管理"
      :bordered="false"
      :mask-closable="false"
    >
      <div class="manage-body">
        <div class="manage-block">
          <h4>新增公告 ID</h4>
          <p class="desc">
            从操作库中挑选好公告后，将其 ID 复制粘贴到下方输入框（支持逗号、空格或换行分隔），点击“保存到项目”即可。
          </p>
          <n-input
            v-model:value="announcementIdsInput"
            type="textarea"
            :rows="4"
            placeholder="示例：1234, 5678, 9012"
          />
          <div class="manage-actions">
            <n-button
              type="primary"
              size="small"
              :loading="savingAnnouncements"
              @click="handleSaveAnnouncementIds"
            >
              保存到项目
            </n-button>
          </div>
        </div>

        <div class="manage-block">
          <h4>当前项目公告</h4>
          <n-data-table
            :columns="manageColumns"
            :data="projectAnnouncements"
            :row-key="rowKey"
            checkable
            :checked-row-keys="checkedAnnouncementIds"
            @update:checked-row-keys="checkedAnnouncementIds = $event as string[]"
            size="small"
            :bordered="false"
          />
          <div class="manage-actions right">
            <n-button
              type="error"
              size="small"
              secondary
              :disabled="!checkedAnnouncementIds.length"
              :loading="deletingAnnouncements"
              @click="handleDeleteSelectedAnnouncements"
            >
              删除选中
            </n-button>
          </div>
        </div>
      </div>
    </n-modal> -->

    <!-- 从操作库选择样本 -->
    <n-modal
      v-model:show="selectFromRepoVisible"
      preset="card"
      style="width: 1360px; max-width: 98vw"
      title="从事件看板选择事件作为样本"
      :bordered="false"
      :mask-closable="false"
    >
      <div class="repo-select-scroll-body">
      <!-- 筛选条件（与事件看板同款） -->
      <div class="filter" style="margin-bottom: 12px">
        <div class="filter-header" @click="toggleRepoSearch">
          <div class="filter-header-content">
            <n-icon :component="SearchOutline" size="18" :style="{ color: '#165dff' }" />
            <n-text strong>筛选条件</n-text>
          </div>
          <div class="filter-header-action">
            <n-text class="filter-toggle-text" :style="{ color: 'lightgray' }">
              {{ repoSearchExpanded ? '点击收起' : '点击展开' }}
            </n-text>
            <n-icon
              :component="ArrowUpOutline"
              size="16"
              :style="{
                color: 'lightgray',
                transform: repoSearchExpanded ? 'rotate(0deg)' : 'rotate(180deg)',
                transition: 'transform 0.3s ease',
              }"
            />
          </div>
        </div>

        <n-collapse-transition :show="repoSearchExpanded">
          <div class="filter-content">
            <div class="filter-row">
              <div class="filter-item">
                <label class="filter-label">
                  <n-icon :component="SearchOutline" size="14" />
                  关键字
                </label>
                <n-input
                  placeholder="输入关键字"
                  v-model:value="repo_search_keyword"
                  clearable
                  size="small"
                  class="filter-input"
                />
              </div>
            </div>

            <div class="filter-row">
              <div class="filter-item">
                <label class="filter-label">
                  <n-icon :component="AnalyticsOutline" size="14" />
                  事件类型
                </label>
                <n-select
                  clearable
                  multiple
                  placeholder="选择事件类型"
                  :options="[
                    { label: '全部', value: 'all' },
                    { label: '宏观', value: 'macro' },
                    { label: '行业', value: 'industry' },
                    { label: '个股', value: 'trading' },
                    { label: '情绪', value: 'sentiment' },
                  ]"
                  v-model:value="repo_search_event_type"
                  size="small"
                  class="filter-input"
                />
              </div>

              <div class="filter-item">
                <label class="filter-label">
                  <n-icon :component="TimeOutline" size="14" />
                  时间范围
                </label>
                <n-date-picker
                  type="datetimerange"
                  v-model:value="repo_search_time_range"
                  clearable
                  size="small"
                  class="filter-input"
                />
              </div>
            </div>

            <div class="filter-actions">
              <n-button
                size="small"
                type="primary"
                secondary
                @click="submitRepoSearch"
                class="filter-button"
              >
                <template #icon>
                  <n-icon :component="SearchOutline" size="16" />
                </template>
                查询
              </n-button>

              <n-button size="small" @click="resetRepoSearch" class="filter-button">
                重置
              </n-button>
            </div>
          </div>
        </n-collapse-transition>
      </div>

      <n-data-table
        :columns="repoColumns"
        :data="repoFilteredSamples"
        :loading="loadingRepoSamples"
        remote
        :scroll-x="1620"
        checkable
        :row-key="repoRowKey"
        :checked-row-keys="checkedRepoKeys"
        @update:checked-row-keys="checkedRepoKeys = $event as (string | number)[]"
        @update:sorter="handleRepoSorter"
        @update:filters="handleRepoFilters"
        :row-props="repoRowProps"
        size="small"
        class="all-events-table"
        :single-line="false"
        max-height="420px"
        :bordered="false"
      />
      <div class="pagination-container">
        <n-pagination
          v-model:page="repoPage"
          :page-size="repoPageSize"
          :item-count="repoTotal"
          show-size-picker
          show-quick-jumper
          :page-sizes="[10, 20, 50, 100]"
          @update:page="changeRepoPage"
          @update:page-size="onRepoPageSizeChange"
        />
      </div>
      </div>
      <template #footer>
        <div class="dialog-footer right">
          <n-button @click="selectFromRepoVisible = false"> 取消 </n-button>
          <n-button type="primary" :loading="savingFromRepo" @click="handleSaveFromRepo">
            确认选择
          </n-button>
        </div>
      </template>
    </n-modal>

    <!-- 样本 / 操作库详情（复用事件看板详情样式） -->
    <n-modal
      v-model:show="detailVisible"
      preset="card"
      :title="detailTitle"
      style="width: 760px; max-width: 92vw"
      :bordered="false"
      :mask-closable="true"
    >
      <div v-if="detailRecord" class="detail-content">
        <n-descriptions
          label-placement="left"
          :column="1"
          size="small"
          bordered
          :label-style="{
            width: '110px',
            minWidth: '110px',
            fontWeight: '500',
            textAlign: 'right',
          }"
          :content-style="{ maxWidth: '560px' }"
        >
          <template v-if="detailType === 'node' || detailType === 'edge'">
            <n-descriptions-item label="ID">
              <n-text>{{ (detailRecord as any).id || '-' }}</n-text>
            </n-descriptions-item>
            <n-descriptions-item label="名称/值">
              <n-text v-if="detailType === 'node'">{{ getNodeDisplayName(detailRecord) }}</n-text>
              <n-text v-else>{{ detailRecord.value || detailRecord.description || '-' }}</n-text>
            </n-descriptions-item>

            <n-descriptions-item v-if="detailType === 'node'" label="关键属性">
              <n-text>{{ detailRecord.key || detailRecord.properties?.canonical_name || '-' }}</n-text>
            </n-descriptions-item>

            <n-descriptions-item label="上下文 / 样本">
              <n-text>{{ detailType === 'node' ? getNodeContext(detailRecord) : (detailRecord.properties?.context || '-') }}</n-text>
            </n-descriptions-item>

            <n-descriptions-item v-if="detailType === 'edge'" label="起点">
              <n-text>{{ getEdgeNodeName(detailRecord, 'from') }}</n-text>
            </n-descriptions-item>
            <n-descriptions-item v-if="detailType === 'edge'" label="终点">
              <n-text>{{ getEdgeNodeName(detailRecord, 'to') }}</n-text>
            </n-descriptions-item>

            <n-descriptions-item v-if="detailType === 'edge'" label="依据">
              <n-scrollbar style="max-height: 160px">
                <pre style="margin:0; font-size:12px; white-space:pre-wrap">{{ detailRecord.properties?.context || detailRecord.context || '-' }}</pre>
              </n-scrollbar>
            </n-descriptions-item>
          </template>

          <template v-else>
          <n-descriptions-item label="样本 ID">
            <n-text>{{ detailRecord.id || '-' }}</n-text>
          </n-descriptions-item>

          <n-descriptions-item label="事件类型">
            <n-tag
              :type="
                getEventType(detailRecord) === 'macro'
                  ? 'info'
                  : getEventType(detailRecord) === 'industry'
                  ? 'success'
                  : getEventType(detailRecord) === 'trading'
                  ? 'warning'
                  : 'default'
              "
            >
              {{ formatEventType(getEventType(detailRecord)) }}
            </n-tag>
          </n-descriptions-item>

          <n-descriptions-item label="事件子类">
            <n-text>{{ formatEventSubtype(getEventSubtype(detailRecord)) }}</n-text>
          </n-descriptions-item>

          <n-descriptions-item label="发布时间">
            <n-text>
              <n-time
                v-if="(detailRecord as any).event_time"
                :time="new Date((detailRecord as any).event_time)"
                type="datetime"
              />
              <span v-else-if="(detailRecord as any)['发布时间']">{{ (detailRecord as any)['发布时间'] }}</span>
              <span v-else>-</span>
            </n-text>
          </n-descriptions-item>

          <n-descriptions-item label="事件摘要">
            <div style="padding: 8px; background: #f8f9fa; border-radius: 4px">
              <n-text style="white-space: pre-wrap; line-height: 1.6; font-size: 13px">
                {{
                  getEventType(detailRecord) === 'industry'
                    ? formatIndustryEventDetail(detailRecord)
                    : getEventType(detailRecord) === 'sentiment'
                    ? formatMoodEventDetail(detailRecord)
                    : getEventType(detailRecord) === 'trading'
                    ? ((detailRecord as any)['标题'] || (detailRecord as any).event_description)
                    : (detailRecord as any).event_description || (detailRecord as any).raw_data?.新闻内容 || '-'
                }}
              </n-text>
            </div>
          </n-descriptions-item>
          </template>

          <n-descriptions-item
            v-if="getEventType(detailRecord) === 'trading' && (detailRecord as any)['内容']"
            label="完整内容"
          >
            <div
              style="
                max-height: 200px;
                overflow-y: auto;
                padding: 8px;
                background: #f8f9fa;
                border-radius: 4px;
              "
            >
              <n-text style="white-space: pre-wrap; line-height: 1.6; font-size: 13px">
                {{ (detailRecord as any)['内容'] }}
              </n-text>
            </div>
          </n-descriptions-item>

          <n-descriptions-item
            v-if="getEventType(detailRecord) === 'macro' && (detailRecord as any).raw_data?.新闻内容"
            label="新闻内容"
          >
            <div
              style="
                max-height: 200px;
                overflow-y: auto;
                padding: 8px;
                background: #f8f9fa;
                border-radius: 4px;
              "
            >
              <n-text style="white-space: pre-wrap; line-height: 1.6; font-size: 13px">
                {{ (detailRecord as any).raw_data.新闻内容 }}
              </n-text>
            </div>
          </n-descriptions-item>

          <n-descriptions-item
            v-if="(detailRecord as any).symbol || getEventType(detailRecord) === 'trading'"
            label="相关标的"
          >
            <n-text>
              <span v-if="getEventType(detailRecord) === 'trading'">
                {{
                  (() => {
                    const title = (detailRecord as any)['标题'] || '';
                    const content = (detailRecord as any)['内容'] || '';
                    const symbolMatch = title.match(/[0-9]{6}/) || content.match(/[0-9]{6}/);
                    return symbolMatch
                      ? symbolMatch[0]
                      : (detailRecord as any).symbol || (detailRecord as any).stock_num || '-';
                  })()
                }}
              </span>
              <span v-else-if="(detailRecord as any).board_name">{{ (detailRecord as any).board_name }}</span>
              <span v-else>{{ (detailRecord as any).symbol || (detailRecord as any).stock_num || '-' }}</span>
            </n-text>
          </n-descriptions-item>

          <n-descriptions-item label="影响等级">
            <n-tag
              :type="
                ((detailRecord as any).impact_level || 'medium') === 'critical'
                  ? 'error'
                  : ((detailRecord as any).impact_level || 'medium') === 'high'
                  ? 'warning'
                  : ((detailRecord as any).impact_level || 'medium') === 'medium'
                  ? 'default'
                  : 'info'
              "
            >
              {{ formatImpactLevel((detailRecord as any).impact_level) }}
            </n-tag>
          </n-descriptions-item>

          <n-descriptions-item label="情感倾向">
            <n-tag
              :type="
                ((detailRecord as any).sentiment || 'neutral') === 'positive'
                  ? 'success'
                  : ((detailRecord as any).sentiment || 'neutral') === 'negative'
                  ? 'error'
                  : 'default'
              "
            >
              {{ formatSentiment((detailRecord as any).sentiment) }}
            </n-tag>
          </n-descriptions-item>

          <template v-if="(detailRecord as any).raw_data">
            <n-descriptions-item
              v-if="(detailRecord as any).raw_data.real_time_close !== undefined"
              label="实时价格"
            >
              <n-text>{{ (detailRecord as any).raw_data.real_time_close.toFixed(2) }} 元</n-text>
            </n-descriptions-item>

            <n-descriptions-item
              v-if="(detailRecord as any).raw_data.price_change !== undefined"
              label="涨跌幅"
            >
              <n-text :type="(detailRecord as any).raw_data.price_change > 0 ? 'error' : 'success'">
                {{ (detailRecord as any).raw_data.price_change > 0 ? '+' : ''
                }}{{ (detailRecord as any).raw_data.price_change.toFixed(2) }}%
              </n-text>
            </n-descriptions-item>

            <n-descriptions-item
              v-if="(detailRecord as any).raw_data.total_amount !== undefined"
              label="成交额"
            >
              <n-text>{{ ((detailRecord as any).raw_data.total_amount / 10000).toFixed(1) }} 亿元</n-text>
            </n-descriptions-item>

            <n-descriptions-item
              v-if="(detailRecord as any).raw_data.net_inflow !== undefined"
              label="净流入"
            >
              <n-text :type="(detailRecord as any).raw_data.net_inflow > 0 ? 'error' : 'success'">
                {{ (detailRecord as any).raw_data.net_inflow > 0 ? '+' : ''
                }}{{ ((detailRecord as any).raw_data.net_inflow / 10000).toFixed(1) }} 亿元
              </n-text>
            </n-descriptions-item>

            <n-descriptions-item
              v-if="(detailRecord as any).raw_data.rise_stocks !== undefined"
              label="上涨家数"
            >
              <n-text>
                {{ (detailRecord as any).raw_data.rise_stocks }} /
                {{ (detailRecord as any).raw_data.total_stocks }}
                ({{ (((detailRecord as any).raw_data.rise_stocks / (detailRecord as any).raw_data.total_stocks) * 100).toFixed(1) }}%)
              </n-text>
            </n-descriptions-item>

            <n-descriptions-item v-if="(detailRecord as any).raw_data.leader_stock" label="领涨/跌股">
              <n-text>
                {{ (detailRecord as any).raw_data.leader_stock }}
                <span
                  v-if="(detailRecord as any).raw_data.leader_change !== undefined"
                  :type="(detailRecord as any).raw_data.leader_change > 0 ? 'error' : 'success'"
                  style="margin-left: 8px; font-size: 12px"
                >
                  {{ (detailRecord as any).raw_data.leader_change > 0 ? '+' : ''
                  }}{{ (detailRecord as any).raw_data.leader_change.toFixed(2) }}%
                </span>
              </n-text>
            </n-descriptions-item>

            <n-descriptions-item v-if="(detailRecord as any).raw_data.daily_MA5 !== undefined" label="MA5">
              <n-text>{{ (detailRecord as any).raw_data.daily_MA5.toFixed(2) }}</n-text>
            </n-descriptions-item>

            <n-descriptions-item v-if="(detailRecord as any).raw_data.daily_MA10 !== undefined" label="MA10">
              <n-text>{{ (detailRecord as any).raw_data.daily_MA10.toFixed(2) }}</n-text>
            </n-descriptions-item>

            <n-descriptions-item v-if="(detailRecord as any).raw_data.daily_MA20 !== undefined" label="MA20">
              <n-text>{{ (detailRecord as any).raw_data.daily_MA20.toFixed(2) }}</n-text>
            </n-descriptions-item>

            <n-descriptions-item v-if="(detailRecord as any).raw_data.daily_MA60 !== undefined" label="MA60">
              <n-text>{{ (detailRecord as any).raw_data.daily_MA60.toFixed(2) }}</n-text>
            </n-descriptions-item>

            <n-descriptions-item
              v-if="(detailRecord as any).raw_data.deviation_pct !== undefined"
              label="偏离度"
            >
              <n-text>{{ (detailRecord as any).raw_data.deviation_pct.toFixed(2) }}%</n-text>
            </n-descriptions-item>
          </template>

          <n-descriptions-item v-if="(detailRecord as any).data_source" label="数据源">
            <n-text>{{ (detailRecord as any).data_source }}</n-text>
          </n-descriptions-item>

          <n-descriptions-item v-if="(detailRecord as any).raw_data?.匹配关键词?.length > 0" label="关键词">
            <n-space wrap>
              <n-tag
                v-for="(keyword, index) in (detailRecord as any).raw_data.匹配关键词"
                :key="index"
                size="small"
                type="info"
                style="margin: 2px"
              >
                {{ keyword }}
              </n-tag>
            </n-space>
          </n-descriptions-item>

          <n-descriptions-item v-if="(detailRecord as any).raw_data" label="raw_data">
            <n-scrollbar style="max-height: 220px">
              <pre style="margin: 0; font-size: 12px; line-height: 1.5; white-space: pre-wrap">
{{ prettyJson((detailRecord as any).raw_data) }}
              </pre>
            </n-scrollbar>
          </n-descriptions-item>
        </n-descriptions>
      </div>

      <template #footer>
        <n-space justify="end">
          <n-button @click="detailVisible = false">关闭</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<!-- <script setup lang="ts">
import { computed, onMounted, ref, h } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useMessage } from 'naive-ui';
import type { DataTableColumns, DataTableRowKey } from 'naive-ui';
import { fetchAllEvents } from '@/api/message/message';
import {
  getProjectAnnouncements,
  saveSelectData,
  deleteSelectedData,
  checkExtractionStatus,
  extractRelations,
  getEdgesByProject,
  getNodesByProject,
  type ProjectAnnouncementItem,
} from '@/api/kg/extract';

const route = useRoute();
const router = useRouter();
const message = useMessage();

const projectId = computed(() => String(route.params.projectId || ''));

const currentStep = ref(1);

// 样本 / 公告
const projectAnnouncements = ref<ProjectAnnouncementItem[]>([]);
const loadingProjectAnnouncements = ref(false);
const announcementManageVisible = ref(false);
const announcementIdsInput = ref('');
const savingAnnouncements = ref(false);
const deletingAnnouncements = ref(false);
const checkedAnnouncementIds = ref<string[]>([]);

// 分页相关
const announcementPage = ref(1);
const announcementPageSize = ref(5); // 每页显示5条

// 计算当前页的数据
const paginatedAnnouncements = computed(() => {
  const start = (announcementPage.value - 1) * announcementPageSize.value;
  const end = start + announcementPageSize.value;
  return projectAnnouncements.value.slice(start, end);
});

// 操作库样本
interface TextSampleItem {
  id?: string;
  index: number;
  title: string;
  content: string;
  publishTime: string;
  summary?: string;
  stock_num?: string;
  event_type?: string;
  event_subtype?: string;
  impact_level?: string;
  sentiment?: string;
}

const selectFromRepoVisible = ref(false);
const repoSamples = ref<TextSampleItem[]>([]);
const loadingRepoSamples = ref(false);
const repoPage = ref(1);
const repoPageSize = ref(10);
const repoTotal = ref(0);
const checkedRepoKeys = ref<(string | number)[]>([]);
const savingFromRepo = ref(false);

// 抽取状态
const extractingNodes = ref(false);
const nodesProgress = ref(0);
const nodesCount = ref(0);
const hasNodes = ref(false);

const extractingRelations = ref(false);
const edgesCount = ref(0);
const hasEdges = ref(false);

const relationType = ref<'causal' | 'temporal' | 'general'>('general');
const relationTypeOptions = [
  { label: '通用关系', value: 'general' },
  { label: '因果关系', value: 'causal' },
  { label: '时序关系', value: 'temporal' },
];

const nodeStatusText = computed(() => {
  if (extractingNodes.value) return '正在抽取节点...';
  if (hasNodes.value) return '已完成节点抽取';
  return '尚未抽取节点';
});

const edgeStatusText = computed(() => {
  if (extractingRelations.value) return '正在抽取关系...';
  if (hasEdges.value) return '已完成关系抽取';
  return '尚未抽取关系';
});

// 修改表格列定义，禁用默认的 ellipsis tooltip
const selectedColumns: DataTableColumns<ProjectAnnouncementItem> = [
  {
    title: '公告 ID',
    key: 'id',
    width: 120,
    ellipsis: {
      tooltip: false,
    },
    render(row) {
      return h('span', {
        style: {
          display: 'block',
          width: '100%',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          cursor: 'pointer'
        }
      }, row.id || '-');
    }
  },
  {
    title: '标题',
    key: 'title',
    ellipsis: {
      tooltip: false,
    },
    render(row) {
      return h('span', {
        style: {
          display: 'block',
          width: '100%',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          cursor: 'pointer'
        }
      }, row.title || '-');
    }
  },
  {
    title: '内容',
    key: 'content',
    ellipsis: {
      tooltip: false,
    },
    render(row) {
      return h('span', {
        style: {
          display: 'block',
          width: '100%',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          cursor: 'pointer'
        }
      }, row.content || '-');
    }
  },
  {
    title: '日期',
    key: 'date',
    width: 120,
    render(row) {
      return h('span', {}, row.date || '-');
    }
  },
  {
    title: '股票代码',
    key: 'stock_num',
    width: 120,
    render(row) {
      return h('span', {}, row.stock_num || '-');
    }
  },
];

const manageColumns: DataTableColumns<ProjectAnnouncementItem> = [
  {
    type: 'selection',
  },
  ...selectedColumns,
];

const rowKey = (row: ProjectAnnouncementItem): DataTableRowKey => row.id;

// 操作库表格列（完全复用事件看板里的结构样式）
const repoColumns: DataTableColumns<TextSampleItem> = [
  {
    type: 'selection',
    width: 50,
    fixed: 'left',
  },
  {
    title: '事件类型',
    key: 'event_type',
    width: 100,
    fixed: 'left',
    align: 'center',
    render(row) {
      return h('span', {}, row.event_type || '-');
    }
  },
  {
    title: '事件时间',
    key: 'publishTime',
    width: 120,
    align: 'center',
    render(row) {
      return h('span', {}, row.publishTime || '-');
    }
  },
  {
    title: '事件摘要',
    key: 'content',
    width: 320,
    align: 'center',
    ellipsis: {
      tooltip: false,
    },
    render(row) {
      return h('span', {
        style: {
          display: 'block',
          width: '100%',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          cursor: 'pointer'
        }
      }, row.content || '-');
    }
  },
  {
    title: '事件子类',
    key: 'event_subtype',
    width: 120,
    align: 'center',
    render(row) {
      return h('span', {}, row.event_subtype || '-');
    }
  },
  {
    title: '影响级别',
    key: 'impact_level',
    width: 80,
    align: 'center',
    render(row) {
      return h('span', {}, row.impact_level || '-');
    }
  },
  {
    title: '情感',
    key: 'sentiment',
    width: 80,
    align: 'center',
    render(row) {
      return h('span', {}, row.sentiment || '-');
    }
  },
  {
    title: '相关标的',
    key: 'stock_num',
    width: 120,
    align: 'center',
    render(row) {
      return h('span', {}, row.stock_num || '-');
    }
  },
];

const repoRowKey = (row: TextSampleItem): DataTableRowKey => (row.id as string) || row.index;

const goBack = () => {
  router.push({ name: 'project_manage_index' });
};

const goToGraphEditor = () => {
  if (!projectId.value) return;
  router.push({ name: 'graph_editor', params: { projectId: projectId.value } });
};

const detailVisible = ref(false);
const detailRecord = ref<ProjectAnnouncementItem | null>(null);

// 修改行点击处理函数
const handleRowClick = (row: ProjectAnnouncementItem) => {
  detailRecord.value = row;
  detailVisible.value = true;
};

// 分页切换函数
const changeAnnouncementPage = (page: number) => {
  if (page < 1) return;
  const maxPage = Math.max(1, Math.ceil(projectAnnouncements.value.length / announcementPageSize.value));
  announcementPage.value = Math.min(page, maxPage);
};

const refreshProjectAnnouncements = async () => {
  if (!projectId.value) {
    console.log('projectId 为空');
    return;
  }
  loadingProjectAnnouncements.value = true;
  try {
    console.log('开始获取项目公告，projectId:', projectId.value);
    const res = await getProjectAnnouncements(projectId.value);
    console.log('获取项目公告响应:', res);
    
    if (res.status !== 200) {
      message.error(res.msg || '获取项目公告失败');
      return;
    }
    projectAnnouncements.value = res.data || [];
    console.log('项目公告数据:', projectAnnouncements.value);
    // 重置到第一页
    announcementPage.value = 1;
  } catch (error: any) {
    console.error('refreshProjectAnnouncements error:', error);
    message.error(error?.message || '获取项目公告失败');
  } finally {
    loadingProjectAnnouncements.value = false;
  }
};

const handleOpenSelectFromRepo = async () => {
  selectFromRepoVisible.value = true;
  checkedRepoKeys.value = [];
  await loadRepoSamples();
};

// 简化版事件类型推断（复用事件看板的核心逻辑）
function getEventTypeForRepo(event: any): string {
  if (event.event_type) return event.event_type;
  if (event.type) return event.type;
  if (event.eventType) return event.eventType;
  if (event['事件类型']) return event['事件类型'];
  if (event.category) return event.category;

  if (
    event.board_name ||
    event.event_subtype?.includes('price') ||
    event.event_subtype?.includes('leader')
  ) {
    return 'industry';
  }
  if (event['标题'] || event['内容']) {
    return 'trading';
  }
  if (event.raw_data?.新闻内容 || event.event_subtype?.includes('macro')) {
    return 'macro';
  }
  if (event.event_subtype?.includes('ma') || event.event_subtype?.includes('cross')) {
    return 'sentiment';
  }

  return 'unknown';
}

// 简化版事件摘要
function getEventSummaryForRepo(event: any): string {
  const eventType = getEventTypeForRepo(event);
  const rawData = event.raw_data || {};

  if (event.event_description) return event.event_description;

  switch (eventType) {
    case 'macro':
      return (
        event.event_description ||
        (rawData.新闻内容 ? String(rawData.新闻内容).slice(0, 80) + '…' : '宏观事件')
      );
    case 'industry':
      return event.board_name || '行业事件';
    case 'trading':
      return event['标题'] || event.title || '个股事件';
    default:
      return event['标题'] || event.title || rawData.新闻内容 || '事件';
  }
}

const loadRepoSamples = async () => {
  if (!projectId.value) return;
  loadingRepoSamples.value = true;
  try {
    const params: any = {
      page: repoPage.value,
      size: repoPageSize.value,
      sort_field: 'event_time',
      sort_order: -1,
    };

    console.log('开始获取操作库数据，params:', params);
    const response = await fetchAllEvents(params);
    console.log('操作库响应:', response);

    if (response.code !== 0) {
      message.error('获取事件数据失败');
      return;
    }

    const data = response.data;
    let events: any[] = [];
    let total = 0;

    if (data && data.messages) {
      events = Array.isArray(data.messages) ? data.messages : [];
      total = data.total || data.count || events.length;
    } else if (Array.isArray(data)) {
      events = data;
      total = data.length;
    } else if (data && data.data) {
      events = Array.isArray(data.data) ? data.data : [];
      total = data.total || data.count || events.length;
    } else if (data && data.list) {
      events = Array.isArray(data.list) ? data.list : [];
      total = data.total || data.count || events.length;
    }

    console.log('解析后的事件数据:', events);

    repoSamples.value = events.map((event, idx) => {
      const id = event._id || event.id || `${repoPage.value}-${idx}`;
      const title = event.title || event['标题'] || event.event_name || '';
      const stock =
        event.symbol || event.stock_code || event.company_of_interest || '';
      const time =
        event.event_time || event.trade_date || event.date || event.time || '';

      const event_type = getEventTypeForRepo(event);
      const content = getEventSummaryForRepo(event);

      return {
        id: String(id),
        index: (repoPage.value - 1) * repoPageSize.value + idx + 1,
        title,
        content,
        publishTime: String(time || ''),
        stock_num: stock,
        event_type,
        event_subtype: event.event_subtype || '',
        impact_level: event.impact_level || '',
        sentiment: event.sentiment || '',
      };
    });

    console.log('处理后的操作库样本数据:', repoSamples.value);
    repoTotal.value = total;
  } catch (error: any) {
    console.error('loadRepoSamples error:', error);
    message.error(error?.message || '获取事件数据失败');
  } finally {
    loadingRepoSamples.value = false;
  }
};

const changeRepoPage = async (page: number) => {
  if (page < 1) return;
  const maxPage = Math.max(1, Math.ceil(repoTotal.value / repoPageSize.value));
  repoPage.value = Math.min(page, maxPage);
  await loadRepoSamples();
};

const handleSaveAnnouncementIds = async () => {
  const raw = announcementIdsInput.value.trim();
  if (!raw) {
    message.warning('请输入至少一个公告 ID');
    return;
  }
  const ids = raw
    .split(/[\s,，;；]+/)
    .map((s) => s.trim())
    .filter(Boolean);
  if (!ids.length) {
    message.warning('未解析到有效的公告 ID');
    return;
  }

  savingAnnouncements.value = true;
  try {
    const res = await saveSelectData({
      project_id: projectId.value,
      announcement_ids: ids,
    });
    if (res.status === 200) {
      message.success(res.msg || '保存公告成功');
      announcementIdsInput.value = '';
      await refreshProjectAnnouncements();
    } else {
      message.error(res.msg || '保存公告失败');
    }
  } catch (error: any) {
    message.error(error?.message || '保存公告失败');
    console.error('handleSaveAnnouncementIds error:', error);
  } finally {
    savingAnnouncements.value = false;
  }
};

const handleSaveFromRepo = async () => {
  if (!checkedRepoKeys.value.length) {
    message.warning('请至少选择一条样本');
    return;
  }
  // 假设操作库返回的每条数据都包含真实公告 ID
  const ids = repoSamples.value
    .filter((item) => checkedRepoKeys.value.includes(item.id || item.index))
    .map((item) => item.id)
    .filter(Boolean) as string[];

  if (!ids.length) {
    message.warning('未获取到有效的样本 ID');
    return;
  }

  savingFromRepo.value = true;
  try {
    const res = await saveSelectData({
      project_id: projectId.value,
      announcement_ids: ids,
    });
    if (res.status === 200) {
      message.success(res.msg || '保存样本成功');
      selectFromRepoVisible.value = false;
      await refreshProjectAnnouncements();
    } else {
      message.error(res.msg || '保存样本失败');
    }
  } catch (error: any) {
    message.error(error?.message || '保存样本失败');
    console.error('handleSaveFromRepo error:', error);
  } finally {
    savingFromRepo.value = false;
  }
};

const handleDeleteSelectedAnnouncements = async () => {
  if (!checkedAnnouncementIds.value.length) {
    return;
  }
  deletingAnnouncements.value = true;
  try {
    const res = await deleteSelectedData({
      project_id: projectId.value,
      ids: checkedAnnouncementIds.value,
    });
    if (res.status === 200) {
      message.success(res.msg || '删除公告成功');
      checkedAnnouncementIds.value = [];
      await refreshProjectAnnouncements();
    } else {
      message.error(res.msg || '删除公告失败');
    }
  } catch (error: any) {
    message.error(error?.message || '删除公告失败');
    console.error('handleDeleteSelectedAnnouncements error:', error);
  } finally {
    deletingAnnouncements.value = false;
  }
};

// 节点抽取：使用 fetch 处理 NDJSON 流，只取最终结果
const handleExtractNodes = async () => {
  if (!projectAnnouncements.value.length) {
    message.warning('请先为项目配置公告数据');
    return;
  }
  if (extractingNodes.value) return;

    const ids = projectAnnouncements.value
      .map((item: any) => item.id ?? item._id)
      .filter((id): id is string => id != null && String(id).trim() !== '');
    if (!ids.length) {
      message.warning('未获取到有效的公告 ID');
      return;
    }

    extractingNodes.value = true;
  conflictsList.value = [];
  nodesProgress.value = 0;
  currentStep.value = 2;

  try {
    const resp = await fetch('/old-api/llmGenKG/extract_nodes_with_llm', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        project_id: projectId.value,
        announcement_ids: ids,
      }),
    });

    const text = await resp.text();
    const lines = text
      .split('\n')
      .map((l) => l.trim())
      .filter(Boolean);

    let finalData: any = null;
    for (const line of lines) {
      try {
        const jsonLine = JSON.parse(line);
        if (typeof jsonLine.progress === 'number') {
          nodesProgress.value = jsonLine.progress;
        }
        if (jsonLine.status === 'complete') {
          finalData = jsonLine;
        }
      } catch {
        // 忽略解析失败的行
      }
    }

    if (!finalData) {
      message.error('节点抽取返回结果异常');
      return;
    }

    nodesCount.value = finalData.data?.count ?? 0;
    hasNodes.value = nodesCount.value > 0;
    nodesProgress.value = 100;
    message.success('节点抽取完成');
    currentStep.value = 3;
  } catch (error: any) {
    message.error(error?.message || '节点抽取失败');
    console.error('handleExtractNodes error:', error);
  } finally {
    extractingNodes.value = false;
  }
};

const handleOneClickBuild = async () => {
  if (!projectAnnouncements.value.length) {
    message.warning('请先为项目配置公告数据');
    return;
  }
  if (oneClickBuilding.value || extractingNodes.value || extractingRelations.value) return;

  const ids = projectAnnouncements.value
    .map((item: any) => item.id ?? item._id)
    .filter((id): id is string => id != null && String(id).trim() !== '');
  if (!ids.length) {
    message.warning('未获取到有效的公告 ID');
    return;
  }

  oneClickBuilding.value = true;
  conflictsList.value = [];
  currentStep.value = 3;
  try {
    const res = await runMasterAgent({
      project_id: projectId.value,
      sample_ids: ids,
    });
    if (!res.success || res.status !== 200) {
      message.error(res.message || '一键构建失败');
      return;
    }
    nodesCount.value = res.data?.nodes?.length ?? 0;
    edgesCount.value = res.data?.edges?.length ?? 0;
    hasNodes.value = nodesCount.value > 0;
    hasEdges.value = edgesCount.value > 0;
    conflictsList.value = res.data?.conflicts ?? res.data?.graph?.conflicts ?? [];
    message.success('一键构建完成');
    await refreshNeo4jGraph(true);
  } catch (error: any) {
    message.error(error?.message || '一键构建失败');
    console.error('handleOneClickBuild error:', error);
  } finally {
    oneClickBuilding.value = false;
  }
};

const handleExtractRelations = async () => {
  if (!hasNodes.value) {
    message.warning('请先完成节点抽取');
    return;
  }
  if (extractingRelations.value) return;

  extractingRelations.value = true;
  conflictsList.value = [];
  try {
    const res = await extractRelations({
      project_id: projectId.value,
      relation_type: relationType.value,
      model_base: 'llm',
    });

    if (!res.success || res.status !== 200) {
      message.error(res.message || '关系抽取失败');
      return;
    }

    edgesCount.value = res.data?.count ?? 0;
    hasEdges.value = edgesCount.value > 0;
    message.success('关系抽取完成');
  } catch (error: any) {
    message.error(error?.message || '关系抽取失败');
    console.error('handleExtractRelations error:', error);
  } finally {
    extractingRelations.value = false;
  }
};

const refreshStatus = async () => {
  if (!projectId.value) return;
  try {
    const statusRes = await checkExtractionStatus(projectId.value);
    if (!statusRes.success) return;
    hasNodes.value = statusRes.has_nodes;
    hasEdges.value = statusRes.has_edges;

    if (hasNodes.value) {
      const nodesRes = await getNodesByProject(projectId.value);
      if (nodesRes.success && nodesRes.data) {
        nodesCount.value = nodesRes.data.count;
      }
    }
    if (hasEdges.value) {
      const edgesRes = await getEdgesByProject(projectId.value);
      if (edgesRes.success && edgesRes.data) {
        edgesCount.value = edgesRes.data.count;
      }
    }
  } catch (error) {
    console.error('refreshStatus error:', error);
  }
};

watch([runId, projectId], () => {
    if (runId.value && projectId.value) {
      hasEdges.value = true;
      refreshNeo4jGraph(false);
    }
  });

  onMounted(async () => {
    console.log('组件挂载，开始加载数据...');
    await refreshProjectAnnouncements();
    await refreshStatus();
    if (runId.value && projectId.value) {
      hasEdges.value = true;
      await refreshNeo4jGraph(false);
    }
  });
</script>

<style scoped lang="scss">
.extract-process-page {
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

.content-wrapper {
  margin-top: 20px;
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

.section-card {
  padding: 12px 4px 4px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;

  h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: #111827;
  }

  p {
    margin: 4px 0 0;
    font-size: 12px;
    color: #6b7280;
  }
}

.section-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 13px;
  color: #4b5563;
  margin-top: 8px;
}

.status-item {
  display: flex;
  align-items: center;

  .label {
    color: #9ca3af;
    margin-right: 4px;
  }

  .value {
    font-weight: 500;
  }
}

.manage-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.manage-block {
  padding: 8px 0;

  h4 {
    margin: 0 0 4px;
    font-size: 14px;
    font-weight: 600;
  }

  .desc {
    margin: 0 0 8px;
    font-size: 12px;
    color: #6b7280;
  }
}

.manage-actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;

  &.right {
    justify-content: flex-end;
  }
}

/* 复用事件看板表格的主要样式，使视觉风格保持一致 */
.all-events-table {
  flex: 1;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e5e7eb;

  :deep(.n-data-table-base-table) {
    border-radius: 8px;
    overflow: hidden;
  }

  :deep(.n-data-table-th) {
    background: #fafafa;
    font-weight: 600;
    color: #111827;
    padding: 12px 16px;
    border-bottom: 1px solid #f0f0f0;
  }

  :deep(.n-data-table-td) {
    padding: 12px 16px;
    border-bottom: 1px solid #f0f0f0;
  }
}

.pagination-container {
  margin-top: 12px;
  padding: 8px 0 0;
  border-top: 1px solid #f0f0f0;
  display: flex;
  justify-content: center;
  width: 100%;
}

.pagination-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  justify-content: center;
}

.page-info {
  min-width: 150px;
  text-align: center;
  font-size: 13px;
  color: #666;
  font-weight: 500;
  padding: 0 12px;
}

@media (max-width: 768px) {
  .extract-process-page {
    padding: 12px;
  }
}
</style> -->

<script setup lang="ts">
  import { computed, onMounted, onBeforeUnmount, ref, watch, h } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import {
    useMessage,
    NTag,
    NIcon,
    NEllipsis,
    NText,
    NCollapseTransition,
    NDescriptions,
    NDescriptionsItem,
    NSpace,
    NButton,
    NSwitch,
    NPagination,
    NProgress,
    NTime,
  } from 'naive-ui';
  import type { DataTableColumns, DataTableRowKey } from 'naive-ui';
  import { fetchAllEvents } from '@/api/message/message';
  import { parseStr } from '@/api/time';
  import {
    AddOutline,
    RemoveOutline,
    ScanOutline,
    ExpandOutline,
    ContractOutline,
    ArrowUpOutline,
    TimeOutline,
    AnalyticsOutline,
    BusinessOutline,
    SearchOutline,
  } from '@vicons/ionicons5';
  import {
    EXTRACTION_HISTORY_REFRESH_EVENT,
    getProjectBaseInfo,
    getProjectAnnouncements,
    saveSelectData,
    deleteSelectedData,
    checkExtractionStatus,
    previewMasterBuildPath,
    startMasterAgentAsyncTask,
    getMasterAgentTaskStatus,
    getEdgesByProject,
    getExtractionHistoryList,
    getNeo4jGraph,
    getNeo4jGraphByRun,
    getNodesByProject,
    getWorkflowReportByRun,
    analyzeQualityReportAI,
    type ProjectAnnouncementItem,
    type WorkflowMeta,
  } from '@/api/kg/extract';
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
  import { useUserStore } from '@/store/modules/user';

  interface QualityReport {
    grade?: string;
    overall_score?: number | string;
    node_property_fill_rate?: number | string;
    edge_property_fill_rate?: number | string;
    semantic_relation_ratio?: number | string;
    conflict_count?: number | string;
  }

  const route = useRoute();
  const router = useRouter();
  const message = useMessage();
  const userStore = useUserStore();
  const canViewQualityReport = computed(() => true);
  const canUseAiQualityAnalysis = computed(() => Boolean(userStore.isAdmin));

  const projectId = computed(() => String(route.params.projectId || ''));
  const runId = computed(() => String(route.query.run || ''));
  const currentProjectName = ref('');

  const currentStep = ref(1);

  // 样本 / 公告
  const projectAnnouncements = ref<ProjectAnnouncementItem[]>([]);
  const loadingProjectAnnouncements = ref(false);
  const announcementManageVisible = ref(false);
  const announcementIdsInput = ref('');
  const savingAnnouncements = ref(false);
  const deletingAnnouncements = ref(false);
  const checkedAnnouncementIds = ref<string[]>([]);
  const checkedProjectAnnouncementIds = ref<DataTableRowKey[]>([]);
  const autoDetectedNewSampleIds = ref<string[]>([]);
  const lastBuildSampleIds = ref<Set<string>>(new Set());

  // 分页相关
  const announcementPage = ref(1);
  const announcementPageSize = ref(5); // 每页显示5条

  // 计算当前页的数据
  const paginatedAnnouncements = computed(() => {
    const start = (announcementPage.value - 1) * announcementPageSize.value;
    const end = start + announcementPageSize.value;
    return projectAnnouncements.value.slice(start, end);
  });

  // 操作库样本
  interface TextSampleItem {
    id?: string;
    index: number;
    title?: string;
    content?: string;
    publishTime?: string;
    summary?: string;
    stock_num?: string;
    event_type?: string;
    event_subtype?: string;
    impact_level?: string;
    sentiment?: string;
  }

  const selectFromRepoVisible = ref(false);
  const repoSamples = ref<TextSampleItem[]>([]);
  const loadingRepoSamples = ref(false);
  const repoPage = ref(1);
  const repoPageSize = ref(10);
  const repoTotal = ref(0);
  const checkedRepoKeys = ref<(string | number)[]>([]);
  const savingFromRepo = ref(false);

  // 操作库（对话框）筛选面板状态（与事件看板一致）
  const repoSearchExpanded = ref(false);
  const repo_search_stock_code = ref<string>('');
  const getDefaultRepoTimeRange = (): [number, number] => {
    const now = Date.now();
    return [now - 7 * 24 * 60 * 60 * 1000, now];
  };

  const repo_search_event_type = ref<string[]>(['all']);
  const repo_search_keyword = ref<string>('');
  const repo_search_time_range = ref<[number, number] | null>(getDefaultRepoTimeRange());
  const repoSortField = ref<string>('event_time');
  const repoSortOrder = ref<1 | -1>(-1);
  const repoHeaderFilters = ref<{
    event_type: string[];
    impact_level: string[];
    sentiment: string[];
  }>({
    event_type: [],
    impact_level: [],
    sentiment: [],
  });

  // 抽取状态
  const nodesCount = ref(0);
  const hasNodes = ref(false);

  const oneClickBuilding = ref(false);
  const buildRunMode = ref<'full' | 'incremental'>('full');
  const edgesCount = ref(0);
  const hasEdges = ref(false);

  /** 一键构建进度弹窗 */
  const buildProgressModalVisible = ref(false);
  const buildProgressPercent = ref(0);
  const buildPhase = ref<'nodes' | 'relations'>('nodes');
  const buildProgressLabel = ref('');
  const latestQualityReport = ref<QualityReport | null>(null);
  const latestWorkflowMeta = ref<WorkflowMeta | null>(null);
  const activeWorkflowRunId = ref('');
  const activeWorkflowReportSource = ref('当前构建返回');
  const workflowReportModalVisible = ref(false);
  const aiAnalysisModalVisible = ref(false);
  const loadingAiAnalysis = ref(false);
  const aiAnalysisText = ref('');
  const aiAnalysisForRunId = ref('');
  const loadingWorkflowReport = ref(false);
  const workflowReportApiUnavailable = ref(false);
  const hasBuildCompleted = ref(false);
  const qualityReportMissing = ref(false);
  const animatedBuildProgressPercent = ref(0);
  let buildProgressRaf: number | null = null;

  const activeMasterBuildTaskId = ref('');
  const activeMasterBuildTaskStatus = ref<'pending' | 'running' | 'success' | 'error' | ''>('');
  const activeMasterBuildTaskRunId = ref('');
  const activeMasterBuildTaskMode = ref<'full' | 'incremental'>('full');
  const taskCompletionNotified = ref(false);
  let masterBuildTaskPollTimer: number | null = null;
  const ACTIVE_MASTER_BUILD_TASK_KEY = 'finkg-active-master-build-task';

  const WORKFLOW_REPORT_CACHE_PREFIX = 'finkg-workflow-report';

  function getWorkflowReportCacheKey(pid: string, rid: string): string {
    return `${WORKFLOW_REPORT_CACHE_PREFIX}:${pid}:${rid}`;
  }

  function persistWorkflowReportCache(pid: string, rid: string, meta: WorkflowMeta) {
    if (!pid || !rid || !meta || typeof meta !== 'object') return;
    try {
      sessionStorage.setItem(
        getWorkflowReportCacheKey(pid, rid),
        JSON.stringify({ workflow_meta: meta, saved_at: Date.now() })
      );
    } catch {
      /* ignore cache write errors */
    }
  }

  function restoreWorkflowReportFromCache(pid: string, rid: string): boolean {
    if (!pid || !rid) return false;
    try {
      const raw = sessionStorage.getItem(getWorkflowReportCacheKey(pid, rid));
      if (!raw) return false;
      const parsed = JSON.parse(raw) as { workflow_meta?: WorkflowMeta };
      const meta = parsed?.workflow_meta;
      if (!meta || typeof meta !== 'object') return false;
      latestWorkflowMeta.value = meta;
      activeWorkflowRunId.value = String(meta.run_id || rid);
      activeWorkflowReportSource.value = '本地缓存回填';
      latestQualityReport.value = normalizeQualityReport(meta.quality_report);
      qualityReportMissing.value = hasBuildCompleted.value && !latestQualityReport.value;
      return true;
    } catch {
      return false;
    }
  }

  /** 抽取结果表格（默认每页 5 条） */
  const nodesTableData = ref<any[]>([]);
  const edgesTableData = ref<any[]>([]);
  const nodeTablePage = ref(1);
  const nodeTablePageSize = ref(5);
  const edgeTablePage = ref(1);
  const edgeTablePageSize = ref(5);

  const paginatedNodesTable = computed(() => {
    const start = (nodeTablePage.value - 1) * nodeTablePageSize.value;
    return nodesTableData.value.slice(start, start + nodeTablePageSize.value);
  });

  const paginatedEdgesTable = computed(() => {
    const start = (edgeTablePage.value - 1) * edgeTablePageSize.value;
    return edgesTableData.value.slice(start, start + edgeTablePageSize.value);
  });

  function onNodePageSizeChange(size: number) {
    nodeTablePageSize.value = size;
    nodeTablePage.value = 1;
  }

  function onEdgePageSizeChange(size: number) {
    edgeTablePageSize.value = size;
    edgeTablePage.value = 1;
  }

  const buildPhaseTitle = computed(() =>
    buildPhase.value === 'nodes' ? '节点抽取进度' : '关系抽取进度'
  );

  const buildProgressColor = computed(() =>
    buildPhase.value === 'nodes' ? '#0ea5e9' : '#10b981'
  );

  const isNodeStageDone = computed(() =>
    buildPhase.value === 'relations' || buildProgressPercent.value >= 100
  );

  const isRelationStageDone = computed(() =>
    buildPhase.value === 'relations' && buildProgressPercent.value >= 100
  );

  const buildStageHint = computed(() => {
    if (buildProgressPercent.value >= 100) return '图谱构建完成，正在回填最新图数据。';
    return buildPhase.value === 'nodes'
      ? '正在从样本中抽取节点并补全关键属性。'
      : '正在构建关系、冲突检测并组装图结构。';
  });

  const canReopenBuildProgress = computed(
    () => Boolean(activeMasterBuildTaskId.value && !buildProgressModalVisible.value)
  );

  function showBuildProgressModal() {
    if (!activeMasterBuildTaskId.value) {
      return;
    }
    buildProgressModalVisible.value = true;
    void pollMasterBuildTaskStatus(activeMasterBuildTaskId.value);
  }

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

  interface WorkflowMetaFormItem {
    label: string;
    value: string;
  }

  interface WorkflowMetaFormSection {
    key: string;
    title: string;
    items: WorkflowMetaFormItem[];
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
          { label: '深度冲突检查', path: 'build_plan.enable_conflict_deep_check' },
          { label: '严格陈旧清理', path: 'build_plan.strict_stale_cleanup' },
          { label: '图优化开关', path: 'build_plan.enable_graph_optimization' },
          { label: '孤立点修复', path: 'build_plan.enable_isolated_repair' },
        ],
        wm
      ),
      buildWorkflowMetaSection(
        'quality-score',
        '质量评分',
        [
          { label: '综合得分', path: 'quality_score.overall_score' },
          { label: '覆盖度', path: 'quality_score.dimensions.coverage', formatter: formatPercentFromRatio },
          { label: '一致性', path: 'quality_score.dimensions.consistency', formatter: formatPercentFromRatio },
          { label: '时效性', path: 'quality_score.dimensions.freshness', formatter: formatPercentFromRatio },
          { label: '结构完整性', path: 'quality_score.dimensions.structural', formatter: formatPercentFromRatio },
          { label: '节点数', path: 'quality_score.metrics.node_count' },
          { label: '关系数', path: 'quality_score.metrics.edge_count' },
          { label: '样本数', path: 'quality_score.metrics.sample_count' },
          { label: '冲突数', path: 'quality_score.metrics.conflict_count' },
          {
            label: '样本锚定覆盖率',
            path: 'quality_score.metrics.sample_anchor_coverage',
            formatter: formatPercentFromRatio,
          },
        ],
        wm
      ),
      buildWorkflowMetaSection(
        'graph-opt',
        '图优化执行结果',
        [
          { label: '是否启用', path: 'graph_enrichment.graph_optimization.enabled' },
          { label: '是否发生变更', path: 'graph_enrichment.graph_optimization.changed' },
          {
            label: '移除无效/重复关系',
            path: 'graph_enrichment.graph_optimization.removed_invalid_or_duplicate_edges',
          },
          {
            label: '移除冲突修剪关系',
            path: 'graph_enrichment.graph_optimization.removed_conflict_pruned_edges',
          },
          {
            label: '新增孤立点修复关系',
            path: 'graph_enrichment.graph_optimization.added_isolated_repair_edges',
          },
          { label: '优化前关系数', path: 'graph_enrichment.graph_optimization.edge_count_before' },
          { label: '优化后关系数', path: 'graph_enrichment.graph_optimization.edge_count_after' },
        ],
        wm
      ),
      buildWorkflowMetaSection(
        'sample-delta',
        '样本增量变化',
        [
          { label: '增量模式', path: 'sample_delta.mode' },
          { label: '新增样本数', path: 'sample_delta.added_sample_ids.length' },
          { label: '移除样本数', path: 'sample_delta.removed_sample_ids.length' },
          { label: '触达样本数', path: 'sample_delta.touched_sample_ids.length' },
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

  const animateBuildProgressTo = (nextValue: number) => {
    const target = Math.max(0, Math.min(100, Number(nextValue) || 0));
    if (buildProgressRaf !== null) {
      window.cancelAnimationFrame(buildProgressRaf);
      buildProgressRaf = null;
    }
    const from = animatedBuildProgressPercent.value;
    const delta = target - from;
    if (Math.abs(delta) < 0.1) {
      animatedBuildProgressPercent.value = Math.round(target);
      return;
    }
    const duration = Math.max(260, Math.min(900, Math.abs(delta) * 14));
    const start = performance.now();

    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      animatedBuildProgressPercent.value = Math.round(from + delta * eased);
      if (t < 1) {
        buildProgressRaf = window.requestAnimationFrame(tick);
      } else {
        buildProgressRaf = null;
      }
    };
    buildProgressRaf = window.requestAnimationFrame(tick);
  };

  watch(
    buildProgressPercent,
    (v) => {
      animateBuildProgressTo(v);
    },
    { immediate: true }
  );

  function getSampleContentByAnyId(sampleIdRaw: unknown): string {
    const rawList = Array.isArray(sampleIdRaw) ? sampleIdRaw : [sampleIdRaw];
    const ids = rawList
      .map((id) => String(id ?? '').trim())
      .filter((id) => id.length > 0);

    for (const sid of ids) {
      const matched = projectAnnouncements.value.find((item) => String(item?.id ?? '').trim() === sid);
      if (matched) {
        const text = getEventSummary(matched);
        if (text && String(text).trim()) return String(text).trim();
      }
    }

    return '';
  }

  function getNodeNameByAnyId(nodeIdRaw: unknown): string {
    const rawList = Array.isArray(nodeIdRaw) ? nodeIdRaw : [nodeIdRaw];
    const ids = rawList
      .map((id) => String(id ?? '').trim())
      .filter((id) => id.length > 0);

    for (const nid of ids) {
      const matched = nodesTableData.value.find((item) => String(item?.id ?? '').trim() === nid);
      if (!matched) continue;
      const nodeName =
        String(matched?.name ?? '').trim() ||
        String(matched?.displayName ?? '').trim() ||
        String(matched?.value ?? '').trim() ||
        String(matched?.rawValue ?? '').trim() ||
        String(matched?.key ?? '').trim();
      if (nodeName) return nodeName;
    }

    return '';
  }

  const extractedNodesColumns: DataTableColumns<any> = [
    { title: '节点 ID', key: 'id', width: 200, ellipsis: { tooltip: true } },
    {
      title: '节点名称',
      key: '_nodeName',
      width: 160,
      ellipsis: { tooltip: true },
      render(row: any) {
        const nodeName =
          String(row.name ?? '').trim() ||
          String(row.displayName ?? '').trim() ||
          String(row.value ?? '').trim() ||
          String(row.rawValue ?? '').trim() ||
          String(row.key ?? '').trim() ||
          '-';
        return nodeName;
      },
    },
    {
      title: '类型',
      key: 'type',
      width: 72,
      render(row: any) {
        return String(row.type) === '1' ? '事件' : '实体';
      },
    },
    {
      title: '关键属性',
      key: '_coreAttr',
      minWidth: 320,
      ellipsis: { tooltip: true },
      render(row: any) {
        const attrName = String(row.key ?? '').trim() || '未命名属性';
        const attrValue = String(row.value ?? row.rawValue ?? row.id ?? '-').trim() || '-';
        return h('div', { class: 'node-attr-cell' }, [
          h(
            NTag,
            {
              size: 'small',
              type: 'info',
              bordered: false,
              round: true,
              class: 'node-attr-key-tag',
            },
            { default: () => attrName }
          ),
          h('span', { class: 'node-attr-separator' }, '：'),
          h('span', { class: 'node-attr-value', title: attrValue }, attrValue),
        ]);
      },
    },
    {
      title: '上下文 / 样本',
      key: '_ctx',
      ellipsis: { tooltip: true },
      render(row: any) {
        const p = row.properties || {};
        const sampleText = getSampleContentByAnyId(
          p.sample_id ?? p.sampleId ?? p.announcement_id ?? p.announcementId
        );
        if (sampleText) return sampleText;

        const c = p.context || row.context || '';
        return c ? String(c).slice(0, 120) : '-';
      },
    },
  ];

  const extractedEdgesColumns: DataTableColumns<any> = [
    { title: '关系 ID', key: 'id', width: 180, ellipsis: { tooltip: true } },
    {
      title: '起点',
      key: 'from',
      width: 160,
      ellipsis: { tooltip: true },
      render(row: any) {
        const nameFromEdge =
          String(row.from_name ?? '').trim() ||
          String(row.fromName ?? '').trim() ||
          String(row.source_name ?? '').trim() ||
          String(row.sourceName ?? '').trim();
        const nameFromNode = getNodeNameByAnyId(row.from ?? row.source);
        return nameFromEdge || nameFromNode || '未匹配节点';
      },
    },
    {
      title: '终点',
      key: 'to',
      width: 160,
      ellipsis: { tooltip: true },
      render(row: any) {
        const nameFromEdge =
          String(row.to_name ?? '').trim() ||
          String(row.toName ?? '').trim() ||
          String(row.target_name ?? '').trim() ||
          String(row.targetName ?? '').trim();
        const nameFromNode = getNodeNameByAnyId(row.to ?? row.target);
        return nameFromEdge || nameFromNode || '未匹配节点';
      },
    },
    { title: '类型', key: 'type', width: 100, ellipsis: { tooltip: true } },
    { title: '描述', key: 'value', width: 120, ellipsis: { tooltip: true } },
    {
      title: '依据',
      key: '_ev',
      ellipsis: { tooltip: true },
      render(row: any) {
        const c = (row.properties || {}).context;
        return c ? String(c).slice(0, 160) : '-';
      },
    },
  ];

  // 冲突检测（一键构建返回）
  const conflictsList = ref<any[]>([]);

  function pickText(raw: Record<string, any>, keys: string[]): string {
    for (const key of keys) {
      const value = raw[key];
      if (value === undefined || value === null) continue;
      const text = String(value).trim();
      if (text) return text;
    }
    return '';
  }

  function toConflictType(rawType: string, message: string): 'node' | 'edge' | 'other' {
    const t = String(rawType || '').toLowerCase();
    const m = String(message || '').toLowerCase();
    if (t.includes('node') || t.includes('节点') || m.includes('节点')) return 'node';
    if (
      t.includes('edge') ||
      t.includes('relation') ||
      t.includes('关系') ||
      t.includes('边') ||
      m.includes('关系')
    ) {
      return 'edge';
    }
    return 'other';
  }

  function normalizeConflictItem(item: any, index: number, source: 'runtime' | 'workflow') {
    const raw = item && typeof item === 'object' ? (item as Record<string, any>) : {};
    const message = pickText(raw, ['message', 'reason', 'description', 'detail']) || '-';
    const type = pickText(raw, ['type', 'conflict_type', 'category']) || '未分类';
    const from = pickText(raw, ['from', 'source', 'source_node', 'from_node', 'node_a']) || '-';
    const to = pickText(raw, ['to', 'target', 'target_node', 'to_node', 'node_b']) || '-';
    const relation =
      pickText(raw, ['relation', 'relation_type', 'edge', 'edge_type', 'predicate']) || '-';
    const level = pickText(raw, ['level', 'severity', 'risk_level']) || 'medium';
    const evidence = pickText(raw, ['evidence', 'context', 'trace', 'sample_id']) || '-';
    const normalizedType = toConflictType(type, message);

    return {
      id: `${source}-${index}-${type}-${from}-${to}`,
      conflictType: normalizedType,
      type,
      from,
      to,
      relation,
      message,
      level,
      evidence,
      source,
      raw,
    };
  }

  function extractWorkflowConflicts(meta: any): any[] {
    const m = meta && typeof meta === 'object' ? (meta as Record<string, any>) : {};
    const candidates: any[] = [
      m.conflicts,
      m.conflict_list,
      m.conflict_report,
      m.conflict_detection,
      m.graph,
      m.stats,
      m.result,
    ];

    for (const candidate of candidates) {
      if (!candidate) continue;
      if (Array.isArray(candidate)) return candidate;
      if (typeof candidate === 'object') {
        if (Array.isArray((candidate as any).conflicts)) return (candidate as any).conflicts;
        if (Array.isArray((candidate as any).items)) return (candidate as any).items;
        if (Array.isArray((candidate as any).records)) return (candidate as any).records;
      }
    }
    return [];
  }

  const runtimeConflictsNormalized = computed(() =>
    (conflictsList.value || []).map((item, index) => normalizeConflictItem(item, index, 'runtime'))
  );

  const workflowConflictsNormalized = computed(() => {
    const extracted = extractWorkflowConflicts(latestWorkflowMeta.value);
    return extracted.map((item, index) => normalizeConflictItem(item, index, 'workflow'));
  });

  const displayConflictsList = computed(() => {
    const merged = [...runtimeConflictsNormalized.value, ...workflowConflictsNormalized.value];
    const seen = new Set<string>();
    return merged.filter((item) => {
      const fp = [item.type, item.from, item.to, item.relation, item.message].join('|');
      if (seen.has(fp)) return false;
      seen.add(fp);
      return true;
    });
  });

  const displayConflictsCount = computed(() => displayConflictsList.value.length);

  function pickConflictCount(meta: unknown): number {
    if (!meta || typeof meta !== 'object') return 0;
    const m = meta as Record<string, any>;
    const candidates = [
      m?.conflict_count,
      m?.quality_report?.conflict_count,
      m?.quality_report?.stats?.conflict_count,
      m?.quality_score?.metrics?.conflict_count,
      m?.quality_score?.conflict_count,
      m?.stats?.conflict_count,
    ];
    for (const c of candidates) {
      const n = Number(c);
      if (Number.isFinite(n) && n > 0) return Math.floor(n);
    }
    return 0;
  }

  const reportedConflictCount = computed(() => pickConflictCount(latestWorkflowMeta.value));
  const totalConflictCount = computed(() => Math.max(displayConflictsCount.value, reportedConflictCount.value));

  const conflictSummary = computed(() => {
    let node = 0;
    let edge = 0;
    let other = 0;
    for (const item of displayConflictsList.value) {
      if (item.conflictType === 'node') node += 1;
      else if (item.conflictType === 'edge') edge += 1;
      else other += 1;
    }
    if (displayConflictsCount.value === 0 && totalConflictCount.value > 0) {
      other = totalConflictCount.value;
    }
    return { node, edge, other };
  });

  const conflictsColumns: DataTableColumns<any> = [
    {
      title: '类别',
      key: 'conflictType',
      width: 100,
      render(row: any) {
        const labelMap: Record<string, string> = {
          node: '节点冲突',
          edge: '关系冲突',
          other: '其他冲突',
        };
        return labelMap[row.conflictType] || '其他冲突';
      },
    },
    { title: '类型', key: 'type', width: 140, ellipsis: { tooltip: true } },
    { title: '起始节点', key: 'from', width: 120, ellipsis: { tooltip: true } },
    { title: '目标节点', key: 'to', width: 120, ellipsis: { tooltip: true } },
    { title: '说明', key: 'message', ellipsis: { tooltip: true } },
  ];

  const loadingGraph = ref(false);
  const graphNodesCount = ref(0);
  const graphEdgesCount = ref(0);
  const graphPreviewRef = ref<HTMLElement | null>(null);
  const graphChartRef = ref<HTMLElement | null>(null);
  const graphZoomLevel = ref(1);
  const isGraphFullscreen = ref(false);
  let graphChart: echarts.ECharts | null = null;
  let pendingGraphFrame: number | null = null;
  let pendingGraphTimer: number | null = null;
  let graphOptionApplying = false;
  let queuedGraphOption: any = null;
  let graphRefreshSeq = 0;

  const GRAPH_SERIES_ID = 'kg-preview-series';
  const GRAPH_MIN_ZOOM = 0.25;
  const GRAPH_MAX_ZOOM = 4;

  const nodeStatusText = computed(() => {
    if (oneClickBuilding.value) return '一键构建中...';
    if (hasNodes.value) return '已完成节点抽取';
    return '尚未抽取节点';
  });

  const edgeStatusText = computed(() => {
    if (oneClickBuilding.value) return '一键构建中...';
    if (hasEdges.value) return '已完成关系抽取';
    return '尚未抽取关系';
  });

  const graphStatusText = computed(() => {
    if (loadingGraph.value) return '正在加载图谱...';
    if (graphNodesCount.value || graphEdgesCount.value) return '图谱已生成';
    return '暂无图谱数据';
  });

  function renderNeo4jGraph(nodes: any[], edges: any[]) {
    if (!graphChartRef.value) return;
    if (!graphChart) {
      graphChart = echarts.init(graphChartRef.value);
      graphChart.on('graphroam', syncGraphZoomFromChart);
    }

    const rawNodes = (nodes || [])
      .map((n: any) => {
        const id = String(n?.id ?? n?.key ?? n?.value ?? '').trim();
        return id ? { ...n, id } : null;
      })
      .filter((n: any) => !!n);

    const nodeById = new Map<string, any>();
    let duplicateNodeIdCount = 0;
    rawNodes.forEach((n: any) => {
      const id = String(n.id);
      if (nodeById.has(id)) {
        duplicateNodeIdCount += 1;
        return;
      }
      nodeById.set(id, n);
    });
    const normalizedNodes = Array.from(nodeById.values());

    const nodeMap = new Map(normalizedNodes.map((n: any) => [String(n.id), n]));

    const rawEdges = (edges || [])
      .map((e: any, index: number) => {
        const source = String(e?.from ?? e?.source ?? '').trim();
        const target = String(e?.to ?? e?.target ?? '').trim();
        if (!source || !target) return null;
        if (!nodeMap.has(source) || !nodeMap.has(target)) return null;
        return {
          ...e,
          id: e?.id || `edge_${index}_${source}_${target}`,
          from: source,
          to: target,
        };
      })
      .filter((e: any) => !!e);

    const edgeById = new Map<string, any>();
    let duplicateEdgeIdCount = 0;
    rawEdges.forEach((e: any, idx: number) => {
      const baseId = String(e.id || '').trim() || `edge_auto_${idx}_${e.from}_${e.to}`;
      let eid = baseId;
      let suffix = 1;
      while (edgeById.has(eid)) {
        duplicateEdgeIdCount += 1;
        suffix += 1;
        eid = `${baseId}__${suffix}`;
      }
      edgeById.set(eid, { ...e, id: eid });
    });
    const normalizedEdges = Array.from(edgeById.values());

    const droppedNodeCount = Math.max(0, (nodes || []).length - normalizedNodes.length);
    const droppedEdgeCount = Math.max(0, (edges || []).length - normalizedEdges.length);
    console.info('[extract/graph] render normalize:', {
      inputNodes: (nodes || []).length,
      inputEdges: (edges || []).length,
      normalizedNodes: normalizedNodes.length,
      normalizedEdges: normalizedEdges.length,
      droppedNodeCount,
      droppedEdgeCount,
      duplicateNodeIdCount,
      duplicateEdgeIdCount,
      runId: runId.value || null,
      projectId: projectId.value || null,
    });

    if (!normalizedNodes.length) {
      graphChart.clear();
      return;
    }

    const degreeMap = new Map<string, number>();
    normalizedEdges.forEach((e: any) => {
      const source = String(e.from || '');
      const target = String(e.to || '');
      if (source) degreeMap.set(source, (degreeMap.get(source) || 0) + 1);
      if (target) degreeMap.set(target, (degreeMap.get(target) || 0) + 1);
    });

    const visualCategoryNames = sortVisualCategoryNames(
      Array.from(new Set(normalizedNodes.map((n: any) => resolveNodeVisualCategory(n))))
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

    const nodeNameCounter = new Map<string, number>();
    const data = normalizedNodes.map((n: any) => {
      const basicCategory = normalizeNodeCategoryFromNode(n);
      const categoryName = resolveNodeVisualCategory(n);
      const degree = degreeMap.get(String(n.id)) || 0;
      const baseSize = basicCategory === 1 ? 44 : 32;
      const symbolSize = Math.min(64, baseSize + Math.sqrt(degree) * 3.2);
      const displayName = normalizeNodeDisplayName(n);
      const used = nodeNameCounter.get(displayName) || 0;
      nodeNameCounter.set(displayName, used + 1);
      const uniqueName = used > 0 ? `${displayName} (${used + 1})` : displayName;

      return {
        id: n.id,
        name: uniqueName,
        displayName,
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
          borderColor: 'rgba(241, 245, 249, 0.92)',
          borderWidth: 1.6,
          shadowBlur: 16,
          shadowColor: 'rgba(15, 23, 42, 0.55)',
        },
      };
    });

    const links = normalizedEdges.map((e: any) => {
      const fromNode = nodeMap.get(e.from);
      const toNode = nodeMap.get(e.to);
      const displayLabel = normalizeEdgeDisplayLabel(e, fromNode, toNode);
      return {
        id: e.id,
        source: e.from,
        target: e.to,
        value: e.value || e.type || '',
        eventRel: e.eventRel || '',
        type: e.type || '',
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
          width: 1.4,
          curveness: 0.12,
        },
      };
    });

    const nodeCount = data.length;
    const repulsion = nodeCount <= 30 ? 520 : nodeCount <= 90 ? 360 : 250;
    const edgeLength = nodeCount <= 30 ? [120, 220] : nodeCount <= 90 ? [90, 180] : [60, 130];

    const nextOption = {
      backgroundColor: 'transparent',
      tooltip: {
        backgroundColor: 'rgba(255, 255, 255, 0.96)',
        borderWidth: 1,
        borderColor: 'rgba(148, 163, 184, 0.45)',
        textStyle: {
          color: '#0f172a',
          fontSize: 12,
        },
        extraCssText: 'box-shadow:0 10px 20px rgba(15, 23, 42, 0.12);',
        formatter: (params: any) => {
          if (params.dataType === 'edge') {
            return `关系：${params.data?.displayLabel || params.data?.value || '-'}<br/>起点：${params.data?.source || '-'}<br/>终点：${params.data?.target || '-'}`;
          }
          const d = params.data || {};
          return `节点：${d.displayName || d.name || '-'}<br/>类别：${d.categoryName || '-'}<br/>Key：${d.key || '-'}<br/>连接数：${d.degree || 0}`;
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
            color: '#334155',
            fontSize: 12,
            formatter: (params: any) => {
              const name = String(params.data?.displayName || params.data?.name || '-');
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
            width: 1.2,
            opacity: 0.5,
          },
          emphasis: {
            focus: 'adjacency',
            scale: true,
            lineStyle: {
              width: 2.6,
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
              opacity: 0.16,
            },
            lineStyle: {
              opacity: 0.06,
            },
            label: {
              opacity: 0.06,
            },
          },
          select: {
            itemStyle: {
              borderWidth: 2.4,
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
            text: '拖拽节点可调整布局，悬停可聚焦邻接关系',
            fill: 'rgba(71, 85, 105, 0.9)',
            font: '12px sans-serif',
          },
          silent: true,
        },
      ],
    };

    if (pendingGraphFrame !== null) {
      window.cancelAnimationFrame(pendingGraphFrame);
      pendingGraphFrame = null;
    }
    pendingGraphFrame = window.requestAnimationFrame(() => {
      queuedGraphOption = nextOption;
      if (pendingGraphTimer !== null) {
        window.clearTimeout(pendingGraphTimer);
      }
      pendingGraphTimer = window.setTimeout(() => {
        if (!graphChart || !queuedGraphOption) return;
        if (graphOptionApplying) return;
        graphOptionApplying = true;
        const optionToApply = queuedGraphOption;
        queuedGraphOption = null;
        try {
          graphChart.setOption(optionToApply, true);
          graphZoomLevel.value = 1;
        } catch (setOptionErr: any) {
          console.error('[extract/graph] setOption failed:', setOptionErr, {
            nodeCount: normalizedNodes.length,
            edgeCount: normalizedEdges.length,
            runId: runId.value || null,
            projectId: projectId.value || null,
          });
          graphChart.clear();
        } finally {
          graphOptionApplying = false;
        }
      }, 16);
      pendingGraphFrame = null;
    });
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
    } catch (e) {
      console.error('toggleGraphFullscreen error:', e);
    }
  }

  async function refreshNeo4jGraph(showSuccess = false, targetRunId?: string) {
    if (!projectId.value) return;
    const seq = ++graphRefreshSeq;
    loadingGraph.value = true;
    try {
      const effectiveRunId = String(targetRunId || runId.value || '').trim();
      console.info('[extract/graph] refresh request:', {
        seq,
        projectId: projectId.value,
        runId: effectiveRunId || null,
      });
      const res = effectiveRunId
        ? await getNeo4jGraphByRun(projectId.value, effectiveRunId)
        : await getNeo4jGraph(projectId.value);
      if (seq !== graphRefreshSeq) return;
      if (!res.success || res.status !== 200) {
        if (showSuccess) message.error(res.message || '获取 Neo4j 图谱失败');
        return;
      }
      const nodes = res.data?.nodes || [];
      const edges = res.data?.edges || [];
      console.info('[extract/graph] refresh response:', {
        seq,
        projectId: projectId.value,
        runId: effectiveRunId || null,
        success: res.success,
        status: res.status,
        nodes: nodes.length,
        edges: edges.length,
      });
      graphNodesCount.value = nodes.length;
      graphEdgesCount.value = edges.length;
      hasEdges.value = edges.length > 0 || hasEdges.value;
      renderNeo4jGraph(nodes, edges);
      if (showSuccess) {
        message.success('图谱已更新');
      }
    } catch (error: any) {
      if (seq !== graphRefreshSeq) return;
      console.error('refreshNeo4jGraph error:', error);
      if (showSuccess) message.error(error?.message || '获取 Neo4j 图谱失败');
    } finally {
      if (seq === graphRefreshSeq) {
        loadingGraph.value = false;
      }
    }
  }

  function getEventType(event: any): string {
    if (event?.event_type) return event.event_type;
    if (event?.data?.event_type) return event.data.event_type;
    if (event?.type) return event.type;
    if (event?.data?.type) return event.data.type;
    if (event?.eventType) return event.eventType;
    if (event?.data?.eventType) return event.data.eventType;
    if (event?.['事件类型']) return event['事件类型'];
    if (event?.data?.['事件类型']) return event.data['事件类型'];
    if (event?.category) return event.category;
    if (event?.data?.category) return event.data.category;
    if (event?.raw_data?.event_type) return event.raw_data.event_type;
    if (event?.data?.raw_data?.event_type) return event.data.raw_data.event_type;
    return 'unknown';
  }

  function getEventSubtype(event: any): string {
    if (!event) return '';
    if (event.event_subtype) return event.event_subtype;
    if (event.data?.event_subtype) return event.data.event_subtype;
    if (event.eventSubType) return event.eventSubType;
    if (event.data?.eventSubType) return event.data.eventSubType;
    if (event.eventSubtype) return event.eventSubtype;
    if (event.data?.eventSubtype) return event.data.eventSubtype;
    if (event.subtype) return event.subtype;
    if (event.data?.subtype) return event.data.subtype;
    if (event.event_sub_type) return event.event_sub_type;
    if (event.data?.event_sub_type) return event.data.event_sub_type;
    if (event['事件子类']) return event['事件子类'];
    if (event.data?.['事件子类']) return event.data['事件子类'];
    if (event.raw_data?.event_subtype) return event.raw_data.event_subtype;
    if (event.data?.raw_data?.event_subtype) return event.data.raw_data.event_subtype;
    if (event.raw_data?.event_sub_type) return event.raw_data.event_sub_type;
    if (event.data?.raw_data?.event_sub_type) return event.data.raw_data.event_sub_type;
    if (event.raw_data?.['事件子类']) return event.raw_data['事件子类'];
    if (event.data?.raw_data?.['事件子类']) return event.data.raw_data['事件子类'];
    return '';
  }

  function getImpactLevel(event: any): string {
    if (!event) return '';
    if (event.impact_level) return event.impact_level;
    if (event.data?.impact_level) return event.data.impact_level;
    if (event.impactLevel) return event.impactLevel;
    if (event.data?.impactLevel) return event.data.impactLevel;
    if (event.impact) return event.impact;
    if (event.data?.impact) return event.data.impact;
    if (event.severity) return event.severity;
    if (event.data?.severity) return event.data.severity;
    if (event['影响级别']) return event['影响级别'];
    if (event.data?.['影响级别']) return event.data['影响级别'];
    if (event.raw_data?.impact_level) return event.raw_data.impact_level;
    if (event.data?.raw_data?.impact_level) return event.data.raw_data.impact_level;
    if (event.raw_data?.['影响级别']) return event.raw_data['影响级别'];
    if (event.data?.raw_data?.['影响级别']) return event.data.raw_data['影响级别'];
    return '';
  }

  function getSentiment(event: any): string {
    if (!event) return '';
    if (event.sentiment) return event.sentiment;
    if (event.data?.sentiment) return event.data.sentiment;
    if (event.sentiment_label) return event.sentiment_label;
    if (event.data?.sentiment_label) return event.data.sentiment_label;
    if (event.emotion) return event.emotion;
    if (event.data?.emotion) return event.data.emotion;
    if (event.polarity) return event.polarity;
    if (event.data?.polarity) return event.data.polarity;
    if (event['情绪']) return event['情绪'];
    if (event.data?.['情绪']) return event.data['情绪'];
    if (event['情感倾向']) return event['情感倾向'];
    if (event.data?.['情感倾向']) return event.data['情感倾向'];
    if (event.raw_data?.sentiment) return event.raw_data.sentiment;
    if (event.data?.raw_data?.sentiment) return event.data.raw_data.sentiment;
    if (event.raw_data?.['情绪']) return event.raw_data['情绪'];
    if (event.data?.raw_data?.['情绪']) return event.data.raw_data['情绪'];
    return '';
  }

  function formatEventType(type: string) {
    const typeMap: Record<string, string> = {
      macro: '宏观',
      industry: '行业',
      sentiment: '情绪',
      trading: '个股',
      unknown: '未知',
    };
    return typeMap[type] || type || '-';
  }

  function formatDateTime(dateString: string) {
    if (!dateString) return '-';
    try {
      const date = new Date(dateString);
      return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      });
    } catch {
      return dateString;
    }
  }

  function formatEventSubtype(subtype: string) {
    const subtypeMap: Record<string, string> = {
      macro_综合宏观新闻: '综合宏观',
      macro_资本市场: '资本市场',
      macro_央行政策: '央行政策',
      macro_金融监管: '金融监管',
      macro_经济增长: '经济增长',
      macro_国际局势: '国际局势',
      price_rise_abnormal: '涨幅异常',
      price_fall_abnormal: '跌幅异常',
      rise_consistency_abnormal: '上涨一致',
      fall_consistency_abnormal: '下跌一致',
      leader_fluctuation_abnormal: '龙头异动',
      ma5_cross_up: 'MA5上穿',
      ma5_cross_down: 'MA5下穿',
      ma10_cross_up: 'MA10上穿',
      ma10_cross_down: 'MA10下穿',
      ma20_cross_up: 'MA20上穿',
      ma20_cross_down: 'MA20下穿',
      ma60_cross_up: 'MA60上穿',
      ma60_cross_down: 'MA60下穿',
    };
    return subtypeMap[subtype] || subtype?.replace('macro_', '') || subtype || '-';
  }

  function formatImpactLevel(level: string) {
    const levelMap: Record<string, string> = {
      critical: '极高',
      high: '高',
      medium: '中',
      low: '低',
    };
    return levelMap[level] || level || '中';
  }

  function formatSentiment(sentiment: string) {
    const sentimentMap: Record<string, string> = {
      positive: '正面',
      negative: '负面',
      neutral: '中性',
    };
    return sentimentMap[sentiment] || sentiment || '中性';
  }

  function getEventSummary(item: any): string {
    if (item?.event_description) return item.event_description;
    if (item?.content) return item.content;
    if (item?.summary) return item.summary;
    const rawData = item?.raw_data || {};
    return rawData?.新闻内容 || item?.title || item?.['标题'] || '事件';
  }

  function formatIndustryEventDetail(item: any) {
    const boardName = item.board_name || item.symbol || '';
    const rawData = item.raw_data || {};

    switch (item.event_subtype) {
      case 'price_rise_abnormal':
        return `${boardName}板块出现异常上涨：
          涨幅：${rawData.price_change?.toFixed(2) || '0.00'}%
          成交额：${rawData.total_amount ? (rawData.total_amount / 10000).toFixed(1) : '0.0'}亿元
          上涨家数：${rawData.rise_stocks || 0}/${rawData.total_stocks || 0}`;
      case 'price_fall_abnormal':
        return `${boardName}板块出现异常下跌：
          跌幅：${Math.abs(rawData.price_change || 0).toFixed(2)}%
          领跌股：${rawData.leader_stock || '-'}
          领跌股跌幅：${Math.abs(rawData.leader_change || 0).toFixed(2)}%`;
      case 'leader_fluctuation_abnormal':
        return `${boardName}板块龙头股异动：
          龙头股：${rawData.leader_stock || '-'}
          涨跌幅：${rawData.leader_change?.toFixed(2) || '0.00'}%
          成交量：${rawData.leader_volume ? (rawData.leader_volume / 10000).toFixed(1) : '0.0'}万手`;
      case 'rise_consistency_abnormal':
        return `${boardName}板块上涨一致性异常：
          上涨家数：${rawData.rise_stocks || 0}/${rawData.total_stocks || 0}
          上涨占比：${
            rawData.rise_stocks && rawData.total_stocks
              ? ((rawData.rise_stocks / rawData.total_stocks) * 100).toFixed(1)
              : '0.0'
          }%
          平均涨幅：${rawData.average_rise?.toFixed(2) || '0.00'}%`;
      case 'fall_consistency_abnormal':
        return `${boardName}板块下跌一致性异常：
          净流出：${rawData.net_inflow ? Math.abs(rawData.net_inflow / 10000).toFixed(1) : '0.0'}亿元
          下跌家数占比：${rawData.fall_ratio?.toFixed(1) || '0.0'}%
          平均跌幅：${Math.abs(rawData.average_fall || 0).toFixed(2)}%`;
      default:
        return `${boardName}板块出现异常波动`;
    }
  }

  function formatMoodEventDetail(item: any) {
    const rawData = item.raw_data || {};
    const symbol = item.symbol || '';
    const subtype = item.event_subtype || '';

    switch (subtype) {
      case 'ma5_cross_up':
      case 'ma5_cross_down':
        return `${symbol} MA5均线交叉：
          当前价格：${rawData.real_time_close?.toFixed(2) || '0.00'}元
          MA5均线：${rawData.daily_MA5?.toFixed(2) || '0.00'}元
          偏离度：${Math.abs(rawData.deviation_pct || 0).toFixed(2)}%
          方向：${subtype.includes('up') ? '上穿' : '下穿'}`;
      case 'ma10_cross_up':
      case 'ma10_cross_down':
        return `${symbol} MA10均线交叉：
          当前价格：${rawData.real_time_close?.toFixed(2) || '0.00'}元
          MA10均线：${rawData.daily_MA10?.toFixed(2) || '0.00'}元
          偏离度：${Math.abs(rawData.deviation_pct || 0).toFixed(2)}%
          方向：${subtype.includes('up') ? '上穿' : '下穿'}`;
      case 'ma20_cross_up':
      case 'ma20_cross_down':
        return `${symbol} MA20均线交叉：
          当前价格：${rawData.real_time_close?.toFixed(2) || '0.00'}元
          MA20均线：${rawData.daily_MA20?.toFixed(2) || '0.00'}元
          偏离度：${Math.abs(rawData.deviation_pct || 0).toFixed(2)}%
          方向：${subtype.includes('up') ? '上穿' : '下穿'}`;
      case 'ma60_cross_up':
      case 'ma60_cross_down':
        return `${symbol} MA60均线交叉：
          当前价格：${rawData.real_time_close?.toFixed(2) || '0.00'}元
          MA60均线：${rawData.daily_MA60?.toFixed(2) || '0.00'}元
          偏离度：${Math.abs(rawData.deviation_pct || 0).toFixed(2)}%
          方向：${subtype.includes('up') ? '上穿' : '下穿'}`;
      default:
        return `${symbol} 技术指标异常：
          当前价格：${rawData.real_time_close?.toFixed(2) || '0.00'}元`;
    }
  }

  function prettyJson(obj: any) {
    try {
      return JSON.stringify(obj, null, 2);
    } catch {
      return String(obj);
    }
  }

  // 已选样本表格列：按事件看板同款渲染
  const selectedColumns: DataTableColumns<ProjectAnnouncementItem> = [
    {
      title: '事件类型',
      key: 'event_type',
      width: 100,
      fixed: 'left',
      align: 'center',
      render(row: any) {
        const type = getEventType(row);
        const typeConfig: Record<string, any> = {
          macro: { text: '宏观', color: '#1890ff', bgColor: '#e6f7ff' },
          industry: { text: '行业', color: '#52c41a', bgColor: '#f6ffed' },
          trading: { text: '个股', color: '#722ed1', bgColor: '#f9f0ff' },
          sentiment: { text: '情绪', color: '#fa8c16', bgColor: '#fff7e6' },
          宏观: { text: '宏观', color: '#1890ff', bgColor: '#e6f7ff' },
          行业: { text: '行业', color: '#52c41a', bgColor: '#f6ffed' },
          个股: { text: '个股', color: '#722ed1', bgColor: '#f9f0ff' },
          情绪: { text: '情绪', color: '#fa8c16', bgColor: '#fff7e6' },
        };
        const config = typeConfig[type] || { text: type || '-', color: '#666', bgColor: '#f5f5f5' };
        return h(
          NTag,
          {
            size: 'small',
            type: 'default',
            style: {
              background: config.bgColor,
              color: config.color,
              borderColor: config.color + '30',
              fontWeight: '500',
            },
          },
          { default: () => config.text }
        );
      },
    },
    {
      title: '事件时间',
      key: 'event_time',
      width: 120,
      align: 'center',
      render(row: any) {
        return h('div', { class: 'event-time-cell' }, [
          h(
            NIcon,
            { size: '14', style: { marginRight: '4px', color: '#1890ff' } },
            { default: () => h(TimeOutline) }
          ),
          h('span', formatDateTime(row.event_time || row.publishTime || row.eventTime || '')),
        ]);
      },
    },
    {
      title: '事件摘要',
      key: 'summary',
      width: 300,
      align: 'center',
      ellipsis: { tooltip: true },
      render(row: any) {
        const summary = getEventSummary(row);
        return h('div', { class: 'description-preview' }, [
          h(NEllipsis, { tooltip: false, lineClamp: 3 }, { default: () => summary }),
        ]);
      },
    },
    {
      title: '事件子类',
      key: 'event_subtype',
      width: 120,
      align: 'center',
      render(row: any) {
        const subtype = formatEventSubtype(row.event_subtype || row.eventSubType || '');
        return h(
          'span',
          {
            style: {
              fontSize: '12px',
              padding: '2px 6px',
              background: '#f0f0f0',
              borderRadius: '3px',
            },
          },
          subtype
        );
      },
    },
    {
      title: '影响级别',
      key: 'impact_level',
      width: 80,
      align: 'center',
      render(row: any) {
        const level = row.impact_level || row.impactLevel || 'medium';
        const levelMap: Record<string, any> = {
          critical: { text: '极高', class: 'level-critical', color: '#ff4d4f' },
          high: { text: '高', class: 'level-high', color: '#fa541c' },
          medium: { text: '中', class: 'level-medium', color: '#fa8c16' },
          low: { text: '低', class: 'level-low', color: '#d9d9d9' },
        };
        const config = levelMap[level] || {
          text: formatImpactLevel(level),
          class: '',
          color: '#666',
        };
        return h(
          'div',
          {
            class: `impact-level ${config.class}`,
            style: {
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '2px 8px',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: '600',
              background: config.color + '10',
              color: config.color,
              border: `1px solid ${config.color}30`,
            },
          },
          config.text
        );
      },
    },
    {
      title: '情感',
      key: 'sentiment',
      width: 80,
      align: 'center',
      render(row: any) {
        let sentiment = row.sentiment || 'neutral';
        const type = getEventType(row);
        if (!row.sentiment) {
          if (type === 'industry' && row.event_subtype?.includes('rise')) sentiment = 'positive';
          else if (type === 'industry' && row.event_subtype?.includes('fall'))
            sentiment = 'negative';
        }
        const sentimentMap: Record<string, any> = {
          positive: { text: '正面', class: 'sentiment-positive', color: '#52c41a' },
          negative: { text: '负面', class: 'sentiment-negative', color: '#ff4d4f' },
          neutral: { text: '中性', class: 'sentiment-neutral', color: '#666' },
        };
        const config = sentimentMap[sentiment] || {
          text: formatSentiment(sentiment),
          class: '',
          color: '#666',
        };
        return h(
          'div',
          {
            class: `sentiment ${config.class}`,
            style: {
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '2px 8px',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: '600',
              background: config.color + '10',
              color: config.color,
              border: `1px solid ${config.color}30`,
            },
          },
          config.text
        );
      },
    },
    {
      title: '相关标的',
      key: 'symbol',
      width: 120,
      align: 'center',
      render(row: any) {
        const symbol = row.symbol || row.stock_num || row.stockCode || '-';
        return h('div', { class: 'symbol-cell' }, [
          h(
            NIcon,
            { size: '14', style: { marginRight: '4px', color: '#165dff' } },
            { default: () => h(BusinessOutline) }
          ),
          h(
            'span',
            {
              class: 'symbol-text',
              style: {
                fontFamily: "'SFMono-Regular', Consolas, monospace",
                fontSize: '12px',
                fontWeight: '500',
                padding: '2px 6px',
                background: 'rgba(22, 93, 255, 0.05)',
                borderRadius: '3px',
                color: '#165dff',
                border: '1px solid rgba(22, 93, 255, 0.1)',
              },
            },
            symbol
          ),
        ]);
      },
    },
  ];

  const selectedColumnsWithSelection: DataTableColumns<ProjectAnnouncementItem> = [
    {
      type: 'selection',
      width: 50,
      fixed: 'left',
    },
    ...selectedColumns,
  ];

  const manageColumns: DataTableColumns<ProjectAnnouncementItem> = [
    {
      type: 'selection',
    },
    ...selectedColumns,
  ];

  const rowKey = (row: ProjectAnnouncementItem): DataTableRowKey => {
    const anyRow = row as any;
    return String(row?.id || anyRow?._id || anyRow?.announcement_id || row?.index || '');
  };

  function resolveRepoImpactLevel(row: any): string {
    return String(getImpactLevel(row) || 'medium');
  }

  function resolveRepoSentiment(row: any): string {
    const direct = String(getSentiment(row) || '').trim();
    if (direct) return direct;
    const eventType = getEventType(row);
    const eventSubtype = getEventSubtype(row);
    if (eventType === 'industry' && eventSubtype?.includes('rise')) return 'positive';
    if (eventType === 'industry' && eventSubtype?.includes('fall')) return 'negative';
    return 'neutral';
  }

  const repoFilteredSamples = computed(() => {
    const typeFilter = repoHeaderFilters.value.event_type[0] || '';
    const impactFilter = repoHeaderFilters.value.impact_level[0] || '';
    const sentimentFilter = repoHeaderFilters.value.sentiment[0] || '';
    return repoSamples.value.filter((row: any) => {
      const rowType = String(getEventType(row) || '').trim();
      const rowImpact = resolveRepoImpactLevel(row);
      const rowSentiment = resolveRepoSentiment(row);
      if (typeFilter && rowType !== typeFilter) return false;
      if (impactFilter && rowImpact !== impactFilter) return false;
      if (sentimentFilter && rowSentiment !== sentimentFilter) return false;
      return true;
    });
  });

  function handleRepoFilters(filters: Record<string, unknown>) {
    const readFilter = (key: string): string[] => {
      const value = filters?.[key];
      if (Array.isArray(value)) {
        return value.map((x) => String(x || '').trim()).filter(Boolean);
      }
      return [];
    };
    repoHeaderFilters.value = {
      event_type: readFilter('event_type'),
      impact_level: readFilter('impact_level'),
      sentiment: readFilter('sentiment'),
    };
  }

  // 操作库表格列：与事件看板同款渲染（加 selection）
  const repoColumns: DataTableColumns<any> = [
    {
      type: 'selection',
      width: 50,
      fixed: 'left',
    },
    {
      title: '事件类型',
      key: 'event_type',
      filter: true,
      filterOptions: [
        { label: '宏观', value: 'macro' },
        { label: '行业', value: 'industry' },
        { label: '个股', value: 'trading' },
        { label: '情绪', value: 'sentiment' },
      ],
      filterMultiple: false,
      filterOptionValues: repoHeaderFilters.value.event_type,
      width: 126,
      fixed: 'left',
      align: 'center',
      render(row) {
        const type = row.event_type;
        const typeConfig: Record<string, any> = {
          macro: { text: '宏观', color: '#1890ff', bgColor: '#e6f7ff' },
          industry: { text: '行业', color: '#52c41a', bgColor: '#f6ffed' },
          trading: { text: '个股', color: '#722ed1', bgColor: '#f9f0ff' },
          sentiment: { text: '情绪', color: '#fa8c16', bgColor: '#fff7e6' },
        };
        const config = typeConfig[type] || { text: type, color: '#666', bgColor: '#f5f5f5' };
        return h(
          NTag,
          {
            size: 'small',
            type: 'default',
            style: {
              background: config.bgColor,
              color: config.color,
              borderColor: config.color + '30',
              fontWeight: '500',
            },
          },
          { default: () => config.text }
        );
      },
    },
    {
      title: '事件时间',
      key: 'event_time',
      width: 120,
      align: 'center',
      sorter: (a, b) => {
        const timeA = a.event_time ? new Date(a.event_time).getTime() : 0;
        const timeB = b.event_time ? new Date(b.event_time).getTime() : 0;
        return timeA - timeB;
      },
      render(row) {
        return h('div', { class: 'event-time-cell' }, [
          h(
            NIcon,
            { size: '14', style: { marginRight: '4px', color: '#1890ff' } },
            { default: () => h(TimeOutline) }
          ),
          h('span', formatDateTime(row.event_time || row['发布时间'])),
        ]);
      },
    },
    {
      title: '事件摘要',
      key: 'summary',
      width: 300,
      align: 'center',
      ellipsis: { tooltip: true },
      render(row) {
        const summary = getEventSummary(row);
        return h('div', { class: 'description-preview' }, [
          h(NEllipsis, { tooltip: false, lineClamp: 3 }, { default: () => summary }),
        ]);
      },
    },
    {
      title: '事件子类',
      key: 'event_subtype',
      sorter: true,
      width: 120,
      align: 'center',
      render(row) {
        const subtype = formatEventSubtype(getEventSubtype(row));
        return h(
          'span',
          {
            style: {
              fontSize: '12px',
              padding: '2px 6px',
              background: '#f0f0f0',
              borderRadius: '3px',
            },
          },
          subtype
        );
      },
    },
    {
      title: '影响级别',
      key: 'impact_level',
      filter: true,
      filterOptions: [
        { label: '极高', value: 'critical' },
        { label: '高', value: 'high' },
        { label: '中', value: 'medium' },
        { label: '低', value: 'low' },
      ],
      filterMultiple: false,
      filterOptionValues: repoHeaderFilters.value.impact_level,
      width: 122,
      align: 'center',
      render(row) {
        const level = resolveRepoImpactLevel(row);
        const levelMap: Record<string, any> = {
          critical: { text: '极高', class: 'level-critical', color: '#ff4d4f' },
          high: { text: '高', class: 'level-high', color: '#fa541c' },
          medium: { text: '中', class: 'level-medium', color: '#fa8c16' },
          low: { text: '低', class: 'level-low', color: '#d9d9d9' },
        };
        const config = levelMap[level] || {
          text: formatImpactLevel(level),
          class: '',
          color: '#666',
        };
        return h(
          'div',
          {
            class: `impact-level ${config.class}`,
            style: {
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '2px 8px',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: '600',
              background: config.color + '10',
              color: config.color,
              border: `1px solid ${config.color}30`,
            },
          },
          config.text
        );
      },
    },
    {
      title: '情感',
      key: 'sentiment',
      filter: true,
      filterOptions: [
        { label: '正面', value: 'positive' },
        { label: '负面', value: 'negative' },
        { label: '中性', value: 'neutral' },
      ],
      filterMultiple: false,
      filterOptionValues: repoHeaderFilters.value.sentiment,
      width: 122,
      align: 'center',
      render(row) {
        const sentiment = resolveRepoSentiment(row);
        const sentimentMap: Record<string, any> = {
          positive: { text: '正面', class: 'sentiment-positive', color: '#52c41a' },
          negative: { text: '负面', class: 'sentiment-negative', color: '#ff4d4f' },
          neutral: { text: '中性', class: 'sentiment-neutral', color: '#666' },
        };
        const config = sentimentMap[sentiment] || {
          text: formatSentiment(sentiment),
          class: '',
          color: '#666',
        };
        return h(
          'div',
          {
            class: `sentiment ${config.class}`,
            style: {
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '2px 8px',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: '600',
              background: config.color + '10',
              color: config.color,
              border: `1px solid ${config.color}30`,
            },
          },
          config.text
        );
      },
    },
    {
      title: '相关标的',
      key: 'symbol',
      sorter: true,
      width: 120,
      align: 'center',
      render(row) {
        const eventType = getEventType(row);
        let symbol =
          row.symbol ||
          row.stock_num ||
          row.raw_data?.symbol ||
          row.data?.symbol ||
          row.data?.raw_data?.symbol ||
          '-';
        if (eventType === 'trading' && !symbol && row['标题']) {
          const symbolMatch = row['标题'].match(/[0-9]{6}/);
          if (symbolMatch) {
            symbol = symbolMatch[0];
          }
        }
        if (eventType === 'industry') {
          symbol = row.board_name || row.raw_data?.board_name || row.data?.board_name || symbol;
        }
        return h('div', { class: 'symbol-cell' }, [
          h(
            NIcon,
            { size: '14', style: { marginRight: '4px', color: '#165dff' } },
            { default: () => h(BusinessOutline) }
          ),
          h(
            'span',
            {
              class: 'symbol-text',
              style: {
                fontFamily: "'SFMono-Regular', Consolas, monospace",
                fontSize: '12px',
                fontWeight: '500',
                padding: '2px 6px',
                background: 'rgba(22, 93, 255, 0.05)',
                borderRadius: '3px',
                color: '#165dff',
                border: '1px solid rgba(22, 93, 255, 0.1)',
              },
            },
            symbol
          ),
        ]);
      },
    },
  ];

  const repoRowKey = (row: TextSampleItem): DataTableRowKey => (row.id as string) || row.index;

  const goBack = () => {
    router.push({ name: 'project_manage_index' });
  };

  const goToGraphEditor = () => {
    if (!projectId.value) return;
    router.push({ name: 'graph_editor', params: { projectId: projectId.value } });
  };

  const detailVisible = ref(false);
  const detailRecord = ref<any | null>(null);
  const detailType = ref<'event' | 'node' | 'edge'>('event');

  const detailTitle = computed(() => {
    if (detailType.value === 'node') return '抽取节点详情';
    if (detailType.value === 'edge') return '抽取关系详情';
    if (!detailRecord.value) return '事件详情';
    const type = getEventType(detailRecord.value);
    return `${formatEventType(type)}事件详情`;
  });

  function openDetail(record: any, type: 'event' | 'node' | 'edge' = 'event') {
    detailRecord.value = record;
    detailType.value = type;
    detailVisible.value = true;
  }

  function isClickOnSelection(e: MouseEvent) {
    const el = e.target as HTMLElement | null;
    if (!el) return false;
    return Boolean(
      el.closest('.n-data-table__checkbox') ||
        el.closest('.n-checkbox') ||
        el.closest('input[type="checkbox"]')
    );
  }

  const sampleRowProps = (row: ProjectAnnouncementItem) => ({
    style: { cursor: 'pointer' },
    onClick: (e: MouseEvent) => {
      if (isClickOnSelection(e)) return;
      openDetail(row, 'event');
    },
  });

  const repoRowProps = (row: any) => ({
    style: { cursor: 'pointer' },
    onClick: (e: MouseEvent) => {
      if (isClickOnSelection(e)) return;
      openDetail(row, 'event');
    },
  });

  const extractedNodeRowProps = (row: any) => ({
    style: { cursor: 'pointer' },
    onClick: (e: MouseEvent) => {
      if (isClickOnSelection(e)) return;
      openDetail(row, 'node');
    },
  });

  const extractedEdgeRowProps = (row: any) => ({
    style: { cursor: 'pointer' },
    onClick: (e: MouseEvent) => {
      if (isClickOnSelection(e)) return;
      openDetail(row, 'edge');
    },
  });

  function getNodeDisplayName(row: any): string {
    return (
      String(row.name ?? row.displayName ?? row.value ?? row.rawValue ?? row.key ?? '').trim() ||
      '-' 
    );
  }

  function getNodeContext(row: any): string {
    const p = row.properties || {};
    const sampleText = getSampleContentByAnyId(
      p.sample_id ?? p.sampleId ?? p.announcement_id ?? p.announcementId
    );
    if (sampleText) return sampleText;
    const c = p.context || row.context || '';
    return c ? String(c).slice(0, 320) : '-';
  }

  function getEdgeNodeName(row: any, direction: 'from' | 'to'): string {
    const nameFromEdge =
      direction === 'from'
        ? String(row.from_name ?? row.fromName ?? row.source_name ?? row.sourceName ?? '').trim()
        : String(row.to_name ?? row.toName ?? row.target_name ?? row.targetName ?? '').trim();
    if (nameFromEdge) return nameFromEdge;
    const sideKey = direction === 'from' ? row.from ?? row.source : row.to ?? row.target;
    return getNodeNameByAnyId(sideKey) || '未匹配节点';
  }

  function handleUpdateCheckedProjectAnnouncementIds(keys: DataTableRowKey[]) {
    checkedProjectAnnouncementIds.value = keys;
  }

  function currentProjectSampleIds(): string[] {
    return projectAnnouncements.value
      .map((item: any) => String(item?.id ?? item?._id ?? '').trim())
      .filter(Boolean);
  }

  // 分页切换函数
  const changeAnnouncementPage = (page: number) => {
    if (page < 1) return;
    const maxPage = Math.max(
      1,
      Math.ceil(projectAnnouncements.value.length / announcementPageSize.value)
    );
    announcementPage.value = Math.min(page, maxPage);
  };

  const refreshProjectAnnouncements = async () => {
    if (!projectId.value) {
      console.log('projectId 为空');
      return;
    }
    loadingProjectAnnouncements.value = true;
    try {
      console.log('开始获取项目公告，projectId:', projectId.value);
      const res = await getProjectAnnouncements(projectId.value);
      console.log('获取项目公告响应:', res);

      if (res.status !== 200) {
        message.error((res as any).msg || '获取项目公告失败');
        return;
      }
      projectAnnouncements.value = res.data || [];
      console.log('项目公告数据:', projectAnnouncements.value);
      const existingIds = new Set(projectAnnouncements.value.map((i) => String(i.id)));
      checkedProjectAnnouncementIds.value = checkedProjectAnnouncementIds.value.filter((k) =>
        existingIds.has(String(k))
      );
      autoDetectedNewSampleIds.value = autoDetectedNewSampleIds.value.filter((id) =>
        existingIds.has(String(id))
      );
      // 重置到第一页
      announcementPage.value = 1;
    } catch (error: any) {
      console.error('refreshProjectAnnouncements error:', error);
      message.error(error?.message || '获取项目公告失败');
    } finally {
      loadingProjectAnnouncements.value = false;
    }
  };

  const handleOpenSelectFromRepo = async () => {
    selectFromRepoVisible.value = true;
    checkedRepoKeys.value = [];
    if (!repo_search_event_type.value.length) {
      repo_search_event_type.value = ['all'];
    }
    if (!repo_search_time_range.value) {
      repo_search_time_range.value = getDefaultRepoTimeRange();
    }
    if (projectId.value) {
      try {
        const infoRes = await getProjectBaseInfo(projectId.value);
        if (infoRes?.status === 200 && infoRes?.data?.project_name) {
          currentProjectName.value = String(infoRes.data.project_name || '').trim();
        }
      } catch (e) {
        console.warn('获取项目基础信息失败，默认关键词回退为空:', e);
      }
    }
    const defaultKeyword = String(currentProjectName.value || '').trim();
    if (defaultKeyword) {
      repo_search_keyword.value = defaultKeyword;
      repoSearchExpanded.value = true;
    }
    repoPage.value = 1;
    await loadRepoSamples();
  };

  function toggleRepoSearch() {
    repoSearchExpanded.value = !repoSearchExpanded.value;
  }

  function resetRepoSearch() {
    repo_search_stock_code.value = '';
    repo_search_keyword.value = String(currentProjectName.value || '').trim();
    repo_search_event_type.value = ['all'];
    repo_search_time_range.value = getDefaultRepoTimeRange();
  }

  function handleRepoSorter(sorter: any) {
    const order = sorter?.order as 'ascend' | 'descend' | false | undefined;
    const columnKey = String(sorter?.columnKey || '').trim();
    const allowed: Record<string, string> = {
      event_type: 'event_type',
      event_time: 'event_time',
      event_subtype: 'event_subtype',
      impact_level: 'impact_level',
      sentiment: 'sentiment',
      symbol: 'symbol',
    };
    if (!order || !allowed[columnKey]) {
      repoSortField.value = 'event_time';
      repoSortOrder.value = -1;
    } else {
      repoSortField.value = allowed[columnKey];
      repoSortOrder.value = order === 'ascend' ? 1 : -1;
    }
    repoPage.value = 1;
    void loadRepoSamples();
  }

  async function submitRepoSearch() {
    repoPage.value = 1;
    await loadRepoSamples();
  }

  const loadRepoSamples = async () => {
    if (!projectId.value) return;
    loadingRepoSamples.value = true;
    try {
      const selectedEventType =
        repo_search_event_type.value.find((x: string) => x && x !== 'all') || undefined;

      const params: any = {
        page: repoPage.value,
        size: repoPageSize.value,
        sort_field: repoSortField.value,
        sort_order: repoSortOrder.value,
        stock_code: repo_search_stock_code.value === '' ? undefined : repo_search_stock_code.value,
        keyword: repo_search_keyword.value === '' ? undefined : repo_search_keyword.value,
        start_time: repo_search_time_range.value
          ? parseStr(repo_search_time_range.value[0])
          : undefined,
        end_time: repo_search_time_range.value
          ? parseStr(repo_search_time_range.value[1])
          : undefined,
        event_type: selectedEventType,
      };

      console.log('开始获取操作库数据，params:', params);
      const response: any = await fetchAllEvents(params);
      const code = Number(response?.code);
      if (code !== 0) {
        message.error(response?.msg || '获取事件数据失败');
        return;
      }

      const payload = response?.data || {};
      const events = Array.isArray(payload?.messages)
        ? payload.messages
        : Array.isArray(payload)
        ? payload
        : [];
      const total = Number(payload?.total ?? payload?.count ?? events.length);

      console.log('解析后的事件数据:', events);

      const mappedRows = events.map((event, idx) => ({
        ...event,
        id: String(event._id || event.id || event.data?._id || event.data?.id || `${repoPage.value}-${idx}`),
        index: (repoPage.value - 1) * repoPageSize.value + idx + 1,
        content:
          event.event_description ||
          event.data?.event_description ||
          event.content ||
          event.data?.content ||
          event.summary ||
          event.data?.summary ||
          (event.raw_data && (event.raw_data as any)['新闻内容']) ||
          (event.data?.raw_data && (event.data.raw_data as any)['新闻内容']) ||
          '',
        // 兼容旧字段名：表格列渲染会优先走 event_time / event_description / symbol 等
        publishTime: String(
          event.event_time || event.data?.event_time || event.trade_date || event.date || event.time || ''
        ),
        symbol:
          event.symbol ||
          event.raw_data?.symbol ||
          event.data?.symbol ||
          event.data?.raw_data?.symbol ||
          '',
        board_name: event.board_name || event.raw_data?.board_name || event.data?.board_name || '',
        stock_num:
          event.symbol ||
          event.raw_data?.symbol ||
          event.data?.symbol ||
          event.data?.raw_data?.symbol ||
          event.stock_code ||
          event.company_of_interest ||
          '',
        event_type: getEventType(event),
        event_subtype: getEventSubtype(event),
        impact_level: getImpactLevel(event),
        sentiment: getSentiment(event),
      })) as any[];

      // 事件子类按“展示文本”排序，避免后端按原始编码排序导致与用户观感不一致。
      if (repoSortField.value === 'event_subtype') {
        const factor = repoSortOrder.value === 1 ? 1 : -1;
        mappedRows.sort((a: any, b: any) => {
          const aText = String(formatEventSubtype(getEventSubtype(a)) || '');
          const bText = String(formatEventSubtype(getEventSubtype(b)) || '');
          return aText.localeCompare(bText, 'zh-Hans-CN', { sensitivity: 'base' }) * factor;
        });
      }

      repoSamples.value = mappedRows;

      console.log('处理后的操作库样本数据:', repoSamples.value);
      repoTotal.value = total;
    } catch (error: any) {
      console.error('loadRepoSamples error:', error);
      message.error(error?.message || '获取事件数据失败');
    } finally {
      loadingRepoSamples.value = false;
    }
  };

  const changeRepoPage = async (page: number) => {
    if (page < 1) return;
    const maxPage = Math.max(1, Math.ceil(repoTotal.value / repoPageSize.value));
    repoPage.value = Math.min(page, maxPage);
    await loadRepoSamples();
  };

  const onRepoPageSizeChange = async (size: number) => {
    repoPageSize.value = size;
    repoPage.value = 1;
    await loadRepoSamples();
  };

  const handleSaveAnnouncementIds = async () => {
    const raw = announcementIdsInput.value.trim();
    if (!raw) {
      message.warning('请输入至少一个公告 ID');
      return;
    }
    const ids = raw
      .split(/[\s,，;；]+/)
      .map((s) => s.trim())
      .filter(Boolean);
    if (!ids.length) {
      message.warning('未解析到有效的公告 ID');
      return;
    }

    const beforeIds = new Set(currentProjectSampleIds());
    savingAnnouncements.value = true;
    try {
      const res = await saveSelectData({
        project_id: projectId.value,
        announcement_ids: ids,
      });
      if (res.status === 200) {
        message.success(res.msg || '保存公告成功');
        announcementIdsInput.value = '';
        await refreshProjectAnnouncements();
        const afterIds = new Set(currentProjectSampleIds());
        const detected = Array.from(afterIds).filter((id) => !beforeIds.has(id));
        if (detected.length > 0) {
          const merged = new Set([...(autoDetectedNewSampleIds.value || []), ...detected]);
          autoDetectedNewSampleIds.value = Array.from(merged);
        }
      } else {
        message.error(res.msg || '保存公告失败');
      }
    } catch (error: any) {
      message.error(error?.message || '保存公告失败');
      console.error('handleSaveAnnouncementIds error:', error);
    } finally {
      savingAnnouncements.value = false;
    }
  };

  const handleSaveFromRepo = async () => {
    if (!checkedRepoKeys.value.length) {
      message.warning('请至少选择一条样本');
      return;
    }
    // 假设操作库返回的每条数据都包含真实公告 ID
    const ids = repoSamples.value
      .filter((item) => checkedRepoKeys.value.includes(item.id || item.index))
      .map((item) => item.id)
      .filter(Boolean) as string[];

    if (!ids.length) {
      message.warning('未获取到有效的样本 ID');
      return;
    }

    const beforeIds = new Set(currentProjectSampleIds());
    savingFromRepo.value = true;
    try {
      const res = await saveSelectData({
        project_id: projectId.value,
        announcement_ids: ids,
      });
      if (res.status === 200) {
        message.success(res.msg || '保存样本成功');
        selectFromRepoVisible.value = false;
        await refreshProjectAnnouncements();
        const afterIds = new Set(currentProjectSampleIds());
        const detected = Array.from(afterIds).filter((id) => !beforeIds.has(id));
        if (detected.length > 0) {
          const merged = new Set([...(autoDetectedNewSampleIds.value || []), ...detected]);
          autoDetectedNewSampleIds.value = Array.from(merged);
          message.info(`已自动识别 ${detected.length} 条新导入样本，可直接执行增量更新。`);
        }
      } else {
        message.error(res.msg || '保存样本失败');
      }
    } catch (error: any) {
      message.error(error?.message || '保存样本失败');
      console.error('handleSaveFromRepo error:', error);
    } finally {
      savingFromRepo.value = false;
    }
  };

  const handleDeleteSelectedAnnouncements = async () => {
    if (!checkedAnnouncementIds.value.length) {
      return;
    }
    deletingAnnouncements.value = true;
    try {
      const res = await deleteSelectedData({
        project_id: projectId.value,
        ids: checkedAnnouncementIds.value,
      });
      if (res.status === 200) {
        message.success(res.msg || '删除公告成功');
        checkedAnnouncementIds.value = [];
        await refreshProjectAnnouncements();
      } else {
        message.error(res.msg || '删除公告失败');
      }
    } catch (error: any) {
      message.error(error?.message || '删除公告失败');
      console.error('handleDeleteSelectedAnnouncements error:', error);
    } finally {
      deletingAnnouncements.value = false;
    }
  };

  const handleBatchDeleteSamples = async () => {
    const ids = checkedProjectAnnouncementIds.value.map(String).filter(Boolean);
    if (!ids.length) return;
    deletingAnnouncements.value = true;
    try {
      const res = await deleteSelectedData({
        project_id: projectId.value,
        ids,
      });
      if (res.status === 200) {
        message.success((res as any).msg || '删除样本成功');
        checkedProjectAnnouncementIds.value = [];
        await refreshProjectAnnouncements();
        const existing = new Set(currentProjectSampleIds());
        autoDetectedNewSampleIds.value = autoDetectedNewSampleIds.value.filter((id) =>
          existing.has(String(id))
        );
      } else {
        message.error((res as any).msg || '删除样本失败');
      }
    } catch (error: any) {
      message.error(error?.message || '删除样本失败');
      console.error('handleBatchDeleteSamples error:', error);
    } finally {
      deletingAnnouncements.value = false;
    }
  };

  async function loadExtractedTablesFromApi() {
    if (!projectId.value) return;
    try {
      const [nodesRes, edgesRes] = await Promise.all([
        getNodesByProject(projectId.value),
        getEdgesByProject(projectId.value),
      ]);
      if (nodesRes.success && nodesRes.data?.nodes) {
        nodesTableData.value = nodesRes.data.nodes;
        nodesCount.value = nodesRes.data.count ?? nodesRes.data.nodes.length;
        hasNodes.value = nodesTableData.value.length > 0;
      }
      if (edgesRes.success && edgesRes.data?.edges) {
        edgesTableData.value = edgesRes.data.edges;
        edgesCount.value = edgesRes.data.count ?? edgesRes.data.edges.length;
        hasEdges.value = edgesTableData.value.length > 0;
      }
    } catch (e) {
      console.error('loadExtractedTablesFromApi', e);
    }
  }

  function applyMasterCompletePayload(data: any) {
    const d = data || {};
    const prevMeta = latestWorkflowMeta.value;
    const prevQuality = latestQualityReport.value;

    nodesTableData.value = d.nodes ?? [];
    edgesTableData.value = d.edges ?? [];
    nodesCount.value = nodesTableData.value.length;
    edgesCount.value = edgesTableData.value.length;
    hasNodes.value = nodesCount.value > 0;
    hasEdges.value = edgesCount.value > 0;
    conflictsList.value = d.conflicts ?? d.graph?.conflicts ?? [];
    nodeTablePage.value = 1;
    edgeTablePage.value = 1;
    buildProgressPercent.value = 100;
    buildProgressLabel.value = '构建完成';

    // 如果后端没有返回 workflow_meta，保留之前的
    let incomingMeta: WorkflowMeta | null =
      d.workflow_meta && typeof d.workflow_meta === 'object'
        ? (d.workflow_meta as WorkflowMeta)
        : null;

    if (incomingMeta) {
      // 若本次构建未返回 quality_report，但我们有上次有效的报告，则回退合并
      const incomingHasQuality = !!incomingMeta.quality_report;
      if (!incomingHasQuality && prevMeta && prevMeta.quality_report) {
        incomingMeta = {
          ...incomingMeta,
          quality_report: prevMeta.quality_report,
          quality_score: incomingMeta.quality_score ?? prevMeta.quality_score,
        } as WorkflowMeta;
        activeWorkflowReportSource.value = '回退到上次有效质量报告';
      } else {
        activeWorkflowReportSource.value = '当前构建返回';
      }
    } else {
      // 如果后端完全没有返回 meta，则保持原有 meta
      incomingMeta = prevMeta;
      if (incomingMeta) activeWorkflowReportSource.value = '回退到上次有效质量报告';
    }

    latestWorkflowMeta.value = incomingMeta;
    activeWorkflowRunId.value = String(incomingMeta?.run_id || '');
    if (projectId.value && activeWorkflowRunId.value && latestWorkflowMeta.value) {
      persistWorkflowReportCache(projectId.value, activeWorkflowRunId.value, latestWorkflowMeta.value);
    }

    hasBuildCompleted.value = true;
    latestQualityReport.value = normalizeQualityReport(latestWorkflowMeta.value?.quality_report) || prevQuality;
    qualityReportMissing.value = !latestQualityReport.value;
  }

  async function loadWorkflowReportByRun(targetRunId: string): Promise<boolean> {
    if (!canViewQualityReport.value || !projectId.value) return false;
    if (workflowReportApiUnavailable.value) return false;
    const rid = String(targetRunId || '').trim();
    if (!rid) return false;
    if (restoreWorkflowReportFromCache(projectId.value, rid)) return true;
    loadingWorkflowReport.value = true;
    try {
      const res = await getWorkflowReportByRun(projectId.value, rid);
      if (!res.success || res.status !== 200) return false;
      const meta = res.data?.workflow_meta;
      latestWorkflowMeta.value =
        meta && typeof meta === 'object' ? (meta as WorkflowMeta) : null;
      activeWorkflowRunId.value = String(res.data?.run_id || rid);
      activeWorkflowReportSource.value = '历史任务回放';
      latestQualityReport.value = normalizeQualityReport(meta?.quality_report);
      if (projectId.value && activeWorkflowRunId.value && latestWorkflowMeta.value) {
        persistWorkflowReportCache(projectId.value, activeWorkflowRunId.value, latestWorkflowMeta.value);
      }
      qualityReportMissing.value = hasBuildCompleted.value && !latestQualityReport.value;
      return true;
    } catch (e: any) {
      const status = Number(e?.response?.status || 0);
      if (status === 404) {
        workflowReportApiUnavailable.value = true;
        return false;
      }
      console.error('loadWorkflowReportByRun error:', e);
      return false;
    } finally {
      loadingWorkflowReport.value = false;
    }
  }

  async function resolveLatestRunIdForProject(): Promise<string> {
    if (!projectId.value) return '';
    try {
      const listRes = await getExtractionHistoryList(projectId.value);
      if (!listRes.success || listRes.status !== 200) return '';
      const items = listRes.data?.items || [];
      const first = items.find((x) => String(x?.run_id || '').trim());
      return first ? String(first.run_id) : '';
    } catch (e) {
      console.error('resolveLatestRunIdForProject error:', e);
      return '';
    }
  }

  const handleOpenWorkflowReport = async () => {
    if (!canViewQualityReport.value) return;
    if (latestWorkflowMeta.value) {
      workflowReportModalVisible.value = true;
      return;
    }

    const preferredRunId = String(activeWorkflowRunId.value || runId.value || '').trim();
    let ok = false;
    if (preferredRunId) {
      ok = restoreWorkflowReportFromCache(projectId.value, preferredRunId);
    }
    if (!ok && preferredRunId) {
      ok = await loadWorkflowReportByRun(preferredRunId);
    }
    if (!ok) {
      const latestRunId = await resolveLatestRunIdForProject();
      if (latestRunId) {
        ok = await loadWorkflowReportByRun(latestRunId);
      }
    }

    if (!ok || !latestWorkflowMeta.value) {
      if (workflowReportApiUnavailable.value) {
        message.warning('构建报告查询接口暂不可用（后端可能未重启加载新路由），已尝试本地缓存回填。');
      }
      message.warning('未找到可展示的构建报告，请先执行一键构建或切换到包含 run_id 的结果。');
      return;
    }
    workflowReportModalVisible.value = true;
  };

  const handleOpenAiQualityAnalysis = async () => {
    if (!canUseAiQualityAnalysis.value) {
      return;
    }
    const preferredRunId = String(activeWorkflowRunId.value || runId.value || '').trim();
    if (!latestWorkflowMeta.value && canUseAiQualityAnalysis.value) {
      let ok = false;
      if (preferredRunId) {
        ok = restoreWorkflowReportFromCache(projectId.value, preferredRunId);
      }
      if (!ok && preferredRunId) {
        ok = await loadWorkflowReportByRun(preferredRunId);
      }
      if (!ok) {
        const latestRunId = await resolveLatestRunIdForProject();
        if (latestRunId) {
          await loadWorkflowReportByRun(latestRunId);
        }
      }
    }

    aiAnalysisModalVisible.value = true;

    if (!latestWorkflowMeta.value) {
      message.warning('未找到可用于分析的构建报告，请先执行一键构建或切换到有 run_id 的结果。');
      return;
    }

    const runForAnalysis = String(activeWorkflowRunId.value || runId.value || latestWorkflowMeta.value?.run_id || '').trim();

    loadingAiAnalysis.value = true;
    aiAnalysisText.value = '';
    aiAnalysisForRunId.value = '';
    try {
      // 强制走专用 NDJSON 流式接口，避免后端/网关按 JSON 缓冲导致“瞬间出完整报告”
      const resp = await fetch('/old-api/llmGenKG/analyze_quality_report_ai_stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId.value,
          run_id: runForAnalysis,
          workflow_meta: latestWorkflowMeta.value || undefined,
          conflicts: displayConflictsList.value,
        }),
      });

      if (!resp.ok || !resp.body) {
        // 流式不可用时回退普通接口
        const fallback = await analyzeQualityReportAI({
          project_id: projectId.value,
          run_id: runForAnalysis,
          workflow_meta: latestWorkflowMeta.value || undefined,
          conflicts: displayConflictsList.value,
        });
        if (!fallback.success || fallback.status !== 200) {
          message.error(fallback.message || 'AI 分析生成失败');
          return;
        }
        aiAnalysisText.value = String(fallback.data?.analysis_report || '').trim();
        aiAnalysisForRunId.value = runForAnalysis;
        if (!aiAnalysisText.value) {
          aiAnalysisText.value = '本次未生成分析文本，请稍后重试。';
        }
        return;
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          const t = line.trim();
          if (!t) continue;
          try {
            const evt = JSON.parse(t);
            if (evt?.status === 'chunk') {
              aiAnalysisText.value += String(evt?.data?.text || '');
            } else if (evt?.status === 'complete') {
              if (!aiAnalysisText.value.trim()) {
                aiAnalysisText.value = String(evt?.data?.analysis_report || '').trim();
              }
              aiAnalysisForRunId.value = runForAnalysis;
            }
          } catch {
            // ignore non-json line
          }
        }
      }

      if (buffer.trim()) {
        try {
          const evt = JSON.parse(buffer.trim());
          if (evt?.status === 'chunk') {
            aiAnalysisText.value += String(evt?.data?.text || '');
          } else if (evt?.status === 'complete') {
            if (!aiAnalysisText.value.trim()) {
              aiAnalysisText.value = String(evt?.data?.analysis_report || '').trim();
            }
            aiAnalysisForRunId.value = runForAnalysis;
          } else if (evt?.success && Number(evt?.status) === 200) {
            aiAnalysisText.value = String(evt?.data?.analysis_report || '').trim();
            aiAnalysisForRunId.value = runForAnalysis;
          }
        } catch {
          // ignore tail parse errors
        }
      }

      if (!aiAnalysisText.value.trim()) {
        aiAnalysisText.value = '本次未生成分析文本，请稍后重试。';
      }
    } catch (e: any) {
      console.error('handleOpenAiQualityAnalysis error:', e);
      message.error(e?.message || 'AI 分析生成失败');
      aiAnalysisText.value = '分析生成失败，请稍后重试。';
    } finally {
      loadingAiAnalysis.value = false;
    }
  };

  function notifyExtractionHistoryRefresh() {
    window.dispatchEvent(new CustomEvent(EXTRACTION_HISTORY_REFRESH_EVENT));
  }

  function parseStreamLine(jsonLine: any) {
    if (jsonLine.status === 'progress') {
      buildPhase.value = jsonLine.phase === 'relations' ? 'relations' : 'nodes';
      buildProgressPercent.value = Math.min(
        100,
        Math.max(0, Number(jsonLine.progress) || 0)
      );
      buildProgressLabel.value = jsonLine.label || jsonLine.stage || '';
      return;
    }
    if (jsonLine.status === 'complete' && jsonLine.success) {
      applyMasterCompletePayload(jsonLine.data);
      const builtIds = (currentBuildSampleIds.value || []).filter((x) => String(x || '').trim() !== '');
      if (builtIds.length > 0) {
        lastBuildSampleIds.value = new Set(builtIds);
        autoDetectedNewSampleIds.value = autoDetectedNewSampleIds.value.filter(
          (id) => !lastBuildSampleIds.value.has(id)
        );
      }
      notifyExtractionHistoryRefresh();
      const completedRunId = String(jsonLine.data?.workflow_meta?.run_id || '');
      if (completedRunId && completedRunId !== runId.value) {
        router.replace({
          name: 'abstract_kg',
          params: { projectId: projectId.value },
          query: { run: completedRunId },
        });
        void refreshNeo4jGraph(
          true,
          buildRunMode.value === 'incremental' ? undefined : completedRunId,
        );
      } else {
        void refreshNeo4jGraph(true);
      }
      const sampleDelta = jsonLine.data?.workflow_meta?.sample_delta || {};
      const deltaKind = String(sampleDelta?.kind || '');
      if (deltaKind === 'noop') {
        message.info(
          sampleDelta?.message || '样本无更新，已跳过重复抽取。可在左侧「抽取历史」查看已有结果。'
        );
      } else if (deltaKind === 'incremental_only' || deltaKind === 'incremental_and_prune') {
        const added = Array.isArray(sampleDelta?.added_sample_ids)
          ? sampleDelta.added_sample_ids.length
          : 0;
        const removed = Array.isArray(sampleDelta?.removed_sample_ids)
          ? sampleDelta.removed_sample_ids.length
          : 0;
        message.success(
          `已按样本变化完成增量构建（新增 ${added} 条，移除 ${removed} 条）。`
        );
      } else if (deltaKind === 'prune_only') {
        const removed = Array.isArray(sampleDelta?.removed_sample_ids)
          ? sampleDelta.removed_sample_ids.length
          : 0;
        message.success(`已完成样本删除裁剪（移除 ${removed} 条样本对应子图）。`);
      } else {
        message.success(buildRunMode.value === 'incremental' ? '增量更新完成' : '一键构建完成');
      }
      void loadExtractedTablesFromApi();
      return;
    }
    if (jsonLine.status === 'error') {
      message.error(jsonLine.message || (buildRunMode.value === 'incremental' ? '增量更新失败' : '一键构建失败'));
    }
  }

  interface MasterBuildTaskQueueItem {
    task_id: string;
    project_id: string;
    project_name: string;
    mode: 'full' | 'incremental';
    created_at: string;
    run_id?: string;
  }

  const MASTER_BUILD_TASKS_KEY = 'finkg-master-build-tasks';
  const MASTER_BUILD_TASKS_UPDATED_EVENT = 'finkg-master-build-tasks-updated';

  function registerMasterBuildTask(item: MasterBuildTaskQueueItem) {
    try {
      const raw = localStorage.getItem(MASTER_BUILD_TASKS_KEY);
      const list = raw ? (JSON.parse(raw) as MasterBuildTaskQueueItem[]) : [];
      const merged = [item, ...(Array.isArray(list) ? list : [])].filter(
        (x, idx, arr) => !!x?.task_id && arr.findIndex((y) => y.task_id === x.task_id) === idx
      );
      localStorage.setItem(MASTER_BUILD_TASKS_KEY, JSON.stringify(merged));
      try {
        localStorage.setItem(ACTIVE_MASTER_BUILD_TASK_KEY, JSON.stringify(item));
      } catch {
        // ignore storage errors
      }
      window.dispatchEvent(new CustomEvent(MASTER_BUILD_TASKS_UPDATED_EVENT));
    } catch {
      /* ignore storage errors */
    }
  }

  function clearMasterBuildTaskPollTimer() {
    if (masterBuildTaskPollTimer !== null) {
      window.clearTimeout(masterBuildTaskPollTimer);
      masterBuildTaskPollTimer = null;
    }
  }

  function persistActiveMasterBuildTask(task: {
    task_id: string;
    project_id: string;
    mode: 'full' | 'incremental';
    run_id?: string;
    status?: string;
  }) {
    try {
      localStorage.setItem(ACTIVE_MASTER_BUILD_TASK_KEY, JSON.stringify(task));
    } catch {
      // ignore storage errors
    }
  }

  function restoreActiveMasterBuildTaskFromStorage() {
    try {
      const raw = localStorage.getItem(ACTIVE_MASTER_BUILD_TASK_KEY);
      if (!raw) return false;
      const task = JSON.parse(raw) as {
        task_id?: string;
        project_id?: string;
        mode?: 'full' | 'incremental';
        run_id?: string;
        status?: string;
      };
      if (!task?.task_id || String(task.project_id || '') !== projectId.value) return false;
      activeMasterBuildTaskId.value = String(task.task_id);
      activeMasterBuildTaskMode.value = task.mode === 'incremental' ? 'incremental' : 'full';
      activeMasterBuildTaskRunId.value = String(task.run_id || '');
      activeMasterBuildTaskStatus.value = String(task.status || '') as any;
      return true;
    } catch {
      return false;
    }
  }

  function clearActiveMasterBuildTaskState() {
    activeMasterBuildTaskId.value = '';
    activeMasterBuildTaskRunId.value = '';
    activeMasterBuildTaskStatus.value = '';
    activeMasterBuildTaskMode.value = 'full';
    taskCompletionNotified.value = false;
    try {
      localStorage.removeItem(ACTIVE_MASTER_BUILD_TASK_KEY);
    } catch {
      // ignore storage errors
    }
  }

  async function pollMasterBuildTaskStatus(taskId: string) {
    clearMasterBuildTaskPollTimer();
    if (!taskId) return;
    try {
      const res = await getMasterAgentTaskStatus(taskId);
      if (!res.success || !res.data) {
        throw new Error(res.message || '获取任务状态失败');
      }
      const data = res.data;
      activeMasterBuildTaskId.value = String(data.task_id || taskId);
      activeMasterBuildTaskStatus.value = String(data.status || 'pending') as any;
      if (typeof data.progress === 'number') {
        buildProgressPercent.value = Math.min(100, Math.max(0, data.progress));
      }
      if (data.phase) {
        buildPhase.value = data.phase === 'relations' ? 'relations' : 'nodes';
      }
      buildProgressLabel.value = String(data.label || data.message || '');
      if (!buildProgressLabel.value) {
        buildProgressLabel.value =
          activeMasterBuildTaskStatus.value === 'pending'
            ? '任务已提交，等待执行'
            : activeMasterBuildTaskStatus.value === 'running'
            ? '后台运行中，可关闭弹窗并前往其他页面继续操作'
            : activeMasterBuildTaskStatus.value === 'success'
            ? '图谱构建完成'
            : activeMasterBuildTaskStatus.value === 'error'
            ? '构建失败，请检查任务状态'
            : '';
      }
      if (data.run_id) {
        activeMasterBuildTaskRunId.value = String(data.run_id);
      }
      persistActiveMasterBuildTask({
        task_id: activeMasterBuildTaskId.value,
        project_id: projectId.value,
        mode: activeMasterBuildTaskMode.value,
        run_id: activeMasterBuildTaskRunId.value,
        status: activeMasterBuildTaskStatus.value,
      });

      if (activeMasterBuildTaskStatus.value === 'success') {
        buildProgressPercent.value = 100;
        buildPhase.value = 'relations';
        buildProgressLabel.value = '图谱构建完成';
        hasBuildCompleted.value = true;
        if (!taskCompletionNotified.value) {
          taskCompletionNotified.value = true;
          message.success(
            activeMasterBuildTaskMode.value === 'incremental'
              ? '增量更新完成'
              : '一键构建完成'
          );
        }
        if (projectId.value) {
          await loadExtractedTablesFromApi();
          await refreshNeo4jGraph(false, activeMasterBuildTaskRunId.value || undefined);
          if (canViewQualityReport.value && activeMasterBuildTaskRunId.value) {
            if (!restoreWorkflowReportFromCache(projectId.value, activeMasterBuildTaskRunId.value)) {
              await loadWorkflowReportByRun(activeMasterBuildTaskRunId.value);
            }
          }
        }
        return;
      }

      if (activeMasterBuildTaskStatus.value === 'error') {
        if (!taskCompletionNotified.value) {
          taskCompletionNotified.value = true;
          message.error(data.error || data.message || '构建任务失败');
        }
        return;
      }

      masterBuildTaskPollTimer = window.setTimeout(() => {
        void pollMasterBuildTaskStatus(taskId);
      }, 1500);
    } catch (error: any) {
      console.error('pollMasterBuildTaskStatus error:', error);
      masterBuildTaskPollTimer = window.setTimeout(() => {
        if (activeMasterBuildTaskId.value) {
          void pollMasterBuildTaskStatus(activeMasterBuildTaskId.value);
        }
      }, 2000);
    }
  }

  async function runMasterBuildStream(sampleIds: string[], mode: 'full' | 'incremental') {
    if (oneClickBuilding.value) return;
    buildRunMode.value = mode;
    const ids = projectAnnouncements.value
      .map((item: any) => item.id ?? item._id)
      .filter((id): id is string => id != null && String(id).trim() !== '');
    const useIds = (sampleIds || []).filter((id) => String(id || '').trim() !== '');
    if (!ids.length || !useIds.length) {
      message.warning('未获取到有效的公告 ID');
      return;
    }

    oneClickBuilding.value = true;
    currentBuildSampleIds.value = [...useIds];
    conflictsList.value = [];
    hasBuildCompleted.value = false;
    latestQualityReport.value = null;
    latestWorkflowMeta.value = null;
    activeWorkflowRunId.value = '';
    activeWorkflowReportSource.value = '当前构建返回';
    workflowReportApiUnavailable.value = false;
    qualityReportMissing.value = false;
    buildProgressModalVisible.value = true;
    buildProgressPercent.value = 8;
    buildPhase.value = 'nodes';
    buildProgressLabel.value = mode === 'incremental' ? '正在提交增量后台任务…' : '正在提交后台任务…';
    currentStep.value = 2;

    try {
      const uid =
        userStore.getUserId || userStore.getUsername || userStore.getName || '';
      const uname = userStore.getUsername || userStore.getName || '';
      const res = await startMasterAgentAsyncTask({
        project_id: projectId.value,
        sample_ids: useIds,
        ...(mode === 'incremental'
          ? {
              build_plan: {
                mode: 'incremental',
                persistence_mode: 'merge',
                strict_stale_cleanup: false,
              },
            }
          : {}),
        ...(uid
          ? {
              user_id: uid,
              creator: uid,
              username: uname,
            }
          : {}),
      });

      if (!res.success || !res.data?.task_id) {
        message.error(res.message || `${mode === 'incremental' ? '增量更新' : '一键构建'}提交失败`);
        return;
      }

      const taskProjectName = String(currentProjectName.value || `项目${projectId.value}`).trim();
      registerMasterBuildTask({
        task_id: res.data.task_id,
        project_id: projectId.value,
        project_name: taskProjectName,
        mode,
        created_at: new Date().toISOString(),
        run_id: String(res.data.run_id || '').trim() || undefined,
      });
      activeMasterBuildTaskId.value = res.data.task_id;
      activeMasterBuildTaskStatus.value = String(res.data.status || 'pending') as any;
      activeMasterBuildTaskMode.value = mode;
      activeMasterBuildTaskRunId.value = String(res.data.run_id || '').trim();
      persistActiveMasterBuildTask({
        task_id: activeMasterBuildTaskId.value,
        project_id: projectId.value,
        mode,
        run_id: activeMasterBuildTaskRunId.value,
        status: activeMasterBuildTaskStatus.value,
      });
      taskCompletionNotified.value = false;

      buildProgressPercent.value = 15;
      buildProgressLabel.value = '后台运行中，可关闭弹窗并前往其他页面继续操作';
      void pollMasterBuildTaskStatus(activeMasterBuildTaskId.value);
      message.success(`${mode === 'incremental' ? '增量更新' : '一键构建'}已转为后台运行，可关闭进度弹窗。`);
    } catch (error: any) {
      message.error(error?.message || (mode === 'incremental' ? '增量更新失败' : '一键构建失败'));
      console.error('runMasterBuildStream error:', error);
    } finally {
      oneClickBuilding.value = false;
    }
  }

  const currentBuildSampleIds = ref<string[]>([]);

  const handleOneClickBuild = async () => {
    if (!projectAnnouncements.value.length) {
      message.warning('请先为项目配置公告数据');
      return;
    }
    const ids = projectAnnouncements.value
      .map((item: any) => item.id ?? item._id)
      .filter((id): id is string => id != null && String(id).trim() !== '');
    try {
      const preview = await previewMasterBuildPath(projectId.value, ids);
      if (preview.success && preview.status === 200 && preview.data?.message) {
        message.info(preview.data.message);
      }
    } catch (e) {
      // 预判提示失败不阻断正式构建
      console.warn('previewMasterBuildPath failed:', e);
    }
    await runMasterBuildStream(ids, 'full');
  };

  const handleIncrementalBuild = async () => {
    if (!projectAnnouncements.value.length) {
      message.warning('请先为项目配置公告数据');
      return;
    }
    const selected = checkedProjectAnnouncementIds.value.map((x) => String(x || '').trim()).filter(Boolean);
    const allIds = projectAnnouncements.value
      .map((item: any) => item.id ?? item._id)
      .filter((id): id is string => id != null && String(id).trim() !== '');
    const autoDetected = (autoDetectedNewSampleIds.value || [])
      .map((x) => String(x || '').trim())
      .filter((x) => x && allIds.includes(x));
    const deltaFromLastBuild = allIds.filter((id) => !lastBuildSampleIds.value.has(id));

    let ids = selected;
    if (ids.length === 0 && autoDetected.length > 0) {
      ids = autoDetected;
      message.info(`已自动识别 ${ids.length} 条新导入样本，按新增样本执行增量更新。`);
    }
    if (ids.length === 0 && deltaFromLastBuild.length > 0) {
      ids = deltaFromLastBuild;
      message.info(`检测到相对上次构建新增 ${ids.length} 条样本，按新增样本执行增量更新。`);
    }
    if (ids.length === 0) {
      ids = allIds;
      message.info('未检测到新增样本，将使用当前项目全部样本执行增量更新。');
    }
    await runMasterBuildStream(ids, 'incremental');
  };

  const refreshStatus = async () => {
    if (!projectId.value) return;
    try {
      const statusRes = await checkExtractionStatus(projectId.value);
      if (!statusRes.success) return;
      hasNodes.value = statusRes.has_nodes;
      hasEdges.value = statusRes.has_edges;

      await loadExtractedTablesFromApi();

      if (hasEdges.value) {
        await refreshNeo4jGraph();
      }
    } catch (error) {
      console.error('refreshStatus error:', error);
    }
  };

  const handleGraphResize = () => {
    graphChart?.resize();
  };

  const handleFullscreenChange = () => {
    isGraphFullscreen.value = document.fullscreenElement === graphPreviewRef.value;
    graphChart?.resize();
  };

  watch([runId, projectId], () => {
    if (runId.value && projectId.value) {
      hasEdges.value = true;
      refreshNeo4jGraph(false);
      if (canViewQualityReport.value) {
        if (!restoreWorkflowReportFromCache(projectId.value, runId.value)) {
          void loadWorkflowReportByRun(runId.value);
        }
      }
    }
  });

  onMounted(async () => {
    console.log('组件挂载，开始加载数据...');
    await refreshProjectAnnouncements();
    lastBuildSampleIds.value = new Set(currentProjectSampleIds());
    await refreshStatus();
    if (hasNodes.value || hasEdges.value) {
      currentStep.value = 2;
    }
    if (restoreActiveMasterBuildTaskFromStorage() && activeMasterBuildTaskId.value) {
      void pollMasterBuildTaskStatus(activeMasterBuildTaskId.value);
    }
    if (runId.value && projectId.value) {
      hasEdges.value = true;
      await refreshNeo4jGraph(false);
      if (canViewQualityReport.value) {
        if (!restoreWorkflowReportFromCache(projectId.value, runId.value)) {
          await loadWorkflowReportByRun(runId.value);
        }
      }
    }
    window.addEventListener('resize', handleGraphResize);
    document.addEventListener('fullscreenchange', handleFullscreenChange);
  });

  onBeforeUnmount(() => {
    window.removeEventListener('resize', handleGraphResize);
    document.removeEventListener('fullscreenchange', handleFullscreenChange);
    if (buildProgressRaf !== null) {
      window.cancelAnimationFrame(buildProgressRaf);
      buildProgressRaf = null;
    }
    clearMasterBuildTaskPollTimer();
    if (pendingGraphFrame !== null) {
      window.cancelAnimationFrame(pendingGraphFrame);
      pendingGraphFrame = null;
    }
    if (pendingGraphTimer !== null) {
      window.clearTimeout(pendingGraphTimer);
      pendingGraphTimer = null;
    }
    graphChart?.dispose();
    graphChart = null;
  });
</script>

<style scoped lang="scss">
  .extract-process-page {
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

  .content-wrapper {
    margin-top: 20px;
    display: grid;
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .section-card {
    padding: 12px 4px 4px;
  }

  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;

    h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
      color: #111827;
    }

    p {
      margin: 4px 0 0;
      font-size: 12px;
      color: #6b7280;
    }
  }

  .section-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .subsection-title {
    margin: 16px 0 8px;
    font-size: 14px;
    font-weight: 600;
    color: #374151;
  }

  .status-row {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    font-size: 13px;
    color: #4b5563;
    margin-top: 8px;
  }

  .status-item {
    display: flex;
    align-items: center;

    .label {
      color: #9ca3af;
      margin-right: 4px;
    }

    .value {
      font-weight: 500;
    }
  }

  .graph-chart {
    width: 100%;
    height: 520px;
    margin-top: 12px;
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
  }

  .graph-status-row {
    margin-bottom: 10px;
  }

  .graph-overlay-tools {
    position: absolute;
    top: 56px;
    right: 14px;
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

  .graph-preview-shell:fullscreen {
    background: #f8fbff;
    padding: 14px;
    box-sizing: border-box;
    overflow: auto;
  }

  .graph-preview-shell:fullscreen .graph-chart {
    height: calc(100vh - 120px);
    min-height: 420px;
  }

  .manage-body {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .manage-block {
    padding: 8px 0;

    h4 {
      margin: 0 0 4px;
      font-size: 14px;
      font-weight: 600;
    }

    .desc {
      margin: 0 0 8px;
      font-size: 12px;
      color: #6b7280;
    }
  }

  .manage-actions {
    margin-top: 8px;
    display: flex;
    gap: 8px;

    &.right {
      justify-content: flex-end;
    }
  }

  /* 复用事件看板表格的主要样式，使视觉风格保持一致 */
  .all-events-table {
    flex: 1;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #e5e7eb;

    :deep(.n-data-table-base-table) {
      border-radius: 8px;
      overflow: hidden;
    }

    :deep(.n-data-table-th) {
      background: #fafafa;
      font-weight: 600;
      color: #111827;
      padding: 12px 16px;
      border-bottom: 1px solid #f0f0f0;
    }

    :deep(.n-data-table-td) {
      padding: 12px 16px;
      border-bottom: 1px solid #f0f0f0;
    }
  }

  .pagination-container {
    margin-top: 12px;
    padding: 8px 0 0;
    border-top: 1px solid #f0f0f0;
    display: flex;
    justify-content: center;
    width: 100%;
  }

  .pagination-wrapper {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    justify-content: center;
  }

  .page-info {
    min-width: 150px;
    text-align: center;
    font-size: 13px;
    color: #666;
    font-weight: 500;
    padding: 0 12px;
  }

  .build-progress-shell {
    position: relative;
  }

  .build-progress-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .build-phase-pills {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .phase-pill {
    position: relative;
    padding: 5px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    color: #64748b;
    background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
    border: 1px solid rgba(148, 163, 184, 0.35);
    transition: all 0.28s ease;
  }

  .phase-pill.active {
    color: #0f172a;
    border-color: rgba(56, 189, 248, 0.65);
    background: linear-gradient(180deg, #e0f2fe 0%, #dbeafe 100%);
    box-shadow: 0 8px 18px rgba(56, 189, 248, 0.2);
    transform: translateY(-1px);
  }

  .phase-pill.done {
    color: #065f46;
    border-color: rgba(52, 211, 153, 0.65);
    background: linear-gradient(180deg, #dcfce7 0%, #d1fae5 100%);
  }

  .build-progress-metric {
    min-width: 72px;
    text-align: right;
    font-size: 26px;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #0f172a;
    text-shadow: 0 1px 0 rgba(255, 255, 255, 0.7);
  }

  .build-progress-label {
    display: block;
    margin-top: 8px;
    font-size: 13px;
    line-height: 1.5;
    min-height: 20px;
    transition: color 0.2s ease;
  }

  .build-progress-hint {
    display: block;
    margin-top: 2px;
    font-size: 12px;
    opacity: 0.86;
  }

  .build-progress-bar {
    :deep(.n-progress-graph-line) {
      height: 12px;
      border-radius: 999px;
      background: linear-gradient(180deg, #edf2f7 0%, #e2e8f0 100%);
      overflow: hidden;
    }

    :deep(.n-progress-graph-line-fill) {
      transition: width 0.42s cubic-bezier(0.22, 1, 0.36, 1);
      background-image: linear-gradient(90deg, #38bdf8 0%, #60a5fa 44%, #22c55e 100%);
      background-size: 200% 100%;
      animation: progress-shimmer 1.25s linear infinite;
      box-shadow: 0 3px 14px rgba(56, 189, 248, 0.3);
    }

    :deep(.n-progress-graph-line-indicator) {
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.02em;
    }
  }

  .quality-report-card {
    margin-top: 12px;
    padding: 12px;
    border-radius: 12px;
    border: 1px solid rgba(16, 185, 129, 0.28);
    background: linear-gradient(180deg, rgba(236, 253, 245, 0.94) 0%, rgba(240, 253, 250, 0.94) 100%);
  }

  .quality-report-card--compact {
    margin-top: 4px;
    padding: 10px;
  }

  .quality-report-card__header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 8px;

    h4 {
      margin: 0;
      font-size: 13px;
      font-weight: 700;
      color: #065f46;
    }
  }

  .quality-report-card__hint {
    font-size: 11px;
    color: #6b7280;
  }

  .quality-report-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
  }

  .quality-report-grid__item {
    border-radius: 8px;
    border: 1px solid rgba(110, 231, 183, 0.5);
    background: rgba(255, 255, 255, 0.78);
    padding: 8px;
  }

  .quality-report-grid__label {
    font-size: 11px;
    color: #6b7280;
    line-height: 1.4;
  }

  .quality-report-grid__value {
    margin-top: 2px;
    font-size: 14px;
    font-weight: 700;
    color: #065f46;
    line-height: 1.4;
    word-break: break-word;
  }

  .node-attr-cell {
    display: flex;
    align-items: center;
    min-width: 0;
    max-width: 100%;
    gap: 6px;
  }

  .node-attr-key-tag {
    flex-shrink: 0;
    max-width: 42%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .node-attr-separator {
    flex-shrink: 0;
    color: #94a3b8;
    font-weight: 600;
  }

  .node-attr-value {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #334155;
    font-weight: 500;
  }

  .workflow-report-json {
    margin: 0;
    font-size: 12px;
    line-height: 1.5;
    color: #334155;
    white-space: pre-wrap;
    word-break: break-word;
    padding: 2px 0;
  }

  .workflow-report-modal-body {
    max-height: min(72vh, 680px);
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: 6px;
  }

  .detail-content {
    max-height: min(72vh, 640px);
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: 6px;
  }

  .detail-content :deep(.n-descriptions-table-content) {
    word-break: break-word;
  }

  .workflow-form-section {
    border: 1px solid rgba(148, 163, 184, 0.25);
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.98) 100%);

    :deep(.n-card-header__main) {
      font-size: 13px;
      font-weight: 700;
      color: #0f172a;
    }
  }

  .workflow-form-value {
    color: #1f2937;
    line-height: 1.55;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .workflow-raw-toggle {
    border: 1px dashed rgba(148, 163, 184, 0.55);
    border-radius: 8px;
    padding: 8px 10px;
    background: rgba(248, 250, 252, 0.75);

    summary {
      cursor: pointer;
      font-size: 12px;
      color: #475569;
      font-weight: 600;
      outline: none;
      user-select: none;
    }
  }

  .ai-analysis-content {
    gap: 14px !important;
  }

  .ai-analysis-source {
    display: block;
    margin-top: 2px;
    font-size: 11px;
    letter-spacing: 0.02em;
    opacity: 0.86;
  }

  .ai-analysis-card {
    border-radius: 12px;
    border: 1px solid rgba(125, 211, 252, 0.38);
    background: linear-gradient(180deg, rgba(248, 252, 255, 0.96) 0%, rgba(241, 245, 249, 0.96) 100%);

    :deep(.n-card-header) {
      padding-bottom: 10px;
    }

    :deep(.n-card-header__main) {
      font-size: 15px;
      font-weight: 700;
      color: #0f172a;
    }
  }

  .ai-analysis-report {
    padding: 14px 16px;
    min-height: 200px;
    border-radius: 10px;
    border: 1px solid rgba(148, 163, 184, 0.22);
    background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
    color: #1f2937;
    font-family: 'Microsoft YaHei', 'PingFang SC', 'Hiragino Sans GB', 'Noto Sans SC', sans-serif;
    font-weight: 400;
    letter-spacing: 0.01em;
    font-size: 13px;
    line-height: 1.72;
  }

  /* 筛选框（从事件看板复用） */
  .filter {
    width: 100%;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    background: white;
    transition: all 0.3s ease;
    overflow: hidden;

    &:hover {
      border-color: #165dff;
      box-shadow: 0 2px 8px rgba(22, 93, 255, 0.1);
    }
  }

  .filter-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    cursor: pointer;
    background: #f8fafc;
    border-bottom: 1px solid #e5e7eb;
    transition: all 0.2s ease;

    &:hover {
      background: #f1f5f9;
    }

    &:active {
      background: #e2e8f0;
    }
  }

  .filter-header-content {
    display: flex;
    align-items: center;
    gap: 8px;

    .n-text {
      font-size: 14px;
      font-weight: 500;
      color: #1e293b;
    }
  }

  .filter-header-action {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .filter-toggle-text {
    font-size: 12px;
    transition: color 0.2s ease;
  }

  .filter-content {
    padding: 16px;
  }

  .filter-row {
    display: flex;
    gap: 16px;
    margin-bottom: 16px;

    @media (max-width: 768px) {
      flex-direction: column;
      gap: 12px;
    }
  }

  .filter-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .filter-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    font-weight: 500;
    color: #64748b;
    line-height: 1;
  }

  .filter-input {
    width: 100%;
  }

  .filter-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding-top: 8px;
    border-top: 1px dashed #e5e7eb;
  }

  .filter-button {
    min-width: 80px;
  }

  .repo-select-scroll-body {
    height: 620px;
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: 6px;
  }

  /* 筛选面板动画 */
  .filter-collapse-enter-active,
  .filter-collapse-leave-active {
    transition: all 0.3s ease;
    max-height: 300px;
    overflow: hidden;
  }

  .filter-collapse-enter-from,
  .filter-collapse-leave-to {
    max-height: 0;
    opacity: 0;
    transform: translateY(-10px);
  }

  .filter-collapse-enter-to,
  .filter-collapse-leave-from {
    max-height: 300px;
    opacity: 1;
    transform: translateY(0);
  }

  @keyframes progress-shimmer {
    0% {
      background-position: 0% 0;
    }

    100% {
      background-position: 200% 0;
    }
  }

  @media (max-width: 768px) {
    .extract-process-page {
      padding: 12px;
    }

    .build-progress-top {
      align-items: flex-start;
      flex-direction: column;
    }

    .build-progress-metric {
      min-width: auto;
      text-align: left;
      font-size: 22px;
    }

    .quality-report-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .ai-analysis-report {
      min-height: 170px;
      padding: 12px 13px;
      font-size: 12px;
      line-height: 1.64;
    }

    .repo-select-scroll-body {
      height: 70vh;
    }
  }
</style>
