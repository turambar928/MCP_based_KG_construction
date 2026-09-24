"""Locked scoring: document-paired factorial effects and index contrasts."""
import csv,json,sys
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_ablation_completion.protocol import *
from exps.paper1_mechanism_audit.protocol import read_jsonl
from exps.paper1_submission_extensions.analyze_experiments import generic_metrics
from exps.paper1_repair_benchmark.analyze_results import case_metrics
from exps.paper1_external_receipts.analyze import score_case
HERE=Path(__file__).resolve().parent

def write_csv(path,rows):
    if not rows:return
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)

def paired_stats(values):
    a=np.asarray(values,float);rng=np.random.default_rng(42)
    boot=a[rng.integers(len(a),size=(10000,len(a)))].mean(1)
    sim=(rng.choice([-1,1],size=(10000,len(a)))*a).mean(1)
    return {'n':len(a),'difference':float(a.mean()),'ci_low':float(np.quantile(boot,.025)),
      'ci_high':float(np.quantile(boot,.975)),'p':float((1+sum(abs(sim)>=abs(a.mean())-1e-12))/10001)}

def holm(rows):
    ordered=sorted(rows,key=lambda x:x['p']);last=0
    for i,r in enumerate(ordered):last=max(last,min(1.,r['p']*(len(rows)-i)));r['p_holm']=last

def load_data():
    inputs={(r['cohort'],r['case_id']):r for r in read_jsonl(HERE/'inputs.jsonl')}
    cases={r['case_id']:r for r in read_jsonl(ROOT/'exps/paper1_repair_benchmark/benchmark.jsonl')}
    refs={r['case_id']:r for r in read_jsonl(ROOT/'exps/paper1_receipt_followup/test/references.jsonl')}
    return inputs,cases,refs

def inp_object(r):
    return PublicInput(r['case_id'],r['domain'],r['source_evidence'],r['required_document_node'],tuple(r['allowed_relations']),tuple(r['input_triples']))

def score(r,out,cases,refs):
    if r['cohort']=='receipt':return score_case(r['input_triples'],out,refs[r['case_id']])
    c=cases[r['case_id']];m=generic_metrics(r['input_triples'],out,c['clean_triples'])
    m['repair']=case_metrics(c,{'method':'ablation','triples':out})[0]['defect_repair_rate'] if r['cohort']=='controlled' else None
    m['normalized_f1']=None;m['normalized_exact']=None
    return m

def summarize(rows,keys):
    groups=defaultdict(list)
    for r in rows:groups[tuple(r[k] for k in keys)].append(r)
    result=[]
    for k,rs in sorted(groups.items()):
        row=dict(zip(keys,k));row['n']=len(rs)
        for metric in ['triple_f1','exact_match','clean_fact_preservation','overrepair_rate','repair','normalized_f1']:
            vals=[r[metric] for r in rs if r.get(metric) is not None];row[metric]=float(np.mean(vals)) if vals else None
        result.append(row)
    return result

def main():
    from exps.paper1_ablation_completion.run import verify
    manifest=verify();inputs,cases,refs=load_data();preds=read_jsonl(HERE/'predictions.jsonl');tasks=read_jsonl(HERE/'prompts.jsonl')
    ident=lambda r:(r['cohort'],r['case_id'],r['arm'])
    assert len(preds)==manifest['expected_requests'] and len({ident(r) for r in preds})==len(preds)
    assert {ident(r) for r in preds}=={ident(r) for r in tasks}
    per=[];gate_rows=[];rejects=[];costs=defaultdict(list)
    variants={'full':(),**{'no_'+c:(c,) for c in CHECKS},'no_duplicate_cardinality':('duplicate','cardinality'),'raw':CHECKS}
    for row in preds:
        r=inputs[row['cohort'],row['case_id']];inp=inp_object(r);costs[row['cohort'],row['arm']].append(row)
        ref=refs[r['case_id']]['triples'] if r['cohort']=='receipt' else cases[r['case_id']]['clean_triples'];gold=Counter(map(key,ref))
        for variant,disabled in variants.items():
            out,rejected=filter_candidates(inp,row['triples'],disabled,r['cohort']=='receipt')
            m=score(r,out,cases,refs);base={'cohort':r['cohort'],'case_id':r['case_id'],'arm':row['arm']}
            gate_rows.append({**base,'gate_variant':variant,**m})
            if variant in ['full','raw']:per.append({**base,'g':int(variant=='full'),**m})
            if variant=='full':
                for rej in rejected:rejects.append({**base,'reason':rej['reason'],'reference_member':key(rej['triple']) in gold,'triple':json.dumps(rej['triple'],ensure_ascii=False)})
    effects=[]
    for cohort in ['controlled','natural']:
        index={(r['case_id'],int(r['arm'][1]),int(r['arm'][3]),r['g']):r['triple_f1'] for r in per if r['cohort']==cohort}
        ids=sorted({k[0] for k in index})
        for term in ['P','D','G','PD','PG','DG','PDG']:
            values=[]
            for cid in ids:
                total=0.
                for p in [0,1]:
                    for d in [0,1]:
                        for g in [0,1]:
                            levels=dict(P=p,D=d,G=g);sign=np.prod([2*levels[t]-1 for t in term])
                            total+=sign*index[cid,p,d,g]/(2**(3-len(term)))
                values.append(total)
            effects.append({'cohort':cohort,'effect':term,**paired_stats(values)})
    holm([r for r in effects if len(r['effect'])==1])
    for r in effects:r.setdefault('p_holm',None)
    contrasts=[];receipt={(r['case_id'],r['arm']):r['triple_f1'] for r in per if r['cohort']=='receipt' and r['g']==1}
    ids=sorted({k[0] for k in receipt})
    for left,right in manifest['receipt_contrasts']:
        contrasts.append({'left':left,'right':right,**paired_stats([receipt[c,left]-receipt[c,right] for c in ids])})
    holm(contrasts)
    cost=[]
    for (cohort,arm),rs in sorted(costs.items()):
        cost.append({'cohort':cohort,'arm':arm,'n':len(rs),'ok':sum(r['status']=='ok' for r in rs),'requests':sum(r['calls'] for r in rs),
          'mean_wall_seconds':float(np.mean([r['wall_seconds'] for r in rs])),
          'mean_input_tokens':float(np.mean([r['usage'].get('prompt_tokens',0) for r in rs])),
          'mean_output_tokens':float(np.mean([r['usage'].get('completion_tokens',0) for r in rs]))})
    prompt_index={ident(r):json.loads(r['user']) for r in tasks};placebo=[]
    for cid in ids:
        full=prompt_index['receipt',cid,'full']['field_evidence_index'];random=prompt_index['receipt',cid,'random']['field_evidence_index']
        for field,f in full.items():
            x=random[field];placebo.append({'case_id':cid,'field':field,'anchors':len(f['anchor_lines']),'nearby':len(f['nearby_lines']),
              'random_anchors':len(x['anchor_lines']),'random_nearby':len(x['nearby_lines']),
              'overlap':len(set(f['anchor_lines'])&set(x['anchor_lines'])),
              'true_anchor_chars':sum(len(a['text']) for a in f['anchors']),'random_anchor_chars':sum(len(a['text']) for a in x['anchors'])})
    summary=summarize(per,['cohort','arm','g']);gate_summary=summarize(gate_rows,['cohort','arm','gate_variant'])
    report={'complete':True,'n_responses':len(preds),'requests':sum(r['calls'] for r in preds),'status':dict(Counter(r['status'] for r in preds)),
      'summary':summary,'factorial_effects':effects,'receipt_contrasts':contrasts,'cost':cost,'gate_summary':gate_summary,
      'rejections':{'|'.join(map(str,k)):v for k,v in Counter((r['cohort'],r['reason'],r['reference_member']) for r in rejects).items()}}
    for name,rows in [('per_case',per),('summary',summary),('factorial_effects',effects),('receipt_contrasts',contrasts),('cost',cost),('gate_per_case',gate_rows),('gate_summary',gate_summary),('gate_rejections',rejects),('placebo_diagnostics',placebo)]:write_csv(HERE/(name+'.csv'),rows)
    (HERE/'results.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:report[k] for k in ['complete','n_responses','requests','status','factorial_effects','receipt_contrasts']},indent=2))
if __name__=='__main__':main()
