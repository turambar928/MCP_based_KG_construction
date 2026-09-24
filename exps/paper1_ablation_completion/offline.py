"""Isolated switches of the actual optimizer; fixed archived proposals, zero API calls."""
import json,sys,time,hashlib
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_mechanism_audit.replay_optimizer import AuditedOptimizer,recommendations
from exps.paper1_mechanism_audit.protocol import read_jsonl,public_input,preprocess,digest
from exps.paper1_repair_benchmark.run_benchmark import parse_triples
from content_enhancement.constraint_optimizer import RouterOutput
from exps.paper1_ablation_completion.analyze import summarize,write_csv,paired_stats
from exps.paper1_mechanism_audit.analyze import metrics
HERE=Path(__file__).resolve().parent
VARIANTS=['uniform_always','learned_always','learned_trigger','no_prior','no_cost','no_density','no_profile_bounds','single_step','no_rule_candidates','rule_only','no_local_score','no_graph_score','no_source_score']
class VariantOptimizer(AuditedOptimizer):
    def __init__(self,variant):
        super().__init__(uniform=not variant.startswith('learned'));self.variant=variant
        if variant.startswith('learned'):assert self.router.available,'Frozen neural weights unavailable'
        if variant=='no_prior':self.eta=0
        if variant=='no_cost':self.enforce_action_cost=False
        if variant=='no_density':self.enforce_upper_bounds=False
        if variant=='no_profile_bounds':self.lower_bounds={}
        if variant=='single_step':self.max_iterations=1
        masks={'no_local_score':['S_iso','S_red'],'no_graph_score':['S_log'],'no_source_score':['S_sem']}
        for k in masks.get(variant,[]):self.weights[k]=0;self.lower_bounds.pop(k)
        # Remaining quality weights deliberately retain their original magnitude.
    def route(self,profile):
        out=super().route(profile)
        if self.variant=='learned_always':return RouterOutput(1.,out.pi,'f_phi_always')
        return out
    def _violations_to_actions(self,profile,triples):
        return [] if self.variant=='no_rule_candidates' else super()._violations_to_actions(profile,triples)

def main():
    from exps.paper1_ablation_completion.run import verify
    verify();cases=[r for r in read_jsonl(ROOT/'exps/paper1_repair_benchmark/benchmark.jsonl') if r['split']=='test']
    extraction={r['case_id']:r for r in read_jsonl(ROOT/'exps/paper1_submission_extensions/natural_extraction_claude.jsonl')}
    paths={'controlled':'exps/paper1_repair_benchmark/predictions_ours.jsonl','natural':'exps/paper1_submission_extensions/natural_repairs_full_claude.jsonl'}
    per=[];stops=Counter();reasons=Counter()
    with (HERE/'optimizer_traces.jsonl').open('w') as f:
        for cohort,path in paths.items():
            proposals={r['case_id']:r for r in read_jsonl(ROOT/path)}
            for c in cases:
                inp=public_input(c,c['corrupted_triples'] if cohort=='controlled' else extraction[c['case_id']]['triples'])
                proposed,status=parse_triples(proposals[c['case_id']]['raw_responses'][-1]);initial=preprocess(inp)
                for variant in VARIANTS:
                    opt=VariantOptimizer(variant);rec=[] if variant=='rule_only' else recommendations(initial,proposed)
                    start=time.perf_counter();out,applied,audit=opt.optimize_and_apply([{'name':inp.required_document_node}],initial,rec,inp.source_evidence);elapsed=time.perf_counter()-start
                    assert len(opt.trials)==len(audit['decisions'])
                    for d,t in zip(audit['decisions'],opt.trials):d.update(t);reasons[cohort,variant,d['reason']]+=1
                    stops[cohort,variant,audit['stopped_reason']]+=1
                    m=metrics(c,list(inp.triples),out,cohort)
                    per.append({'cohort':cohort,'case_id':c['case_id'],'variant':variant,**m,'applied':len(applied),'trial_count':len(opt.trials),'wall_seconds':elapsed})
                    f.write(json.dumps({'cohort':cohort,'case_id':c['case_id'],'variant':variant,'proposal_status':status,'input_sha256':digest(inp.payload()),'triples':out,'audit':audit,'applied_count':len(applied),'wall_seconds':elapsed},ensure_ascii=False)+'\n')
            print(cohort,'done',flush=True)
    summary=summarize(per,['cohort','variant'])
    for r in summary:
        rs=[x for x in per if x['cohort']==r['cohort'] and x['variant']==r['variant']]
        for k in ['applied','trial_count','wall_seconds']:r[k]=sum(x[k] for x in rs)
    contrasts=[]
    for cohort in paths:
        for variant in VARIANTS[1:]:
            base='learned_always' if variant=='learned_trigger' else 'uniform_always'
            a={r['case_id']:r for r in per if r['cohort']==cohort and r['variant']==variant};b={r['case_id']:r for r in per if r['cohort']==cohort and r['variant']==base}
            contrasts.append({'cohort':cohort,'variant':variant,'baseline':base,**paired_stats([a[c]['triple_f1']-b[c]['triple_f1'] for c in sorted(a)])})
    write_csv(HERE/'optimizer_per_case.csv',per);write_csv(HERE/'optimizer_summary.csv',summary);write_csv(HERE/'optimizer_contrasts.csv',contrasts)
    (HERE/'optimizer_results.json').write_text(json.dumps({'summary':summary,'contrasts_exploratory':contrasts,'stops':{'|'.join(k):v for k,v in stops.items()},'reasons':{'|'.join(k):v for k,v in reasons.items()}},indent=2)+'\n')
if __name__=='__main__':main()
