#!/usr/bin/env python3
"""No-API checks: gold-free routing replay and input-diagnostic batch timings."""
import sys,json,time,statistics,tracemalloc
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_mechanism_audit.protocol import *
from exps.paper1_mechanism_audit.analyze import write_csv
from exps.paper1_submission_extensions.analyze_experiments import generic_metrics


def needs_repair(inp):
    d=diagnosis(inp,inp.triples);counts=Counter(t['relation'] for t in inp.triples)
    return bool(d['duplicate_rows'] or d['invalid_relation_indices'] or d['wrong_head_indices'] or
                d['unsupported_indices'] or any(n>1 for n in counts.values()))


def route_replay():
    cases=[c for c in read_jsonl(BENCH/'benchmark.jsonl') if c['split']=='test']
    extraction={r['case_id']:r for r in read_jsonl(EXT/'natural_extraction_claude.jsonl')}
    dirtyrepair={r['case_id']:r for r in read_jsonl(EXT/'natural_repairs_full_claude.jsonl')}
    cleanrepair={r['case_id']:r for r in read_jsonl(EXT/'predictions_full_clean_claude.jsonl')}
    records=[]
    for c in cases:
        for kind in ['clean','extracted']:
            initial=c['clean_triples'] if kind=='clean' else extraction[c['case_id']]['triples']
            inp=public_input(c,initial);d=needs_repair(inp)
            pred=(cleanrepair if kind=='clean' else dirtyrepair)[c['case_id']]
            for name,route in [('always',True),('visible_violations',d),('never',False)]:
                out=pred['triples'] if route else initial;m=generic_metrics(initial,out,c['clean_triples'])
                records.append({'case_id':c['case_id'],'input_kind':kind,'policy':name,'routed':int(route),
                                'dirty':int(m['initial_errors']>0),'triple_f1':m['triple_f1'],'exact':m['exact_match'],
                                'cached_calls':pred['calls'] if route else 0})
    summary=[]
    for policy in ['always','visible_violations','never']:
        rows=[r for r in records if r['policy']==policy]
        tp=sum(r['routed'] and r['dirty'] for r in rows);fp=sum(r['routed'] and not r['dirty'] for r in rows)
        fn=sum(not r['routed'] and r['dirty'] for r in rows)
        summary.append({'policy':policy,'n':len(rows),'route_f1':2*tp/max(1,2*tp+fp+fn),'false_negative_rate':fn/max(1,tp+fn),
                        'triple_f1':statistics.mean(r['triple_f1'] for r in rows),'exact':statistics.mean(r['exact'] for r in rows),
                        'cached_calls_per_doc':statistics.mean(r['cached_calls'] for r in rows)})
    write_csv(HERE/'gold_free_router_replay.csv',summary);write_csv(HERE/'gold_free_router_per_case.csv',records)
    return summary


def measure(fn,repeats):
    out=[]
    for _ in range(repeats):
        t=time.perf_counter();fn();out.append((time.perf_counter()-t)*1000)
    return statistics.median(out)


def scaling():
    pool=[public_input(c,c['corrupted_triples']) for c in read_jsonl(BENCH/'benchmark.jsonl')]
    rows=[]
    for target in [1000,5000,10000,50000]:
        tracemalloc.start();batch=[];edges=0;i=0
        while edges<target:
            src=pool[i%len(pool)];h=f'batch{i}:'+src.required_document_node
            ts=tuple({**t,'head':h if t['head']==src.required_document_node else t['head']} for t in src.triples[:target-edges])
            batch.append(PublicInput(str(i),src.domain,src.source_evidence,h,src.allowed_relations,ts))
            edges+=len(ts);i+=1
        _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        def full():return [diagnosis(p,p.triples) for p in batch]
        full();fulltime=measure(full,7)
        p=batch[len(batch)//2];changed=p.triples+(p.triples[0],)
        local=measure(lambda:diagnosis(p,changed),200)
        rows.append({'triples':target,'documents':len(batch),'full_diagnostic_ms':fulltime,'one_doc_update_ms':local,
                     'new_graph_alloc_peak_mb':peak/1024**2})
    write_csv(HERE/'diagnostic_scaling.csv',rows)
    return rows

if __name__=='__main__':
    result={'router_replay':route_replay(),'diagnostic_scaling':scaling(),
            'memory_scope':'new Python allocations for document batches; source text/schema objects shared, not process RSS',
            'router_scope':'cached outcome replay, not online latency'}
    (HERE/'additional_checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
