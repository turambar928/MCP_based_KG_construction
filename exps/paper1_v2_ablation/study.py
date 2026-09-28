"""Current v2, fixed proposals: 13 switches × 450 inputs, two prior origins."""
import gzip,hashlib,json,sys,time
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.math_revision_20260925.paper1.study import ReplayOptimizer,context
from exps.paper1_ablation_completion.offline import VARIANTS
from exps.paper1_ablation_completion.analyze import summarize,write_csv,paired_stats,holm
from exps.paper1_mechanism_audit.protocol import read_jsonl,public_input,preprocess,digest,key
from exps.paper1_mechanism_audit.replay_optimizer import recommendations
from exps.paper1_repair_benchmark.run_benchmark import parse_triples
from exps.paper1_mechanism_audit.analyze import metrics
from content_enhancement.constraint_optimizer_v2 import RouterOutput,FEATURE_VERSION
HERE=Path(__file__).resolve().parent
class Variant(ReplayOptimizer):
    def __init__(self,ctx,variant,relative=False):
        super().__init__(ctx,'learned_absolute');self.variant=variant;self.relative_prior=relative
        assert self.router.available and self.router.scaler['feature_version']==FEATURE_VERSION
        if variant=='no_prior':self.eta=0
        if variant=='no_cost':self.enforce_action_cost=False
        if variant=='no_density':self.enforce_upper_bounds=False
        if variant=='no_profile_bounds':self.lower_bounds={}
        if variant=='single_step':self.max_iterations=1
        for k in {'no_local_score':['S_iso','S_red'],'no_graph_score':['S_log'],'no_source_score':['S_sem']}.get(variant,[]):
            self.weights[k]=0;self.lower_bounds.pop(k)
    def route(self,profile):
        if not self.variant.startswith('learned'):return RouterOutput(1.,{s:1/3 for s in ['entity','graph','context']},'always_uniform')
        out=self.router.predict(profile)
        return RouterOutput(1.,out.pi,'f_phi_always') if self.variant=='learned_always' else out
    def _violations_to_actions(self,profile,triples):
        return [] if self.variant=='no_rule_candidates' else super()._violations_to_actions(profile,triples)
    def _recommendations_to_actions(self,recs):
        if self.variant=='no_rule_candidates':recs=[r for r in recs if r.get('type')!='source_field']
        return super()._recommendations_to_actions(recs)
def freeze():
    paths=[Path(__file__),HERE/'test_study.py',ROOT/'content_enhancement/constraint_optimizer_v2.py',ROOT/'exps/math_revision_20260925/paper1/study.py',ROOT/'exps/paper1_ablation_completion/offline.py',ROOT/'exps/paper1_ablation_completion/analyze.py',ROOT/'exps/paper1_mechanism_audit/protocol.py',ROOT/'exps/paper1_mechanism_audit/analyze.py',ROOT/'exps/paper1_mechanism_audit/replay_optimizer.py',ROOT/'exps/paper1_repair_benchmark/run_benchmark.py']
    paths+=list((ROOT/'exps/math_revision_20260925/paper1/router').glob('*.npz'))+list((ROOT/'exps/math_revision_20260925/paper1/router').glob('scaler.json'))
    paths+=[ROOT/p for p in ['exps/paper1_repair_benchmark/benchmark.jsonl','exps/paper1_repair_benchmark/predictions_ours.jsonl','exps/paper1_submission_extensions/natural_extraction_claude.jsonl','exps/paper1_submission_extensions/natural_repairs_full_claude.jsonl']]
    m={'feature_version':FEATURE_VERSION,'variants':VARIANTS,'cohorts':{'controlled':225,'natural':225},'prior_origins':['absolute_primary','relative_sensitivity'],'outcomes':11700,'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'scope':'Previously evaluated fixed proposals, scorer-only labels, zero API calls; no new holdout or coefficient search.','no_rule_candidates':'Disable detector and explicit source-field actions; preserve diagnostic profiles and model proposal adapter.','statistics':'Paired document bootstrap 10000, sign randomization 10000; Holm across 24 component contrasts separately for each prior origin. Relative vs absolute: 26 contrasts, separate Holm family. Exploratory fixed alternatives.'}
    p=HERE/'manifest.json'
    if p.exists():assert json.loads(p.read_text())==m
    else:p.write_text(json.dumps(m,indent=2)+'\n')
    return m
def main():
    freeze();cases=[c for c in read_jsonl(ROOT/'exps/paper1_repair_benchmark/benchmark.jsonl') if c['split']=='test'];assert len(cases)==225
    extraction={r['case_id']:r for r in read_jsonl(ROOT/'exps/paper1_submission_extensions/natural_extraction_claude.jsonl')}
    per=[];stops=Counter();reasons=Counter()
    assert not (HERE/'results.json').exists(),'Use a new version for reruns'
    with gzip.open(HERE/'traces.jsonl.gz','wt') as f:
        for cohort,path in [('controlled','exps/paper1_repair_benchmark/predictions_ours.jsonl'),('natural','exps/paper1_submission_extensions/natural_repairs_full_claude.jsonl')]:
            props={r['case_id']:r for r in read_jsonl(ROOT/path)}
            for c in cases:
                inp=public_input(c,c['corrupted_triples'] if cohort=='controlled' else extraction[c['case_id']]['triples']);initial=preprocess(inp)
                proposed,status=parse_triples(props[c['case_id']]['raw_responses'][-1])
                for prior in ['absolute_primary','relative_sensitivity']:
                    for variant in VARIANTS:
                        opt=Variant(context(inp),variant,prior.startswith('relative'));rec=[] if variant=='rule_only' else recommendations(initial,proposed)
                        start=time.perf_counter();out,applied,audit=opt.optimize_and_apply([{'name':inp.required_document_node}],initial,rec,inp.source_evidence);elapsed=time.perf_counter()-start
                        assert len(opt.trials)==len(audit['decisions'])
                        for d,t in zip(audit['decisions'],opt.trials):d.update(t);reasons[prior,cohort,variant,d['reason']]+=1
                        stops[prior,cohort,variant,audit['stopped_reason']]+=1
                        good=set(map(key,c['clean_triples']));old=set(map(key,inp.triples));final=set(map(key,out))
                        per.append({'prior':prior,'cohort':cohort,'variant':variant,'case_id':c['case_id'],**metrics(c,list(inp.triples),out,cohort),'lost_correct_facts':len((good&old)-final),'applied':len(applied),'trials':len(opt.trials),'wall_seconds':elapsed})
                        f.write(json.dumps({'prior':prior,'cohort':cohort,'variant':variant,'case_id':c['case_id'],'input_sha256':digest(inp.payload()),'proposal_status':status,'triples':out,'audit':audit},ensure_ascii=False)+'\n')
            print(cohort,'complete',flush=True)
    assert len(per)==11700
    summary=summarize(per,['prior','cohort','variant'])
    for s in summary:
        rows=[r for r in per if all(r[k]==s[k] for k in ['prior','cohort','variant'])]
        for k in ['lost_correct_facts','applied','trials','wall_seconds']:s[k]=sum(r[k] for r in rows)
    lookup={(r['prior'],r['cohort'],r['variant'],r['case_id']):r for r in per};contrasts=[];sensitivity=[]
    for prior in ['absolute_primary','relative_sensitivity']:
        family=[]
        for cohort in ['controlled','natural']:
            for v in VARIANTS[1:]:
                base='learned_always' if v=='learned_trigger' else 'uniform_always'
                diff=[lookup[prior,cohort,v,c['case_id']]['triple_f1']-lookup[prior,cohort,base,c['case_id']]['triple_f1'] for c in cases]
                family.append({'prior':prior,'cohort':cohort,'variant':v,'baseline':base,**paired_stats(diff)})
        holm(family);contrasts+=family
    for cohort in ['controlled','natural']:
        for v in VARIANTS:
            diff=[lookup['relative_sensitivity',cohort,v,c['case_id']]['triple_f1']-lookup['absolute_primary',cohort,v,c['case_id']]['triple_f1'] for c in cases]
            sensitivity.append({'cohort':cohort,'variant':v,**paired_stats(diff)})
    holm(sensitivity)
    write_csv(HERE/'per_case.csv',per);write_csv(HERE/'summary.csv',summary);write_csv(HERE/'contrasts.csv',contrasts)
    (HERE/'results.json').write_text(json.dumps({'summary':summary,'contrasts':contrasts,'prior_sensitivity':sensitivity,'stops':{'|'.join(k):v for k,v in stops.items()},'reasons':{'|'.join(k):v for k,v in reasons.items()},'api_calls':0},indent=2)+'\n')
if __name__=='__main__':main()
