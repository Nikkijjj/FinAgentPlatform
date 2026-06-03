import json
from routes.llmGenKG_api import fetch_samples_from_mongo
from agents.master_build_workflow import invoke_master_build

project_id = '75372133'
sample_ids = ['69e3482c01a14c7e13d37f59','69e3482c01a14c7e13d37f5a','69e3482c01a14c7e13d37f5b','69e3482c01a14c7e13d37f5c']
plan_overrides = {
    'enable_graph_optimization': True,
    'enable_isolated_repair': True,
    'persistence_mode': 'replace',
    'mode': 'full'
}

samples = fetch_samples_from_mongo(sample_ids)
print('samples=', len(samples))
state = invoke_master_build(
    project_id=project_id,
    sample_ids=sample_ids,
    samples=samples,
    plan_overrides=plan_overrides,
    has_incremental_impact=False,
)
print('error=', state.get('error'))
print('run_id=', state.get('run_id'))
print('nodes=', len(state.get('nodes') or []), 'edges=', len(state.get('edges') or []), 'conflicts=', len(state.get('conflicts') or []))

enr = state.get('graph_enrichment') or {}
opt = enr.get('graph_optimization') if isinstance(enr, dict) else None
quality = enr.get('quality_score') if isinstance(enr, dict) else None
out = {
    'run_id': state.get('run_id'),
    'error': state.get('error'),
    'node_count': len(state.get('nodes') or []),
    'edge_count': len(state.get('edges') or []),
    'conflict_count': len(state.get('conflicts') or []),
    'graph_optimization': opt,
    'quality_score': quality,
}
with open('master_build_direct_result.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print('saved master_build_direct_result.json')
