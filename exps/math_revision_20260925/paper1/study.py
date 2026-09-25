"""Public-profile retraining and fixed archive replay; no API requests."""
import json, sys, hashlib, gzip
from pathlib import Path
from collections import Counter
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from content_enhancement.constraint_optimizer_v2 import MultiScaleConstraintOptimizer, TaskContext, FEATURES, FEATURE_VERSION, RouterOutput
from exps.decision_network.build_from_repair_benchmark import scale_targets
from exps.paper1_mechanism_audit.protocol import public_input, preprocess, read_jsonl, diagnosis as legacy_diagnosis
from exps.paper1_mechanism_audit.replay_optimizer import recommendations
from exps.paper1_repair_benchmark.run_benchmark import parse_triples
from exps.paper1_mechanism_audit.analyze import metrics
from exps.paper1_ablation_completion.analyze import summarize,write_csv,paired_stats
HERE=Path(__file__).resolve().parent
BENCH=ROOT/'exps/paper1_repair_benchmark'
EXT=ROOT/'exps/paper1_submission_extensions'

def diagnosis(inp, triples):
    result=legacy_diagnosis(inp, triples)
    result['unsupported_indices']=[i for i,t in enumerate(triples) if not t['tail'].strip() or t['tail'] not in inp.source_evidence]
    return result

def context(inp):
    return TaskContext(document_node=inp.required_document_node,allowed_relations=tuple(inp.allowed_relations))

def build():
    rows=[];public=[]
    for c in read_jsonl(BENCH/'benchmark.jsonl'):
        for variant, triples, target in [('clean',c['clean_triples'],0),('dirty',c['corrupted_triples'],1)]:
            inp=public_input(c,triples)
            opt=MultiScaleConstraintOptimizer(task_context=context(inp))
            profile=opt.assess([{'name':inp.required_document_node}],triples,inp.source_evidence)
            label,_=scale_targets(c['defects']) if target else ('none',{})
            rows.append({'uid':c['case_id'],'domain':c['domain'],'split':c['split'],'variant':variant,
                'y_repair':target,'scale_label':label,**dict(zip(FEATURES,profile.fphi_vector()))})
            public.append({'case_id':c['case_id'],'variant':variant,**inp.payload()})
    dest=HERE/'router';dest.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(dest/'dataset.csv',index=False)
    with gzip.open(HERE/'public_inputs.jsonl.gz','wt') as f:
        for r in public:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    (HERE/'input_contract.json').write_text(json.dumps({'feature_version':FEATURE_VERSION,'features':FEATURES,
        'metadata_migration':'The required document identifier formerly stored in clean_triples[0].head is materialized as public task metadata, as in the prior protocol. No reference relations/values enter feature calculation.',
        'scope':'Clean and corrupted triples are graph inputs in their respective rows; defect labels only supervise targets.',
        'prior_variants':['absolute','relative_to_uniform'],'coefficient_search':False,
        'raw_inputs_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [BENCH/'benchmark.jsonl',BENCH/'predictions_ours.jsonl',EXT/'natural_repairs_full_claude.jsonl']},
        'api_calls':0},indent=2)+'\n')

def evaluate_router():
    df=pd.read_csv(HERE/'router/dataset.csv');opt=MultiScaleConstraintOptimizer();assert opt.router.available
    p=opt.router.params;s=opt.router.scaler
    from exps.decision_network.train_fphi import forward,sigmoid,softmax
    x=(df[list(FEATURES)].to_numpy()-np.asarray(s['mu']))/(np.asarray(s['sd'])+1e-9)
    lr,ls,_=forward(p,x);pr=sigmoid(lr);ps=softmax(ls);df['p_repair']=pr;df['predicted_scale']=ps.argmax(1)
    result=[]
    for split in ['train','validation','test']:
        d=df[df.split==split];y=d.y_repair.to_numpy();prob=d.p_repair.to_numpy();pred=prob>=.5
        tp=int(((y==1)&pred).sum());fn=int(((y==1)&~pred).sum());fp=int(((y==0)&pred).sum());tn=int(((y==0)&~pred).sum())
        dirty=d[d.y_repair==1];scope=dirty.scale_label.map({'entity':0,'graph':1,'context':2})
        ece=0.
        for lo in np.arange(0,1,.1):
            mask=(prob>=lo)&(prob<(lo+.1) if lo<.9 else prob<=1.)
            if mask.any():ece+=mask.mean()*abs(prob[mask].mean()-y[mask].mean())
        result.append({'split':split,'n':len(d),'tp':tp,'fn':fn,'fp':fp,'tn':tn,'accuracy':(tp+tn)/len(d),
            'miss_rate':fn/max(1,tp+fn),'brier':float(np.mean((prob-y)**2)),'ece10':float(ece),
            'scale_accuracy_dirty':float((scope.to_numpy()==dirty.predicted_scale.to_numpy()).mean()),
            'runtime_threshold':.05,'runtime_miss_rate':float(((prob<.05)&(y==1)).sum()/max(1,(y==1).sum()))})
    df.to_csv(HERE/'router/predictions.csv',index=False)
    (HERE/'router/metrics.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

class ReplayOptimizer(MultiScaleConstraintOptimizer):
    def __init__(self,ctx,variant):
        super().__init__(task_context=ctx,relative_prior=variant.endswith('relative'))
        self.variant=variant
        self.trials=[];self._depth=0
    def _apply_candidate(self,triples,candidate):
        before=[dict(t) for t in triples];outer=self._depth==0;self._depth+=1
        try: after=super()._apply_candidate(triples,candidate)
        finally:self._depth-=1
        if outer:self.trials.append({'before_triples':before,'after_triples':after})
        return after
    def _check_constraints(self,before,after,candidate):
        self.trials[-1].update({'before_profile':asdict(before),'after_profile':asdict(after)})
        return super()._check_constraints(before,after,candidate)
    def route(self,profile):
        if self.variant.startswith('uniform'):return RouterOutput(1.,{s:1/3 for s in ['entity','graph','context']},'always_uniform')
        return super().route(profile)

def replay():
    cases=[c for c in read_jsonl(BENCH/'benchmark.jsonl') if c['split']=='test']
    extraction={r['case_id']:r for r in read_jsonl(EXT/'natural_extraction_claude.jsonl')}
    per=[];diag_changes=Counter()
    with gzip.open(HERE/'optimizer_traces.jsonl.gz','wt') as f:
        for cohort,path in [('controlled',BENCH/'predictions_ours.jsonl'),('natural',EXT/'natural_repairs_full_claude.jsonl')]:
            proposals={r['case_id']:r for r in read_jsonl(path)}
            for c in cases:
                inp=public_input(c,c['corrupted_triples'] if cohort=='controlled' else extraction[c['case_id']]['triples'])
                initial=preprocess(inp);proposed,status=parse_triples(proposals[c['case_id']]['raw_responses'][-1])
                diag_changes[cohort]+=diagnosis(inp,initial)!=legacy_diagnosis(inp,initial)
                for variant in ['uniform_absolute','uniform_relative','learned_absolute','learned_relative']:
                    opt=ReplayOptimizer(context(inp),variant)
                    final,applied,audit=opt.optimize_and_apply([{'name':inp.required_document_node}],initial,recommendations(initial,proposed),inp.source_evidence)
                    assert len(opt.trials)==len(audit['decisions'])
                    for d,t in zip(audit['decisions'],opt.trials):d.update(t)
                    per.append({'cohort':cohort,'variant':variant,'case_id':c['case_id'],**metrics(c,list(inp.triples),final,cohort),
                        'applied':len(applied),'trials':len(audit['decisions'])})
                    f.write(json.dumps({'cohort':cohort,'variant':variant,'case_id':c['case_id'],'triples':final,'audit':audit},ensure_ascii=False)+'\n')
            print(cohort,'replayed',flush=True)
    summary=summarize(per,['cohort','variant'])
    for s in summary:
        rs=[r for r in per if r['cohort']==s['cohort'] and r['variant']==s['variant']]
        s['accepted_edits']=sum(r['applied'] for r in rs);s['trials']=sum(r['trials'] for r in rs)
    comparisons=[]
    for cohort in ['controlled','natural']:
        for router in ['uniform','learned']:
            a={r['case_id']:r for r in per if r['cohort']==cohort and r['variant']==router+'_relative'}
            b={r['case_id']:r for r in per if r['cohort']==cohort and r['variant']==router+'_absolute'}
            comparisons.append({'cohort':cohort,'router':router,**paired_stats([a[k]['triple_f1']-b[k]['triple_f1'] for k in sorted(a)])})
    write_csv(HERE/'optimizer_per_case.csv',per)
    (HERE/'results.json').write_text(json.dumps({'summary':summary,'comparisons_exploratory':comparisons,
        'diagnostic_changed_cases':dict(diag_changes),'scope':'Previously observed test proposals; fixed alternatives, no tuning; not a new holdout.','api_calls':0},indent=2)+'\n')

if __name__=='__main__':
    {'build':build,'evaluate':evaluate_router,'replay':replay}[sys.argv[1]]()
