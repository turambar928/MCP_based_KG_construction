#!/usr/bin/env python3
"""Freeze a blind audit of actual system edits, separately from input errors."""
import csv,json,random,sys,hashlib
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_mechanism_audit.protocol import *
from exps.paper1_mechanism_audit.analyze import write_csv


def main():
    cases={c['case_id']:c for c in read_jsonl(BENCH/'benchmark.jsonl') if c['split']=='test'}
    extraction={r['case_id']:r for r in read_jsonl(EXT/'natural_extraction_claude.jsonl')}
    methods={'archived_simple':read_jsonl(EXT/'natural_repairs_simple_claude.jsonl'),
             'archived_diagnosis_gate':read_jsonl(EXT/'natural_repairs_full_claude.jsonl')}
    new=read_jsonl(HERE/'run/predictions.jsonl')
    if len(new)!=360:raise RuntimeError('Freeze only after the complete locked run, including failures')
    for arm in ['base','diagnosis','shacl_context']:
        methods['gemma_'+arm+'_gate']=[{**r,'triples':gate(public_input(cases[r['case_id']],extraction[r['case_id']]['triples']),r['triples'])[0]}
                                       for r in new if r['stream']=='natural' and r['arm']==arm]
    population=[]
    for method,rows in methods.items():
        for row in sorted(rows,key=lambda x:x['case_id']):
            cid=row['case_id'];initial=extraction[cid]['triples'];inp=Counter(key(t) for t in initial);out=Counter(key(t) for t in row['triples'])
            for operation,diff in [('add',out-inp),('remove',inp-out)]:
                for triple,n in sorted(diff.items()):
                    for occurrence in range(n):
                        population.append({'method':method,'case_id':cid,'source':cases[cid]['evidence_text'],
                                           'input_graph':json.dumps(initial,ensure_ascii=False),
                                           'output_graph':json.dumps(row['triples'],ensure_ascii=False),
                                           'operation':operation,'triple':json.dumps(dict(zip(['head','relation','tail'],triple)),ensure_ascii=False),
                                           'occurrence':occurrence})
    sampled=random.Random(42).sample(population,min(200,len(population)))
    folder=HERE/'human_review';folder.mkdir(exist_ok=True)
    if (folder/'manifest.json').exists():raise RuntimeError('Already frozen; do not overwrite labels')
    a=[];b=[];mapping=[];merge=[]
    for i,row in enumerate(sampled):
        uid=f'edit-{i+1:03d}'
        visible={'item_id':uid,**{k:row[k] for k in ['source','input_graph','output_graph','operation','triple']}}
        blank={'is_error':'','repair_acceptable':'','notes':''}
        a.append({**visible,**blank});b.append({**visible,**blank})
        merge.append({'item_id':uid,**{f'{who}_{field}':'' for who in ['annotator_a','annotator_b','adjudicated'] for field in ['is_error','repair_acceptable']},'notes':''})
        mapping.append({'item_id':uid,**{k:row[k] for k in ['method','case_id','operation','triple','occurrence']}})
    write_csv(folder/'annotator_a.csv',a);write_csv(folder/'annotator_b.csv',b)
    write_csv(folder/'coordinator_mapping.csv',mapping);write_csv(folder/'adjudication.csv',merge)
    manifest={'seed':42,'population_size':len(population),'sample_size':len(a),'sampling':'simple random sample of edit occurrences across the five specified configurations; not prevalence-balanced',
              'human_status':'pending','sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*.csv')}}
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Frozen',len(a),'system edits from',len(population),'occurrences')
if __name__=='__main__':main()
