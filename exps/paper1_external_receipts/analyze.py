"""Score all frozen external outcomes against independently stored human labels."""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_mechanism_audit.protocol import read_jsonl, gate, preprocess, key
from exps.paper1_mechanism_audit.source_field_baseline import source_field_copy
from exps.paper1_mechanism_audit.analyze import ci, paired
from exps.paper1_submission_extensions.analyze_experiments import generic_metrics
from exps.paper1_external_receipts.run import input_object

HERE=Path(__file__).resolve().parent


def project(triples, reference, normalized=False):
    excluded=set(['company','date','address','total'])-set(reference['annotated_relations'])
    result=[]
    for t in triples:
        if t['relation'] in excluded:continue
        r=dict(t)
        if normalized:r['tail']=re.sub(r'\s+','',r['tail']).casefold()
        result.append(r)
    return result


def score_case(initial, output, reference):
    m=generic_metrics(project(initial,reference),project(output,reference),reference['triples'])
    normal=generic_metrics(project(initial,reference,True),project(output,reference,True),project(reference['triples'],reference,True))
    return {**m,'normalized_f1':normal['triple_f1'],'normalized_exact':normal['exact_match'],'repair':None}


def write_csv(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def main():
    inputs=read_jsonl(HERE/'inputs.jsonl');references={r['case_id']:r for r in read_jsonl(HERE/'references.jsonl')}
    extractions=read_jsonl(HERE/'extraction.jsonl');repairs=read_jsonl(HERE/'repairs.jsonl')
    ids={r['case_id'] for r in inputs}
    expected={(cid,arm) for cid in ids for arm in ['base','diagnosis','shacl_context']}
    if len(extractions)!=60 or {r['case_id'] for r in extractions}!=ids or len(repairs)!=180 or {(r['case_id'],r['arm']) for r in repairs}!=expected:
        raise RuntimeError('Wait for the complete 60+180 outcomes; keep failures in the denominator')
    initial={r['case_id']:r for r in extractions};preds={(r['case_id'],r['arm']):r for r in repairs}
    records=[];rejections=[]
    for inp in inputs:
        cid=inp['case_id'];start=initial[cid]['triples'];public=input_object(inp,start);ref=references[cid]
        systems={'input':start,'rule_only':preprocess(public),'source_field_copy':source_field_copy(public)}
        for arm in ['base','diagnosis','shacl_context']:
            row=preds[cid,arm];raw=row['triples'];out,rejected=gate(public,raw)
            systems[arm+'_raw']=raw;systems[arm+'_gate']=out
            for rejection in rejected:
                t=rejection['triple'];known=t['relation'] in ref['annotated_relations']
                rejections.append({'case_id':cid,'arm':arm,'reason':rejection['reason'],
                    'annotated_relation':known,'reference_member':key(t) in {key(g) for g in ref['triples']} if known else None,
                    'normalized_reference_member':key(project([t],ref,True)[0]) in {key(g) for g in project(ref['triples'],ref,True)} if known else None,
                    'triple':json.dumps(t,ensure_ascii=False)})
        for method,out in systems.items():
            records.append({'case_id':cid,'method':method,**score_case(start,out,ref)})
    summaries=[]
    for method in sorted({r['method'] for r in records}):
        rows=[r for r in records if r['method']==method];dirty=[r for r in rows if r['initial_errors']>0]
        summaries.append({'method':method,'n':len(rows),**{k:float(np.mean([r[k] for r in rows])) for k in ['triple_f1','exact_match','normalized_f1','normalized_exact','clean_fact_preservation','overrepair_rate']},
            'imperfect_inputs':len(dirty),'error_reduction_on_imperfect':float(np.mean([r['error_reduction'] for r in dirty])) if dirty else None,
            'f1_ci':ci([r['triple_f1'] for r in rows]),'normalized_f1_ci':ci([r['normalized_f1'] for r in rows])})
    comparisons=[paired(records,a,b) for a,b in [('base_gate','input'),('diagnosis_gate','input'),('diagnosis_gate','base_gate'),('diagnosis_gate','shacl_context_gate'),('base_gate','base_raw'),('diagnosis_gate','diagnosis_raw'),('shacl_context_gate','shacl_context_raw')]]
    cost=[]
    for arm in ['extract','base','diagnosis','shacl_context']:
        rows=[r for r in extractions+repairs if r['arm']==arm]
        cost.append({'arm':arm,'n':len(rows),'n_ok':sum(r['status']=='ok' for r in rows),'calls':sum(r['calls'] for r in rows),
            'mean_calls':float(np.mean([r['calls'] for r in rows])),
            'mean_wall_seconds':float(np.mean([r['wall_seconds'] for r in rows])),
            'mean_input_tokens':float(np.mean([r['usage'].get('prompt_tokens',0) for r in rows])),
            'mean_output_tokens':float(np.mean([r['usage'].get('completion_tokens',0) for r in rows]))})
    support=Counter()
    for inp in inputs:
        for t in references[inp['case_id']]['triples']:
            support['annotated_fields']+=1
            support['literal_source_fields']+=t['tail'] in inp['source_evidence']
    report={'complete':True,'n_documents':60,'reference_type':'upstream human KIE annotations; separate from transcripts',
        'source_support':dict(support),'summary':summaries,'paired':comparisons,'cost':cost,
        'rejected_candidates':len(rejections),'rejected_exact_reference_candidates':sum(r['reference_member'] is True for r in rejections),
        'rejected_normalized_reference_candidates':sum(r['normalized_reference_member'] is True for r in rejections),
        'rejections_in_unannotated_fields':sum(not r['annotated_relation'] for r in rejections),
        'status_counts':dict(Counter(r['status'] for r in extractions+repairs))}
    (HERE/'results.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    write_csv(HERE/'per_case.csv',records);write_csv(HERE/'summary.csv',summaries);write_csv(HERE/'cost.csv',cost)
    if rejections:write_csv(HERE/'gate_rejections.csv',rejections)
    lines=['# Independent receipt evaluation','','60 fixed SROIE documents; 239 annotated fields; missing address label excluded only in scoring.','', '|Method|Strict F1|Exact graph|Normalized F1|Preservation|','|---|---:|---:|---:|---:|']
    for r in summaries:lines.append(f"|{r['method']}|{r['triple_f1']:.4f}|{r['exact_match']:.4f}|{r['normalized_f1']:.4f}|{r['clean_fact_preservation']:.4f}|")
    lines+=['',f"Literal source coverage: {dict(support)}.",f"Rejected candidates: {len(rejections)}; exact reference: {report['rejected_exact_reference_candidates']}; normalized reference: {report['rejected_normalized_reference_candidates']}.", '', 'Paired document-bootstrap intervals, randomization comparisons and measured costs are in results.json.']
    (HERE/'report.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':main()
