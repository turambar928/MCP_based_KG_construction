#!/usr/bin/env python3
"""Reference-only scoring of locked predictions, paired by source document."""
from __future__ import annotations
import csv,json,sys
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_mechanism_audit.protocol import *
from exps.paper1_submission_extensions.analyze_experiments import generic_metrics
from exps.paper1_repair_benchmark.analyze_results import case_metrics


def write_csv(path,rows):
    if not rows:return
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def ci(values):
    a=np.array(values,dtype=float)
    if not len(a):return None
    rng=np.random.default_rng(42)
    boot=a[rng.integers(len(a),size=(10000,len(a)))].mean(1)
    return [float(x) for x in np.quantile(boot,[.025,.975])]


def mean(values):return float(np.mean(values)) if len(values) else None


def metrics(c,initial,output,stream):
    m=generic_metrics(initial,output,c['clean_triples'])
    m['repair']=case_metrics(c,{'method':'audit','triples':output})[0]['defect_repair_rate'] if stream=='controlled' else None
    return m


def summarize(records,keys):
    groups=defaultdict(list)
    for row in records:groups[tuple(row[k] for k in keys)].append(row)
    rows=[]
    for k,items in sorted(groups.items()):
        rec=dict(zip(keys,k));rec['n']=len(items)
        for metric in ['triple_f1','exact_match','clean_fact_preservation','overrepair_rate','initial_errors','final_errors']:
            rec[metric]=mean([i[metric] for i in items])
        rec['repair']=mean([i['repair'] for i in items if i['repair'] is not None])
        rec['error_reduction_nonexact']=mean([i['error_reduction'] for i in items if i['initial_errors']>0])
        rec['n_nonexact']=sum(i['initial_errors']>0 for i in items)
        rec['f1_ci']=ci([i['triple_f1'] for i in items])
        rows.append(rec)
    return rows


def paired(records,left,right):
    a={r['case_id']:r for r in records if r['method']==left};b={r['case_id']:r for r in records if r['method']==right}
    ids=sorted(a.keys() & b.keys());out={'left':left,'right':right,'n':len(ids)}
    for metric in ['triple_f1','repair','exact_match']:
        if not ids or a[ids[0]][metric] is None:continue
        diff=np.array([a[c][metric]-b[c][metric] for c in ids]);rng=np.random.default_rng(42)
        sim=(rng.choice([-1,1],size=(10000,len(ids)))*diff).mean(1)
        out[metric]={'difference':float(diff.mean()),'ci':ci(diff),
                     'paired_randomization_p':float((1+sum(abs(sim)>=abs(diff.mean())-1e-12))/10001)}
    return out


def main():
    cases={c['case_id']:c for c in read_jsonl(BENCH/'benchmark.jsonl') if c['split']=='test'}
    extraction={r['case_id']:r for r in read_jsonl(EXT/'natural_extraction_claude.jsonl')}
    legacy=[]
    systems={'input':extraction,'simple':{r['case_id']:r for r in read_jsonl(EXT/'natural_repairs_simple_claude.jsonl')},
             'diagnosis_gate':{r['case_id']:r for r in read_jsonl(EXT/'natural_repairs_full_claude.jsonl')}}
    for name,rows in systems.items():
        for cid,c in cases.items():
            initial=extraction[cid]['triples'];m=metrics(c,initial,rows[cid]['triples'],'natural')
            parse=extraction[cid]['status']=='ok'
            strata=['all','parsed' if parse else 'malformed']
            if parse:strata+=['parsed_dirty' if m['initial_errors']>0 else 'parsed_clean']
            for stratum in strata:legacy.append({'case_id':cid,'method':name,'stratum':stratum,**m})
    legacy_summary=summarize(legacy,['stratum','method']);write_csv(HERE/'natural_stratified.csv',legacy_summary)
    oldpaired={s:paired([r for r in legacy if r['stratum']==s],'diagnosis_gate','simple') for s in ['all','parsed','parsed_dirty','malformed']}
    replay_rows=[];stops=Counter();reason_counts=Counter();accepted=Counter()
    for row in read_jsonl(HERE/'optimizer_replay.jsonl'):
        c=cases[row['case_id']];initial=c['corrupted_triples'] if row['stream']=='controlled' else extraction[c['case_id']]['triples']
        m=metrics(c,initial,row['triples'],row['stream'])
        replay_rows.append({'case_id':c['case_id'],'stream':row['stream'],'method':row['variant'],**m})
        stops[(row['stream'],row['variant'],row['audit']['stopped_reason'])]+=1
        accepted[(row['stream'],row['variant'])]+=row['applied_count']
        for d in row['audit']['decisions']:reason_counts[(row['stream'],row['variant'],d['reason'])]+=1
    replay_summary=summarize(replay_rows,['stream','method']);write_csv(HERE/'optimizer_summary.csv',replay_summary)
    rows=read_jsonl(HERE/'run/predictions.jsonl');new=[];costs=defaultdict(list);gate_audit=[]
    for row in rows:
        c=cases[row['case_id']];stream=row['stream'];initial=c['corrupted_triples'] if stream=='controlled' else extraction[c['case_id']]['triples']
        inp=public_input(c,initial);out,rejected=gate(inp,row['triples']);costs[(stream,row['arm'])].append(row)
        for post,triples in [('raw',row['triples']),('gate',out)]:
            m=metrics(c,initial,triples,stream)
            new.append({'case_id':c['case_id'],'stream':stream,'method':row['arm']+'_'+post,**m})
        gold=Counter(key(t) for t in c['clean_triples'])
        for rej in rejected:
            gate_audit.append({'case_id':c['case_id'],'stream':stream,'arm':row['arm'],'reason':rej['reason'],
                               'reference_member':key(rej['triple']) in gold,'triple':json.dumps(rej['triple'],ensure_ascii=False)})
    new_summary=summarize(new,['stream','method']);write_csv(HERE/'matched_summary.csv',new_summary)
    write_csv(HERE/'matched_per_case.csv',new);write_csv(HERE/'matched_gate_audit.csv',gate_audit)
    costs_summary=[]
    for (stream,arm),items in sorted(costs.items()):
        costs_summary.append({'stream':stream,'arm':arm,'n':len(items),'n_ok':sum(i['status']=='ok' for i in items),
                              'calls':mean([i['calls'] for i in items]),'wall_seconds':mean([i['wall_seconds'] for i in items]),
                              'prompt_tokens':mean([i['usage'].get('prompt_tokens',0) for i in items]),
                              'completion_tokens':mean([i['usage'].get('completion_tokens',0) for i in items])})
    write_csv(HERE/'cost_summary.csv',costs_summary)
    comparisons={stream:[paired([r for r in new if r['stream']==stream],l,r) for l,r in
                          [('diagnosis_raw','base_raw'),('diagnosis_gate','base_gate'),('diagnosis_gate','diagnosis_raw'),
                           ('base_gate','base_raw'),('diagnosis_gate','shacl_context_raw'),('diagnosis_gate','shacl_context_gate')]]
                 for stream in ['controlled','natural']}
    manifest_path=HERE/'run/manifest.json'
    run_ids=json.loads(manifest_path.read_text())['case_ids'] if manifest_path.exists() else []
    expected={(s,a,c) for s in ['controlled','natural'] for a in ['base','diagnosis','shacl_context'] for c in run_ids}
    actual={(r['stream'],r['arm'],r['case_id']) for r in rows}
    complete=bool(expected) and actual==expected and len(rows)==len(expected)
    source_copy=json.loads((HERE/'source_field_results.json').read_text())
    report={'source_field_copy':source_copy,'complete':complete,'n_api_rows':len(rows),'expected_api_rows':len(expected),'natural_stratified':legacy_summary,
            'natural_paired':oldpaired,'optimizer_summary':replay_summary,'optimizer_stop_counts':{'|'.join(k):v for k,v in stops.items()},
            'optimizer_decision_reasons':{'|'.join(k):v for k,v in reason_counts.items()},
            'optimizer_accepted_actions':{'|'.join(k):v for k,v in accepted.items()},
            'matched_summary':new_summary,'paired_comparisons':comparisons,'costs':costs_summary,
            'gate_rejections':{'|'.join(map(str,k)):v for k,v in Counter((r['stream'],r['arm'],r['reason'],r['reference_member']) for r in gate_audit).items()}}
    (HERE/'results.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    lines=['# Paper 1 execution-path and mechanism audit','',f'API run complete: {complete} ({len(rows)}/{len(expected)} records).',
           '','All new calls use Gemma. References are accessed only by the scorer.','',
           '| Study | Stream/stratum | Method | n | Repair | F1 | Exact |','|---|---|---|---:|---:|---:|---:|']
    for label,items in [('Source-field copy',source_copy),('Archived natural strata',legacy_summary),('Executed optimizer',replay_summary),('Matched Gemma',new_summary)]:
        for r in items:
            repair='--' if r['repair'] is None else f"{r['repair']:.4f}"
            lines.append(f"| {label} | {r.get('stream',r.get('stratum'))} | {r['method']} | {r['n']} | {repair} | {r['triple_f1']:.4f} | {r['exact_match']:.4f} |")
    lines+=['','## Interpretation boundaries','',
            '- The deterministic source-field baseline obtains perfect recovery because the source evidence serializes the reference fields; current data cannot establish superiority over direct source reconstruction.',
            '- Optimizer replay applies real trial-state selection to frozen proposals; it is not an additional model call or a trained RL policy.',
            '- Old router features read reference relation presence; old router/LODO results are withdrawn as deployment evidence.',
            '- The SHACL-context arm implements the M+G context design in Lin et al. (2025), Section 5, adapted to document fields and JSON full-graph output. It is not an official-code reproduction.',
            '- The API budget is matched by call count and completion cap, not by input-token count. Raw and gated outputs within each arm share exactly the same response.',
            '- Natural-reference evaluation remains silver; independent human annotations are pending.']
    (HERE/'report.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines[:60]))
if __name__=='__main__':main()
