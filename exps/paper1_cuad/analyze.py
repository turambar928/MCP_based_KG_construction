"""Paired document analysis, with failures retained as empty output graphs."""
import argparse
import csv
import json
import sys
import zipfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_cuad.protocol import ARMS,FIELDS,normalize
HERE=Path(__file__).resolve().parent


def read(path):return [json.loads(l) for l in path.read_text().splitlines()]


def facts(triples,normalized=True):
    return {(t['relation'],normalize(t['tail']) if normalized else t['tail']) for t in triples}


def metrics(pred,ref,initial,raw_reference=None):
    p,g,old=facts(pred),facts(ref),facts(initial)
    tp=len(p&g);f1=2*tp/(len(p)+len(g)) if p or g else 1.
    rawp,rawg=facts(pred,False),facts(ref if raw_reference is None else raw_reference,False)
    rawf=2*len(rawp&rawg)/(len(rawp)+len(rawg)) if rawp or rawg else 1.
    old_good=old&g;lost=old_good-p
    return dict(f1=f1,raw_f1=rawf,precision=tp/len(p) if p else 0.,recall=tp/len(g) if g else 1.,
                field_accuracy=sum({v for r,v in p if r==f}=={v for r,v in g if r==f} for f in FIELDS)/len(FIELDS),
                initial_correct=len(old_good),lost_correct=len(lost),new_incorrect=len((p-g)-old),
                correct_preservation=(len(old_good)-len(lost))/len(old_good) if old_good else None)


def paired_difference(a,b,seed=20260929):
    delta=np.asarray(a)-np.asarray(b);rng=np.random.default_rng(seed)
    estimates=delta[rng.integers(0,len(delta),size=(10000,len(delta)))].mean(1)
    observed=abs(delta.mean());extreme=0
    for _ in range(10):
        flipped=(delta*rng.choice([-1,1],size=(10000,len(delta)))).mean(1)
        extreme+=int(np.count_nonzero(np.abs(flipped)>=observed-1e-12))
    return dict(difference_pp=100*float(delta.mean()),ci95_pp=(100*np.quantile(estimates,[.025,.975])).tolist(),
                p_sign_flip=(extreme+1)/100001,paired_documents=len(delta))


def analyze(split):
    public=read(HERE/(split+'_public.jsonl'));gold={r['case_id']:r['triples'] for r in read(HERE/(split+'_scorer_only.jsonl'))}
    # The materialized primary references normalize whitespace. For the
    # secondary raw metric restore the first official annotated span per field,
    # before looking at outputs; repeated whitespace-equivalent spans do not
    # create additional reference facts.
    archive=ROOT/'exps/submission_week_20260929/sources/cuad_data.zip'
    with zipfile.ZipFile(archive) as z:
        official={d['title']:d for d in json.loads(z.read('CUADv1.json'))['data']}
    rawgold={}
    for doc in public:
        qas=official[doc['title']]['paragraphs'][0]['qas']
        rawgold[doc['case_id']]=[dict(head=doc['case_id'],relation=q['id'].split('__')[-1],tail=q['answers'][0]['text'])
                               for q in qas if q['id'].split('__')[-1] in FIELDS and q['answers']]
    responses=read(HERE/(split+'_responses.jsonl'));lookup={(r['case_id'],r['arm']):r for r in responses}
    expected={(r['case_id'],a) for r in public for a in ARMS}
    assert len(lookup)==len(responses) and set(lookup)==expected,'Incomplete or duplicate collection'
    records=[];summary={}
    for arm in ARMS:
        selected=[];cost=[]
        for doc in public:
            cid=doc['case_id'];row=lookup[cid,arm];initial=lookup[cid,'initial']['triples']
            values=metrics(row['triples'],gold[cid],initial,rawgold[cid])
            record=dict(case_id=cid,arm=arm,status=row['status'],**values)
            records.append(record);selected.append(record);cost.append(row)
        summary[arm]={k:float(np.mean([r[k] for r in selected])) for k in ['f1','raw_f1','precision','recall','field_accuracy']}
        correct=sum(r['initial_correct'] for r in selected);lost=sum(r['lost_correct'] for r in selected)
        summary[arm].update(documents=len(selected),lost_initial_correct=lost,initial_correct=correct,
                            correct_preservation=1-lost/correct if correct else None,new_incorrect=sum(r['new_incorrect'] for r in selected),
                            failures=sum(r['status']!='ok' for r in selected),actual_requests=sum(r['calls'] for r in cost),
                            total_latency_seconds=sum(r['wall_seconds'] for r in cost),
                            median_latency_seconds=float(np.median([r['wall_seconds'] for r in cost])))
        for key in ['prompt_tokens','completion_tokens','total_tokens']:
            usage=[r['usage'].get(key) for r in cost if isinstance(r['usage'],dict)]
            available=[x for x in usage if isinstance(x,(int,float))]
            summary[arm][key]=sum(available) if len(available)==len(cost) else None
            summary[arm][key+'_available_requests']=len(available)
    values={a:[r['f1'] for r in records if r['arm']==a] for a in ARMS}
    result=dict(split=split,documents=len(public),summary=summary,
                primary=paired_difference(values['repair_index'],values['extract_index']),
                descriptive_index_vs_simple=paired_difference(values['repair_index'],values['repair_simple']),
                human_semantics='Not evaluated; exact span agreement only',
                cost_scope='Repair costs exclude initial creation, listed separately in initial; paired workflow cost is initial+repair. Latency includes pacing and retries; summed latency is not batch wall time.')
    (HERE/(split+'_results.json')).write_text(json.dumps(result,indent=2)+'\n')
    with (HERE/(split+'_per_document.csv')).open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    lines=['# CUAD '+split+' results','',f'Documents: {len(public)}. Exact source-span field agreement; not the official CUAD QA metric.','',
           '|Arm|F1 (%)|Correct facts lost|New incorrect facts|Failed outputs|Actual requests|','|---|---:|---:|---:|---:|---:|']
    for a,s in summary.items():lines.append(f"|{a}|{s['f1']*100:.2f}|{s['lost_initial_correct']}|{s['new_incorrect']}|{s['failures']}|{s['actual_requests']}|")
    p=result['primary'];lines+=['',f"Primary indexed repair − indexed extraction: {p['difference_pp']:.2f} pp, 95% paired CI {p['ci95_pp']}, sign-flip p={p['p_sign_flip']:.5f}.",'',result['cost_scope'],'','Human semantic review is pending.']
    (HERE/(split+'_report.md')).write_text('\n'.join(lines)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('split',choices=['dev','test']);analyze(p.parse_args().split)
