#!/usr/bin/env python3
"""Schema-aware source-field copy baseline for the serialized-field benchmark.

Uses source text, declared head and allowed predicates only. No reference values,
reference relation-presence set, defect labels or model call are accessible.
"""
import re,sys,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_mechanism_audit.protocol import *
from exps.paper1_mechanism_audit.analyze import metrics,summarize,write_csv


def source_field_copy(inp):
    names='|'.join(re.escape(r) for r in sorted(inp.allowed_relations,key=lambda r:(-len(r),r)))
    pattern=re.compile(r'(?:^|。)('+names+r')：')
    matches=list(pattern.finditer(inp.source_evidence));result=[];seen=set()
    for i,m in enumerate(matches):
        relation=m.group(1);end=matches[i+1].start() if i+1<len(matches) else len(inp.source_evidence)
        value=inp.source_evidence[m.end():end]
        if value and relation not in seen:
            result.append({'head':inp.required_document_node,'relation':relation,'tail':value});seen.add(relation)
    return result


def main():
    cases=[c for c in read_jsonl(BENCH/'benchmark.jsonl') if c['split']=='test']
    extract={r['case_id']:r for r in read_jsonl(EXT/'natural_extraction_claude.jsonl')}
    records=[];preds=[]
    for c in cases:
        for stream in ['controlled','natural']:
            initial=c['corrupted_triples'] if stream=='controlled' else extract[c['case_id']]['triples']
            inp=public_input(c,initial);start=time.perf_counter();out=source_field_copy(inp);elapsed=time.perf_counter()-start
            preds.append({'case_id':c['case_id'],'stream':stream,'triples':out,'calls':0,'latency_sec':elapsed,'input_sha256':digest(inp.payload())})
            records.append({'case_id':c['case_id'],'stream':stream,'method':'source_field_copy',**metrics(c,initial,out,stream)})
    with (HERE/'source_field_predictions.jsonl').open('w') as f:
        for row in preds:f.write(json.dumps(row,ensure_ascii=False)+'\n')
    summary=summarize(records,['stream','method']);write_csv(HERE/'source_field_summary.csv',summary)
    (HERE/'source_field_results.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
