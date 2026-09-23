"""Score development/test independently with the same fixed metrics and paired tests."""
import argparse,csv,json,sys,hashlib,re
from decimal import Decimal
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_mechanism_audit.protocol import read_jsonl,key,gate
from exps.paper1_mechanism_audit.analyze import ci,paired
from exps.paper1_external_receipts.run import input_object
from exps.paper1_external_receipts.analyze import score_case,project
from exps.paper1_receipt_followup.protocol import filter_response
from exps.paper1_receipt_followup.error_analysis import classify
HERE=Path(__file__).resolve().parent


def write_csv(path,rows):
    if not rows:return
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def amount_value(value):
    value=re.sub(r'^(?:RM|MYR|\$)\s*','',value.strip(),flags=re.I).replace(',','')
    return Decimal(value) if re.fullmatch(r'[-+]?\d+(?:\.\d+)?',value) else None


def analyze(split):
    if split=='test':
        from exps.paper1_receipt_followup.scoring_lock import verify
        verify()
    folder=HERE/split;n=20 if split=='dev' else 60
    inputs={r['case_id']:r for r in read_jsonl(folder/'inputs.jsonl')}
    refs={r['case_id']:r for r in read_jsonl(folder/'references.jsonl')}
    init_rows=read_jsonl(folder/'extraction.jsonl');repair_rows=read_jsonl(folder/'repairs.jsonl')
    ids=set(inputs)
    assert len(ids)==n and set(refs)==ids
    assert len(init_rows)==n and {r['case_id'] for r in init_rows}==ids
    assert len(repair_rows)==3*n and {(r['case_id'],r['arm']) for r in repair_rows}=={(cid,a) for cid in ids for a in ['simple','evidence','shacl']}
    initial={r['case_id']:r for r in init_rows};preds={(r['case_id'],r['arm']):r for r in repair_rows}
    per_case=[];per_field=[];rejects=[];count_changes=Counter();outputs=[]
    for cid,inp in inputs.items():
        start=initial[cid]['triples'];ref=refs[cid]
        methods={'input':start,'input_gate':filter_response(inp,start)[0]}
        for arm in ['simple','evidence','shacl']:
            raw=preds[cid,arm]['triples'];filtered,rejected=filter_response(inp,raw)
            legacy=gate(input_object(inp,start),raw)[0]
            methods.update({arm+'_raw':raw,arm+'_gate':filtered,arm+'_strict_gate':legacy})
            count_changes[arm]+=Counter(map(key,raw))!=Counter(map(key,start))
            for r in rejected:
                rejects.append({'case_id':cid,'arm':arm,'reason':r['reason'],'reference_member':key(r['triple']) in set(map(key,ref['triples'])),
                                'triple':json.dumps(r['triple'],ensure_ascii=False)})
        for method,out in methods.items():
            m=score_case(start,out,ref)
            per_case.append({'case_id':cid,'method':method,**m})
            outputs.append({'case_id':cid,'method':method,'triples':out})
            current={t['relation']:t['tail'] for t in out if t['head']==inp['required_document_node']}
            before={t['relation']:t['tail'] for t in start if t['head']==inp['required_document_node']}
            for t in ref['triples']:
                r=t['relation'];old=before.get(r,'');new=current.get(r,'')
                per_field.append({'case_id':cid,'method':method,'relation':r,'input_exact':old==t['tail'],'output_exact':new==t['tail'],
                    'initial_category':classify(inp['source_evidence'],old,t['tail'],r),
                    'output_category':classify(inp['source_evidence'],new,t['tail'],r),'input_value':old,'output_value':new,'reference_value':t['tail'],
                    'amount_value_match':(amount_value(new) is not None and amount_value(new)==amount_value(t['tail'])) if r=='total' else None})
    summaries=[]
    for method in sorted({r['method'] for r in per_case}):
        rows=[r for r in per_case if r['method']==method];dirty=[r for r in rows if r['initial_errors']>0]
        summaries.append({'method':method,'n':n,**{k:float(np.mean([r[k] for r in rows])) for k in ['triple_f1','exact_match','normalized_f1','normalized_exact','clean_fact_preservation','overrepair_rate']},
            'imperfect_inputs':len(dirty),'mean_error_reduction_on_imperfect':float(np.mean([r['error_reduction'] for r in dirty])) if dirty else None,
            'f1_ci':ci([r['triple_f1'] for r in rows]),'normalized_f1_ci':ci([r['normalized_f1'] for r in rows])})
    comparisons=[paired(per_case,a,b) for a,b in [('evidence_gate','simple_gate'),('simple_gate','input'),('evidence_gate','input'),('evidence_gate','shacl_gate'),
                 ('simple_gate','simple_raw'),('evidence_gate','evidence_raw'),('shacl_gate','shacl_raw')]]
    cost=[]
    for arm in ['extract','simple','evidence','shacl']:
        rows=[r for r in init_rows+repair_rows if r['arm']==arm]
        cost.append({'arm':arm,'n':n,'ok':sum(r['status']=='ok' for r in rows),'requests':sum(r['calls'] for r in rows),
                     'mean_wall_seconds':float(np.mean([r['wall_seconds'] for r in rows])),
                     'mean_input_tokens':float(np.mean([r['usage'].get('prompt_tokens',0) for r in rows])),
                     'mean_output_tokens':float(np.mean([r['usage'].get('completion_tokens',0) for r in rows]))})
    transitions=[]
    for method in ['simple_gate','evidence_gate','shacl_gate']:
        grouped=defaultdict(list)
        for r in per_field:
            if r['method']==method:grouped[r['initial_category']].append(r)
        for category,rows in sorted(grouped.items()):
            transitions.append({'method':method,'initial_category':category,'n':len(rows),
                                'output_exact':sum(r['output_exact'] for r in rows)})
    amounts={method:{'n':len(rs),'correct':sum(r['amount_value_match'] for r in rs)} for method in ['input','simple_gate','evidence_gate','shacl_gate'] for rs in [[r for r in per_field if r['method']==method and r['relation']=='total']]}
    result={'amount_value_accuracy':amounts,'split':split,'complete':True,'n_documents':n,'annotated_fields':sum(len(x['triples']) for x in refs.values()),
        'summary':summaries,'paired':comparisons,'primary_comparison':comparisons[0],
        'cost':cost,'changed_graphs':dict(count_changes),'rejected_candidate_occurrences':len(rejects),
        'reference_candidates_rejected':sum(r['reference_member'] for r in rejects),'field_transitions':transitions}
    (folder/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    (folder/'scored_outputs.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in outputs))
    write_csv(folder/'per_case.csv',per_case);write_csv(folder/'per_field.csv',per_field);write_csv(folder/'summary.csv',summaries)
    write_csv(folder/'cost.csv',cost);write_csv(folder/'field_transitions.csv',transitions);write_csv(folder/'rejections.csv',rejects)
    lines=[f'# Receipt follow-up: {split}','',f"{n} documents, {result['annotated_fields']} annotated fields.",'',
           '|Method|F1|Exact graph|Normalized F1|Preservation|','|---|---:|---:|---:|---:|']
    for r in summaries:lines.append(f"|{r['method']}|{r['triple_f1']:.4f}|{r['exact_match']:.4f}|{r['normalized_f1']:.4f}|{r['clean_fact_preservation']:.4f}|")
    lines+=['','Primary comparison: '+json.dumps(comparisons[0]),'','Graph changes: '+json.dumps(dict(count_changes))]
    (folder/'report.md').write_text('\n'.join(lines)+'\n');print('\n'.join(lines))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('split',choices=['dev','test']);analyze(p.parse_args().split)
