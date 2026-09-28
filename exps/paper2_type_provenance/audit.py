"""Finite source inventory; explicit types require source-compatible identity."""
import csv,gzip,hashlib,json,subprocess,sys
from pathlib import Path
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper2_rule_integration.audit import load_rules
HERE=Path(__file__).resolve().parent
PLACEHOLDERS={'','unknown','enhanced','other','none','null'}
def semantic_type(value):return bool(value) and str(value).strip().lower() not in PLACEHOLDERS

def main():
 tracked=[ROOT/p for p in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0') if p]
 sources=[p for p in tracked if p.suffix=='.csv' and 'nodes' in p.name and p.parts[len(ROOT.parts)] in ['data','exps','evaluate_kg']]
 inventory=[];candidates=[];hashes={};base={}
 for domain in ['政务','金融','环境']:
  with (ROOT/'data'/f'{domain}_nodes.csv').open(encoding='utf-8-sig') as f:base[domain]={r['id']:r for r in csv.DictReader(f)}
 for p in sources:
  with p.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f));cols=list(rows[0]) if rows else []
  hashes[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
  typed=[r for r in rows if semantic_type(r.get('node_type'))]
  inventory.append({'path':str(p.relative_to(ROOT)),'rows':len(rows),'columns':cols,'type_counts':dict(Counter(r.get('node_type','<no column>') for r in rows)),'semantic_type_rows':len(typed)})
  for r in typed:
   # Local integer IDs may be reused between exports; never join on them alone.
   same=[d for d,ns in base.items() if r.get('id') in ns and r.get('name')==ns[r['id']].get('name')]
   candidates.append({'path':str(p.relative_to(ROOT)),'node_id':r.get('id'),'name':r.get('name'),'explicit_type':r['node_type'],'exact_id_name_candidate_domains':same,'status':'requires_shared_document_provenance' if same else 'different_graph_no_identity_match','applied':False})
 rawpaths=[ROOT/'data'/p for p in ['政务.jsonl','金融.jsonl','环境_original.jsonl']]
 raw=[]
 for p in rawpaths:
  with p.open() as f:rows=[json.loads(l) for l in f if l.strip()]
  hashes[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
  raw.append({'path':str(p.relative_to(ROOT)),'rows':len(rows),'keys':sorted({k for r in rows for k in r}),'entity_type_fields':sum(any(k in r for k in ['entity_types','entities','node_type','subject_type','object_type']) for r in rows)})
 # Inspect explicit checkpoint output schema without treating unrelated TNEWS as this graph.
 for p in [ROOT/'exps/neo4j_graph_builder_benchmark'/n for n in ['mcp_checkpoint.json','neo4j_checkpoint.json']]:
  data=json.loads(p.read_text());hashes[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
  raw.append({'path':str(p.relative_to(ROOT)),'keys':list(data),'status':'TNEWS baseline checkpoint; different document universe, no source identity mapping to original three graphs'})
 rules,packets,_=load_rules();relations=defaultdict(Counter);maps=[]
 for domain in base:
  p=ROOT/'data'/f'{domain}_relationships.csv'
  with p.open(encoding='utf-8-sig') as f:edges=list(csv.DictReader(f))
  hashes[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
  relations[domain].update(e['relation_type'] for e in edges)
  for rel,n in sorted(relations[domain].items()):
   matching=[r['rule_id'] for r in rules if r['pattern'][1]==rel]
   maps.append({'domain':domain,'relation':rel,'edge_occurrences':n,'matching_rule_ids':matching,'mapping':'exact_identity' if matching else 'no_exact_rule_relation','typed_edge_coverage':0})
 for p in [Path(__file__),ROOT/'scripts/converters/bulk_jsonl_to_csv_enhanced.py',ROOT/'kg_server.py',ROOT/'kg_utils.py',ROOT/'exps/paper2_offline_revision/rule_lineage.jsonl.gz']:
  hashes[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
 result={'node_file_count':len(inventory),'inventory':inventory,'explicit_candidates':candidates,'raw_input_schemas':raw,'restored_types':0,'original_edge_count':sum(sum(x.values()) for x in relations.values()),'relation_mapping':maps,'scope':'Tracked node CSVs under data/exps/evaluate_kg plus three original raw JSONL and two extraction checkpoints; finite audited inventory, not a claim about missing external/private artifacts.','exclusions':'Unknown/Enhanced/Other are not usable semantic types. Enhanced assigned by converter as processing tag. RuleTest/gold-derived labels and name heuristics excluded. No ID-only or name-only cross-export join.','sha256':hashes,'api_calls':0}
 (HERE/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 (HERE/'candidate_mappings.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in candidates))
 lines=['# Paper2 类型与词汇来源审计','',f'检查 {len(inventory)} 个已跟踪节点 CSV、3 个原始文档 JSONL 和 2 个不同任务的抽取 checkpoint。原始三图共 {result["original_edge_count"]:,} 条边；本次可追溯恢复类型数为 **0**。','', '`Enhanced` 来自 `scripts/converters/bulk_jsonl_to_csv_enhanced.py` 的固定处理标记，不是实体类型。`Unknown` 和默认 `Other` 同样不用于执行类型规则。','', '|节点文件|行数|类型统计|','|---|---:|---|']
 for r in inventory:lines.append(f"|{r['path']}|{r['rows']}|{json.dumps(r['type_counts'],ensure_ascii=False)}|")
 lines+=['','显式类型候选、关系精确映射和每份文件的 SHA256 见 `results.json`。仅数值 ID 相同不足以确认是同一实体；没有同一来源文档／导出映射时不自动回填。','', '下一步所需输入：每个实体的来源文档 ID、来源跨度、显式类型与类型词表版本；独立核验的人可回填这些字段。API 可以提议类型，但不能同时作为规则有效性或最终编辑的独立参考。当前缺口不能通过直接启动 DDQN 训练解决。','', '审计只覆盖清单中的本地档案；如另有原始带类型的抽取日志，可以追加新版本审计。']
 (HERE/'report_zh.md').write_text('\n'.join(lines)+'\n');print(json.dumps({'node_files':len(inventory),'explicit_candidates':len(candidates),'restored':0,'edges':result['original_edge_count']}))
if __name__=='__main__':main()
