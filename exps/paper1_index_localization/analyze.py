"""Post-hoc localization, no gold enters the fixed index or model prompts."""
import csv,hashlib,json,re,sys
from pathlib import Path
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_receipt_followup.protocol import evidence_index
from content_enhancement.source_validation import normalize_source_whitespace as norm
from exps.paper1_mechanism_audit.protocol import read_jsonl
from exps.paper1_ablation_completion.analyze import write_csv
HERE=Path(__file__).resolve().parent;SOURCE=ROOT/'exps/paper1_receipt_followup/test'
def locate(lines,value):
    # Keep positions on the actual contiguous source; never join selected lines.
    chars=[];ids=[]
    for i,line in enumerate(lines,1):
        text=norm(line)
        if not text:continue
        if chars:chars.append(' ');ids.append(0)
        chars.extend(text);ids.extend([i]*len(text))
    text=''.join(chars);value=norm(value);spans=[]
    if not value:return []
    start=0
    while True:
        p=text.find(value,start)
        if p<0:break
        spans.append(sorted(set(ids[p:p+len(value)])-{0}));start=p+1
    return spans
def classify(spans,selected):
    if not spans:return 'not_source_matched'
    return 'indexed' if any(set(s)<=set(selected) for s in spans) else 'outside_index'
def main():
    inputs=read_jsonl(SOURCE/'inputs.jsonl');refs={r['case_id']:r for r in read_jsonl(SOURCE/'references.jsonl')}
    with (SOURCE/'per_field.csv').open() as f:old=list(csv.DictReader(f))
    outcomes={(r['case_id'],r['relation'],r['method']):r for r in old}
    rows=[]
    for inp in inputs:
        index=evidence_index(inp['source_lines'])
        for t in refs[inp['case_id']]['triples']:
            field=t['relation'];idx=index[field];spans=locate(inp['source_lines'],t['tail']);anchors=idx['anchor_lines'];near=idx['nearby_lines']
            # Observable distractor proxies, not manually verified candidate values.
            texts={norm(inp['source_lines'][i-1]) for i in anchors}
            numbers=set(re.findall(r'(?<!\d)\d+\.\d{2}(?!\d)',' '.join(inp['source_lines'][i-1] for i in near))) if field=='total' else set()
            row={'case_id':inp['case_id'],'field':field,'reference_value':t['tail'],'anchor_status':classify(spans,anchors),'nearby_status':classify(spans,near),'source_match_spans':json.dumps(spans),'anchor_lines':json.dumps(anchors),'nearby_lines':json.dumps(near),'anchor_count':len(anchors),'distinct_anchor_texts':len(texts),'multiple_anchor_proxy':len(texts)>1,'distinct_amounts_nearby':len(numbers) if field=='total' else None,'partial_boundary_match':bool(spans) and classify(spans,near)=='outside_index' and any(set(s)&set(near) for s in spans)}
            for method in ['input','simple_gate','evidence_gate','shacl_gate']:
                r=outcomes[inp['case_id'],field,method];row[method+'_exact']=r['output_exact']=='True'
            row['evidence_minus_simple']=int(row['evidence_gate_exact'])-int(row['simple_gate_exact']);rows.append(row)
    assert len(rows)==240
    summary=[]
    for field in ['ALL','company','address','date','total']:
        group=[r for r in rows if field=='ALL' or r['field']==field]
        for status in ['indexed','outside_index','not_source_matched']:
            rs=[r for r in group if r['nearby_status']==status]
            summary.append({'field':field,'stratum':status,'n':len(rs),'simple_exact':sum(r['simple_gate_exact'] for r in rs),'evidence_exact':sum(r['evidence_gate_exact'] for r in rs),'net_exact_gain':sum(r['evidence_minus_simple'] for r in rs),'partial_boundary_matches':sum(r['partial_boundary_match'] for r in rs)})
    competition=[]
    for flag in [False,True]:
        rs=[r for r in rows if r['multiple_anchor_proxy']==flag]
        competition.append({'multiple_anchor_proxy':flag,'n':len(rs),'simple_exact':sum(r['simple_gate_exact'] for r in rs),'evidence_exact':sum(r['evidence_gate_exact'] for r in rs)})
    paths=[SOURCE/p for p in ['inputs.jsonl','references.jsonl','per_field.csv']]+[Path(__file__),HERE/'test_analysis.py',ROOT/'exps/paper1_receipt_followup/protocol.py',ROOT/'content_enhancement/source_validation.py']
    result={'scope':'Post-hoc existing 60 receipts / 240 fields. Descriptive association; no independent field-level significance claims.','matching':'Case/punctuation preserving whitespace normalization; substring spans in contiguous source lines. All lines needed for at least one occurrence must be in index. No noncontiguous concatenation. Source mismatch is not an index miss.','competition_proxy':'Distinct anchor lines >1; for total also distinct decimal amounts in nearby lines. Neither is a semantic multi-value annotation.','summary':summary,'competition':competition,'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'api_calls':0}
    write_csv(HERE/'fields.csv',rows);write_csv(HERE/'summary.csv',summary);(HERE/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Paper1 证据索引定位分析','','既有 60 份收据、240 个参考字段；使用固定索引，参考值仅用于事后定位与评分。','','|字段|参考值位置|字段数|Simple 正确|Index 正确|净增加|','|---|---|---:|---:|---:|---:|']
    for r in summary:lines.append('|'+ '|'.join(str(r[k]) for k in ['field','stratum','n','simple_exact','evidence_exact','net_exact_gain'])+'|')
    lines+=['','匹配保留大小写与标点，仅压缩空白。跨行参考必须覆盖实际连续来源跨度；不把不相邻索引行拼起来制造命中。`not_source_matched` 单列，不能当作索引漏检。','', '多锚点与金额数量仅为可观察竞争代理，不是人工认定的语义候选数量。字段属于同一文档，本报告只做描述性分层，不把 240 个字段当独立统计样本。', '', '复现：`/tmp/kgbench-local-venv/bin/python exps/paper1_index_localization/analyze.py`。该分析不请求模型、不调整索引。']
    (HERE/'report_zh.md').write_text('\n'.join(lines)+'\n');print(json.dumps(summary[:3]))
if __name__=='__main__':main()
