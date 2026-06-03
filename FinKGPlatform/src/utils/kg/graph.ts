export type EntityEventLabel = '实体' | '事件';

// 统一图谱视觉风格（用于预览与编辑）
export const ENTITY_COLOR = '#1890ff';
export const EVENT_COLOR = '#fa8c16';
export const EDGE_COLOR = '#9fb3c8';

export const NODE_CATEGORY_COLORS = {
  '事件-宏观': '#f97316',
  '事件-行业': '#f59e0b',
  '事件-情绪': '#ef4444',
  '事件-交易': '#22c55e',
  '事件-其他': '#fb7185',
  '实体-公司': '#38bdf8',
  '实体-机构': '#60a5fa',
  '实体-人物': '#2dd4bf',
  '实体-地点': '#34d399',
  '实体-时间': '#facc15',
  '实体-指标': '#a3e635',
  '实体-主题': '#f472b6',
  '实体-其他': '#94a3b8',
} as const;

export type NodeVisualCategory = keyof typeof NODE_CATEGORY_COLORS;

const NODE_CATEGORY_ORDER: NodeVisualCategory[] = [
  '事件-宏观',
  '事件-行业',
  '事件-情绪',
  '事件-交易',
  '事件-其他',
  '实体-公司',
  '实体-机构',
  '实体-人物',
  '实体-地点',
  '实体-时间',
  '实体-指标',
  '实体-主题',
  '实体-其他',
];

function asString(v: any): string {
  if (v === null || v === undefined) return '';
  return String(v);
}

function shortText(text: string, maxLen = 14): string {
  const t = (text || '').trim();
  if (!t) return '-';
  if (t.length <= maxLen) return t;
  return t.slice(0, maxLen - 1) + '…';
}

// 后端 node.type 可能是: 0/1, '0'/'1', '实体'/'事件', 'entity'/'event'
export function normalizeNodeCategory(nodeType: any): 0 | 1 {
  const t = asString(nodeType).toLowerCase();
  if (t === '1' || t === 'event' || t === '事件') return 1;
  return 0;
}

// 从 node 自身推断实体/事件：优先用 type，其次用 id 前缀（id 形如 "1_xxx" 或 "0_xxx"）
export function normalizeNodeCategoryFromNode(node: any): 0 | 1 {
  const typeCategory = normalizeNodeCategory(node?.type);
  const typeRaw = asString(node?.type).trim();
  const idStr = asString(node?.id);
  const prefix = idStr.split('_')[0];

  // 若当前 node.type 明确是事件，则优先以 node.type 为准（避免用户在编辑页修改后预览仍被 id 前缀“覆盖”）
  if (typeCategory === 1) return 1;

  // 历史数据可能在 Neo4j 写入阶段把所有节点都写成“实体”，这时用 id 前缀做兜底纠错
  if ((typeRaw === '实体' || typeRaw.toLowerCase() === 'entity') && prefix === '1') return 1;

  return typeCategory;
}

export function normalizeNodeTypeLabel(nodeType: any): EntityEventLabel {
  return normalizeNodeCategory(nodeType) === 1 ? '事件' : '实体';
}

function includesAny(text: string, terms: string[]): boolean {
  return terms.some((term) => text.includes(term));
}

function mergeNodeHintText(node: any): string {
  const p = node?.properties || {};
  return [
    node?.key,
    node?.value,
    node?.name,
    node?.type,
    p?.label,
    p?.entity_type,
    p?.event_type,
    p?.eventType,
    p?.category,
    p?.domain,
    p?.kind,
    p?.context,
  ]
    .map((v) => asString(v).toLowerCase())
    .join(' | ');
}

function classifyEventNode(node: any): NodeVisualCategory {
  const text = mergeNodeHintText(node);

  if (includesAny(text, ['macro', '宏观', '央行', '经济', '监管', '政策'])) return '事件-宏观';
  if (includesAny(text, ['industry', '行业', '赛道', '板块'])) return '事件-行业';
  if (includesAny(text, ['sentiment', '情绪', '舆情', '预期'])) return '事件-情绪';
  if (includesAny(text, ['trading', '交易', '成交', '异动', '涨跌', '资金'])) return '事件-交易';

  return '事件-其他';
}

function classifyEntityNode(node: any): NodeVisualCategory {
  const text = mergeNodeHintText(node);

  if (includesAny(text, ['company', 'corp', 'co.,', '股票', '个股', '上市', '证券', 'ticker'])) {
    return '实体-公司';
  }
  if (includesAny(text, ['institution', 'bank', '基金', '券商', '机构', '政府', '协会', '央行'])) {
    return '实体-机构';
  }
  if (includesAny(text, ['person', '人物', '高管', '董事', 'ceo', 'cfo', '经理', '分析师'])) {
    return '实体-人物';
  }
  if (includesAny(text, ['location', '地区', '城市', '国家', '海外', '本土', 'region'])) {
    return '实体-地点';
  }
  if (includesAny(text, ['time', 'date', '季度', '年份', '月', '日', 'period'])) {
    return '实体-时间';
  }
  if (includesAny(text, ['indicator', '指数', '市盈率', '收益率', '波动率', '估值', '指标'])) {
    return '实体-指标';
  }
  if (includesAny(text, ['theme', 'topic', '概念', '主题', '风格', '逻辑'])) {
    return '实体-主题';
  }

  return '实体-其他';
}

export function resolveNodeVisualCategory(node: any): NodeVisualCategory {
  const category = normalizeNodeCategoryFromNode(node);
  return category === 1 ? classifyEventNode(node) : classifyEntityNode(node);
}

export function sortVisualCategoryNames(categoryNames: string[]): string[] {
  const weight = new Map<string, number>(NODE_CATEGORY_ORDER.map((name, index) => [name, index]));
  return [...categoryNames].sort((a, b) => {
    const wa = weight.has(a) ? (weight.get(a) as number) : Number.MAX_SAFE_INTEGER;
    const wb = weight.has(b) ? (weight.get(b) as number) : Number.MAX_SAFE_INTEGER;
    if (wa !== wb) return wa - wb;
    return a.localeCompare(b, 'zh-CN');
  });
}

export function getNodeVisualColor(categoryName: string): string {
  return NODE_CATEGORY_COLORS[categoryName as NodeVisualCategory] || '#94a3b8';
}

// 处理抽取结果里“太泛”的节点名，让用户至少知道它在图谱里扮演什么语义
const GENERIC_NODE_TERMS = new Set<string>(['影响', 'impact', 'Impact']);

export function normalizeNodeDisplayName(node: any): string {
  const raw = asString(node?.value || node?.name || node?.id);
  const key = asString(node?.key);
  const context = asString(node?.properties?.context || node?.properties?.description);

  // 例如“影响”这类词仅靠字面无法理解，这里用 key 做最小补全
  if (GENERIC_NODE_TERMS.has(raw)) {
    if (key) return `${raw}(${shortText(key, 10)})`;
    if (context) return `${raw}(${shortText(context, 10)})`;
  }

  return shortText(raw, 18);
}

// 处理关系抽取结果里“太泛”的关系描述，比如 value=“影响”
const GENERIC_EDGE_TERMS = new Set<string>(['影响', 'impact', 'Impact']);

export function normalizeEdgeDisplayLabel(edge: any, fromNode: any, toNode: any): string {
  const value = asString(edge?.value);
  const eventRel = asString(edge?.eventRel);
  const relType = asString(edge?.type);

  const verb = value || eventRel || relType;

  if (GENERIC_EDGE_TERMS.has(value) || GENERIC_EDGE_TERMS.has(verb)) {
    const fromName = asString(fromNode?.value || fromNode?.name || fromNode?.id);
    const toName = asString(toNode?.value || toNode?.name || toNode?.id);
    return `影响：${shortText(fromName)} -> ${shortText(toName)}`;
  }

  // 其他情况：优先显示 value，其次 eventRel
  if (value) return shortText(value, 22);
  if (eventRel) return shortText(eventRel, 22);
  return shortText(relType, 22);
}

