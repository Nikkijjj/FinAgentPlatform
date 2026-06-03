// import { requestAPI } from '@/api/response';

// // 样本数据相关 API（/old-api/extractSample）

// export interface FetchAllTextDataParams {
//   project_id: string;
//   page: number;
//   page_size: number;
// }

// export interface TextSampleItem {
//   // 操作库样本主键（后端实际应返回该字段）
//   id?: string;
//   index: number;
//   title: string;
//   content: string;
//   publishTime: string;
//   summary: string;
//   stock_num?: string;
// }

// export async function fetchAllTextData(params: FetchAllTextDataParams) {
//   return await requestAPI('/old-api/extractSample/getAllTextData', 'post', null, params) as {
//     status: number;
//     data: TextSampleItem[];
//     count: number;
//     project_id: string;
//     page: number;
//     page_size: number;
//   };
// }

// export interface SaveSelectDataParams {
//   project_id: string;
//   announcement_ids: (string | number)[];
// }

// export async function saveSelectData(params: SaveSelectDataParams) {
//   return await requestAPI('/old-api/extractSample/saveSelectData', 'post', null, params) as {
//     status: number;
//     msg: string;
//     added_count?: number;
//     total_count?: number;
//   };
// }

// export interface ProjectAnnouncementItem {
//   id: string;
//   title: string;
//   content: string;
//   date: string;
//   stock_num: string;
// }

// export async function getProjectAnnouncements(project_id: string) {
//   return await requestAPI('/old-api/extractSample/getProjectAnnouncements', 'post', null, {
//     project_id,
//   }) as {
//     status: number;
//     data: ProjectAnnouncementItem[];
//     count: number;
//   };
// }

// export interface DeleteSelectedDataParams {
//   project_id: string;
//   ids: (string | number)[];
// }

// export async function deleteSelectedData(params: DeleteSelectedDataParams) {
//   return await requestAPI('/old-api/extractSample/deleteSelectedData', 'post', null, params) as {
//     status: number;
//     msg: string;
//     deleted_count?: number;
//     remaining_count?: number;
//   };
// }

// // 知识图谱构建相关 API（/llmGenKG）

// export interface ExtractNodesParams {
//   project_id: string;
//   announcement_ids: (string | number)[];
// }

// // 提示：该接口为 NDJSON 流式返回，这里只定义类型，具体请求在页面中用 fetch 手动处理
// export interface ExtractNodesFinalResult {
//   status: 'complete';
//   progress: number;
//   message: string;
//   data: {
//     nodes: any[];
//     count: number;
//     project_id: string;
//   };
// }

// export async function getNodesByProject(project_id: string) {
//   return await requestAPI(`/llmGenKG/get_nodes_by_project?project_id=${encodeURIComponent(project_id)}`, 'get') as {
//     success: boolean;
//     status: number;
//     message: string;
//     data?: {
//       nodes: any[];
//       count: number;
//       project_id: string;
//     };
//   };
// }

// export interface ExtractRelationsParams {
//   project_id: string;
//   relation_type?: 'causal' | 'temporal' | 'general';
//   model_base?: 'llm' | string;
// }

// export async function extractRelations(params: ExtractRelationsParams) {
//   return await requestAPI('/llmGenKG/extract_relations', 'post', null, params) as {
//     success: boolean;
//     status: number;
//     message: string;
//     data?: {
//       edges: any[];
//       count: number;
//       project_id: string;
//     };
//   };
// }

// export async function getEdgesByProject(project_id: string) {
//   return await requestAPI(`/llmGenKG/get_edges_by_project?project_id=${encodeURIComponent(project_id)}`, 'get') as {
//     success: boolean;
//     status: number;
//     message: string;
//     data?: {
//       edges: any[];
//       count: number;
//       project_id: string;
//     };
//   };
// }

// export interface CheckExtractionStatusResult {
//   success: boolean;
//   has_nodes: boolean;
//   has_edges: boolean;
//   status: number;
// }

// export async function checkExtractionStatus(project_id: string) {
//   return await requestAPI('/llmGenKG/check_extraction_status', 'post', null, {
//     project_id,
//   }) as CheckExtractionStatusResult;
// }

import { requestAPI } from '@/api/response';

// 样本数据相关 API（/old-api/extractSample）

export interface FetchAllTextDataParams {
  project_id: string;
  page: number;
  page_size: number;
}

export interface TextSampleItem {
  // 操作库样本主键（后端实际应返回该字段）
  id?: string;
  index: number;
  title: string;
  content: string;
  publishTime: string;
  summary: string;
  stock_num?: string;
}

export async function fetchAllTextData(params: FetchAllTextDataParams) {
  return (await requestAPI('/old-api/extractSample/getAllTextData', 'post', null, params)) as {
    status: number;
    data: TextSampleItem[];
    count: number;
    project_id: string;
    page: number;
    page_size: number;
  };
}

export interface SaveSelectDataParams {
  project_id: string;
  announcement_ids: (string | number)[];
}

export async function saveSelectData(params: SaveSelectDataParams) {
  return (await requestAPI('/old-api/extractSample/saveSelectData', 'post', null, params)) as {
    status: number;
    msg: string;
    added_count?: number;
    total_count?: number;
  };
}

/**
 * 项目样本数据项
 * 与操作库事件表结构保持一致：
 * - 事件类型 / 子类 / 影响级别 / 情感 / 标的
 * - 事件时间 publishTime
 * - 摘要 content
 * - id 为事件在 event_data.data 中的 "_id"
 */
export interface ProjectAnnouncementItem {
  id: string; // 对应 event_data.data._id
  index: number;
  event_type?: string;
  event_subtype?: string;
  impact_level?: string;
  sentiment?: string;
  symbol?: string;
  event_description: string;
  event_time: string;
  created_at?: string;
}

export async function getProjectAnnouncements(project_id: string) {
  return (await requestAPI('/old-api/extractSample/getProjectAnnouncements', 'post', null, {
    project_id,
  })) as {
    status: number;
    data: ProjectAnnouncementItem[];
    count: number;
  };
}

export async function getProjectBaseInfo(project_id: string) {
  return (await requestAPI('/old-api/getProjectBaseInfo', 'post', null, {
    project_id,
  })) as {
    status: number;
    msg: string;
    data: {
      project_id: string;
      project_name: string;
      project_desc: string;
      creator: string;
    } | null;
  };
}

/** MongoDB event_data 直连检索（抽取步骤样本圈选用） */
export interface SearchMongoEventsParams {
  page?: number;
  page_size?: number;
  stock_code?: string;
  keyword?: string;
  start_time?: string;
  end_time?: string;
  event_type?: string | string[];
  sort_field?: string;
  sort_order?: 1 | -1;
}

export async function searchMongoEvents(params: SearchMongoEventsParams) {
  return (await requestAPI('/old-api/extractSample/searchMongoEvents', 'post', null, params)) as any;
}

export interface DeleteSelectedDataParams {
  project_id: string;
  ids: (string | number)[];
}

export async function deleteSelectedData(params: DeleteSelectedDataParams) {
  return (await requestAPI('/old-api/extractSample/deleteSelectedData', 'post', null, params)) as {
    status: number;
    msg: string;
    deleted_count?: number;
    remaining_count?: number;
  };
}

// 知识图谱构建相关 API（/llmGenKG）

export interface ExtractNodesParams {
  project_id: string;
  announcement_ids: (string | number)[];
}

// 提示：该接口为 NDJSON 流式返回，这里只定义类型，具体请求在页面中用 fetch 手动处理
export interface ExtractNodesFinalResult {
  status: 'complete';
  progress: number;
  message: string;
  data: {
    nodes: any[];
    count: number;
    project_id: string;
  };
}

export async function getNodesByProject(project_id: string) {
  return (await requestAPI(
    `/old-api/llmGenKG/get_nodes_by_project?project_id=${encodeURIComponent(project_id)}`,
    'get'
  )) as {
    success: boolean;
    status: number;
    message: string;
    data?: {
      nodes: any[];
      count: number;
      project_id: string;
    };
  };
}

export interface ExtractRelationsParams {
  project_id: string;
  relation_type?: 'causal' | 'temporal' | 'general';
  model_base?: 'llm' | string;
}

export async function extractRelations(params: ExtractRelationsParams) {
  return (await requestAPI('/old-api/llmGenKG/extract_relations', 'post', null, params)) as {
    success: boolean;
    status: number;
    message: string;
    data?: {
      edges: any[];
      count: number;
      project_id: string;
    };
  };
}

export async function getEdgesByProject(project_id: string) {
  return (await requestAPI(
    `/old-api/llmGenKG/get_edges_by_project?project_id=${encodeURIComponent(project_id)}`,
    'get'
  )) as {
    success: boolean;
    status: number;
    message: string;
    data?: {
      edges: any[];
      count: number;
      project_id: string;
    };
  };
}

export async function getNeo4jGraph(project_id: string) {
  return (await requestAPI(
    `/old-api/llmGenKG/get_neo4j_graph?project_id=${encodeURIComponent(project_id)}`,
    'get'
  )) as {
    success: boolean;
    status: number;
    message: string;
    data?: {
      nodes: any[];
      edges: any[];
      project_id: string;
    };
  };
}

/** 按 run_id 获取历史快照图谱 */
export async function getNeo4jGraphByRun(project_id: string, run_id: string) {
  return (await requestAPI(
    `/old-api/llmGenKG/get_neo4j_graph_by_run?project_id=${encodeURIComponent(project_id)}&run_id=${encodeURIComponent(run_id)}`,
    'get'
  )) as {
    success: boolean;
    status: number;
    message: string;
    data?: {
      nodes: any[];
      edges: any[];
      project_id: string;
      run_id: string;
    };
  };
}

/** 按 run_id 获取构建流程报告（workflow_meta） */
export async function getWorkflowReportByRun(project_id: string, run_id: string) {
  return (await requestAPI(
    `/old-api/llmGenKG/get_workflow_report_by_run?project_id=${encodeURIComponent(project_id)}&run_id=${encodeURIComponent(run_id)}`,
    'get'
  )) as {
    success: boolean;
    status: number;
    message: string;
    data?: {
      project_id: string;
      run_id: string;
      created_at?: string;
      workflow_meta?: WorkflowMeta;
    };
  };
}

/** 基于 workflow_meta 生成 AI 质量分析小报告 */
export async function analyzeQualityReportAI(params: {
  project_id?: string;
  run_id?: string;
  workflow_meta?: WorkflowMeta;
  conflicts?: any[];
  user_hint?: string;
}) {
  return (await requestAPI('/old-api/llmGenKG/analyze_quality_report_ai', 'post', null, params)) as {
    success: boolean;
    status: number;
    message: string;
    data?: {
      project_id: string;
      run_id: string;
      analysis_report: string;
      metrics?: Record<string, unknown>;
    };
  };
}

export interface ExtractionHistoryItem {
  run_id: string;
  run_type: string;
  created_at: string;
  nodes_count: number;
  edges_count: number;
  /** 后端生成或保存时的列表标题（与历史对话「首条摘要」类似） */
  title?: string | null;
  user_id?: string | null;
}

export const EXTRACTION_HISTORY_REFRESH_EVENT = 'finkg-extraction-history-refresh';

/** 获取项目抽取历史列表（与历史对话一致：传当前用户 id 仅看自己相关的记录） */
export async function getExtractionHistoryList(
  project_id: string,
  opts?: { user_id?: string; creator?: string }
) {
  const q = new URLSearchParams({ project_id });
  const uid = String(opts?.user_id || opts?.creator || '').trim();
  if (uid) {
    q.set('user_id', uid);
  }
  return (await requestAPI(
    `/old-api/llmGenKG/get_extraction_history_list?${q.toString()}`,
    'get'
  )) as {
    success: boolean;
    status: number;
    message: string;
    data?: {
      items: ExtractionHistoryItem[];
      project_id: string;
    };
  };
}

/** 删除一条抽取历史快照（需与项目创建者或记录 user_id 一致） */
export async function deleteExtractionHistory(params: {
  project_id: string;
  run_id: string;
  user_id?: string;
  creator?: string;
  username?: string;
}) {
  return (await requestAPI('/old-api/llmGenKG/delete_extraction_history', 'post', null, params)) as {
    success: boolean;
    status: number;
    message: string;
  };
}

export async function renameExtractionHistory(params: {
  project_id: string;
  run_id: string;
  title: string;
  user_id?: string;
  creator?: string;
  username?: string;
}) {
  return (await requestAPI('/old-api/llmGenKG/rename_extraction_history', 'post', null, params)) as {
    success: boolean;
    status: number;
    message: string;
    data?: {
      run_id: string;
      title: string;
    };
  };
}

export async function createExtractionHistorySnapshot(params: {
  project_id: string;
  title: string;
  source_run_id?: string;
  is_empty?: boolean;
  user_id?: string;
  creator?: string;
  username?: string;
}) {
  return (await requestAPI(
    '/old-api/llmGenKG/create_extraction_history_snapshot',
    'post',
    null,
    params
  )) as {
    success: boolean;
    status: number;
    message: string;
    data?: {
      run_id: string;
      project_id: string;
      title: string;
      nodes_count: number;
      edges_count: number;
    };
  };
}

export async function checkoutExtractionHistory(params: {
  project_id: string;
  run_id: string;
  user_id?: string;
  username?: string;
  creator?: string;
}) {
  return (await requestAPI('/old-api/llmGenKG/checkout_extraction_history', 'post', null, params)) as {
    success: boolean;
    status: number;
    message: string;
  };
}

export interface CheckExtractionStatusResult {
  success: boolean;
  has_nodes: boolean;
  has_edges: boolean;
  status: number;
}

export async function checkExtractionStatus(project_id: string) {
  return (await requestAPI('/old-api/llmGenKG/check_extraction_status', 'post', null, {
    project_id,
  })) as CheckExtractionStatusResult;
}

export interface PreviewMasterBuildPathResult {
  success: boolean;
  status: number;
  message: string;
  data?: {
    kind: 'noop' | 'incremental_only' | 'prune_only' | 'incremental_and_prune' | 'full' | string;
    message: string;
    delta?: Record<string, unknown>;
  };
}

export async function previewMasterBuildPath(project_id: string, sample_ids: (string | number)[]) {
  return (await requestAPI('/old-api/llmGenKG/preview_master_build_path', 'post', null, {
    project_id,
    sample_ids,
  })) as PreviewMasterBuildPathResult;
}

/** 一键构建（Master Agent）：自动完成节点抽取、关系抽取与冲突检测 */
export interface RunMasterAgentParams {
  project_id: string;
  sample_ids: (string | number)[];
  build_plan?: Record<string, unknown>;
  user_id?: string;
  creator?: string;
  username?: string;
}

export interface WorkflowQualityReport {
  grade?: string;
  overall_score?: number;
  node_property_fill_rate?: number;
  edge_property_fill_rate?: number;
  semantic_relation_ratio?: number;
  conflict_count?: number;
}

export interface WorkflowMeta {
  run_id?: string;
  quality_report?: WorkflowQualityReport;
  [key: string]: unknown;
}

/** 更新节点 */
export async function updateNode(params: {
  project_id: string;
  node_id: string;
  value?: string;
  type?: string;
  key?: string;
  properties?: Record<string, unknown>;
}) {
  return (await requestAPI('/old-api/llmGenKG/update_node', 'post', null, params)) as {
    success: boolean;
    status: number;
    message: string;
  };
}

/** 删除节点（会级联删除关联关系） */
export async function deleteNode(params: { project_id: string; node_id: string }) {
  return (await requestAPI('/old-api/llmGenKG/delete_node', 'post', null, params)) as {
    success: boolean;
    status: number;
    message: string;
    data?: {
      deleted_node_id: string;
      deleted_related_edges_count: number;
      affected_node_ids: string[];
      isolated_node_ids: string[];
      project_id: string;
    };
  };
}

/** 属性补全 Agent */
export async function attributeCompletion(params: {
  project_id: string;
  target_type: 'node' | 'edge';
  target_id: string;
  apply_update?: boolean;
}) {
  return (await requestAPI('/old-api/llmGenKG/attribute_completion', 'post', null, params)) as {
    success: boolean;
    status: number;
    message: string;
    data?: {
      target_type: string;
      target_id: string;
      completed_properties: Record<string, unknown>;
      applied: boolean;
    };
  };
}

/** 更新边(关系) */
export async function updateEdge(params: {
  project_id: string;
  edge_id: string;
  value?: string;
  eventRel?: string;
  properties?: Record<string, unknown>;
}) {
  return (await requestAPI('/old-api/llmGenKG/update_edge', 'post', null, params)) as {
    success: boolean;
    status: number;
    message: string;
  };
}

/** 删除单条关系 */
export async function deleteEdge(params: { project_id: string; edge_id: string }) {
  return (await requestAPI('/old-api/llmGenKG/delete_edge', 'post', null, params)) as {
    success: boolean;
    status: number;
    message: string;
    data?: {
      deleted_edge_id: string;
      affected_node_ids: string[];
      isolated_node_ids: string[];
      project_id: string;
    };
  };
}

export async function runMasterAgent(params: RunMasterAgentParams) {
  return (await requestAPI('/old-api/llmGenKG/master_agent_run', 'post', null, params)) as {
    success: boolean;
    status: number;
    message: string;
    data?: {
      samples: any[];
      nodes: any[];
      edges: any[];
      conflicts: any[];
      workflow_meta?: WorkflowMeta;
      graph: { nodes: any[]; edges: any[]; conflicts?: any[]; stats?: any };
    };
  };
}

export interface StartMasterAgentAsyncTaskResult {
  success: boolean;
  status: number;
  message: string;
  data?: {
    task_id: string;
    project_id: string;
    status: 'pending' | 'running' | 'success' | 'error' | string;
    run_id?: string;
  };
}

export async function startMasterAgentAsyncTask(params: RunMasterAgentParams) {
  return (await requestAPI('/old-api/llmGenKG/master_agent_run_async', 'post', null, params)) as StartMasterAgentAsyncTaskResult;
}

export interface MasterAgentTaskStatus {
  task_id: string;
  status: 'pending' | 'running' | 'success' | 'error' | string;
  progress?: number;
  phase?: 'nodes' | 'relations' | string;
  label?: string;
  message?: string;
  error?: string;
  project_id?: string;
  run_id?: string;
  created_at?: string;
  updated_at?: string;
}

export async function getMasterAgentTaskStatus(task_id: string) {
  return (await requestAPI(
    `/old-api/llmGenKG/master_agent_task_status?task_id=${encodeURIComponent(task_id)}`,
    'get'
  )) as {
    success: boolean;
    status: number;
    message: string;
    data?: MasterAgentTaskStatus;
  };
}
