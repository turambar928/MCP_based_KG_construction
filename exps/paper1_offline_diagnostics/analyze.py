"""Post-hoc diagnostic analysis of fixed proposals and saved optimizer states. No API."""
import gzip,hashlib,itertools,json,sys
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_mechanism_audit.protocol import read_jsonl,public_input,preprocess,key
from exps.paper1_mechanism_audit.replay_optimizer import recommendations
from exps.paper1_repair_benchmark.run_benchmark import parse_triples
from exps.paper1_submission_extensions.analyze_experiments import generic_metrics
from exps.paper1_ablation_completion.analyze import write_csv,paired_stats
from content_enhancement.constraint_optimizer import MultiScaleConstraintOptimizer
HERE=Path(__file__).resolve().parent
BASE=ROOT/'exps/paper1_ablation_completion'

def f1(output,gold):return generic_metrics([],output,gold)['triple_f1']
def proposal_oracle(initial,proposed,gold):
    """Enumerate actual runtime actions from fixed model bundles. Reference-only diagnostic.

    Ignores feasibility, cost, stopping and detector actions. Model-generated
    per-relation actions touch disjoint relations, so subset order is canonical.
    Ties prefer fewer actions then lower subset mask. Empty subset is included.
    """
    runtime=MultiScaleConstraintOptimizer()
    candidates=runtime._recommendations_to_actions(recommendations(initial,proposed))
    assert len(candidates)<=16,'Unexpected candidate count; do not silently approximate enumeration'
    best=None
    for mask in range(1<<len(candidates)):
        out=[dict(t) for t in initial]
        for i,c in enumerate(candidates):
            if mask&(1<<i):out=runtime._apply_candidate(out,c)
        score=f1(out,gold);ranking=(score,-mask.bit_count(),-mask)
        if best is None or ranking>best[0]:best=(ranking,out,mask)
    assert best[0][0]+1e-12>=f1(initial,gold)
    return {'triples':best[1],'f1':best[0][0],'selected_actions':best[2].bit_count(),'candidate_actions':len(candidates),'subsets':1<<len(candidates)}

def main():
    from exps.paper1_ablation_completion.run import verify
    verify()
    paths=['exps/paper1_offline_diagnostics/analyze.py','exps/paper1_ablation_completion/optimizer_traces.jsonl.gz',
      'exps/paper1_repair_benchmark/benchmark.jsonl','exps/paper1_repair_benchmark/predictions_ours.jsonl',
      'exps/paper1_submission_extensions/natural_extraction_claude.jsonl','exps/paper1_submission_extensions/natural_repairs_full_claude.jsonl']
    manifest={'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
      'study':'Post-hoc descriptive bottleneck analysis on previously evaluated cases; no tuning, API calls, or new holdout.',
      'oracle':'Reference-scored exhaustive subset of actual per-relation model-proposal actions; no new facts or detector actions; ignores feasibility, utility and stopping. Upper bound only for this fixed subset family, not a deployable system.',
      'statistics':'Document-paired means and 10000 document bootstrap with seed42. All comparisons exploratory; no confirmatory significance claims.'}
    lock=HERE/'manifest.json'
    if lock.exists():assert json.loads(lock.read_text())==manifest
    else:lock.write_text(json.dumps(manifest,indent=2)+'\n')
    traces=[json.loads(l) for l in gzip.decompress((BASE/'optimizer_traces.jsonl.gz').read_bytes()).splitlines()]
    idx={(r['cohort'],r['case_id'],r['variant']):r for r in traces}
    cases={c['case_id']:c for c in read_jsonl(ROOT/paths[2]) if c['split']=='test'}
    ext={r['case_id']:r for r in read_jsonl(ROOT/paths[4])};per=[];trials=[];outputs=[];changes=[]
    for cohort,path in [('controlled',paths[3]),('natural',paths[5])]:
        proposals={r['case_id']:r for r in read_jsonl(ROOT/path)}
        for cid,c in sorted(cases.items()):
            start=c['corrupted_triples'] if cohort=='controlled' else ext[cid]['triples'];initial=preprocess(public_input(c,start));gold=c['clean_triples']
            proposal,status=parse_triples(proposals[cid]['raw_responses'][-1]);oracle=proposal_oracle(initial,proposal,gold)
            baseline=idx[cohort,cid,'uniform_always'];nocost=idx[cohort,cid,'no_cost'];audit=baseline['audit'];basef=f1(baseline['triples'],gold)
            missing=Counter(map(key,gold))-Counter(map(key,initial));extra=Counter(map(key,initial))-Counter(map(key,gold))
            groups={r:sum(t['relation']==r for t in initial) for r in {t['relation'] for t in gold}}
            potential=oracle['f1']>f1(initial,gold)+1e-12
            row={'cohort':cohort,'case_id':cid,'domain':c['domain'],'proposal_status':status,
              'input_f1':f1(start,gold),'preprocessed_f1':f1(initial,gold),'preprocessed_exact':not missing and not extra,
              'preprocessed_missing_occurrences':sum(missing.values()),'preprocessed_extra_occurrences':sum(extra.values()),
              'missing_relation_fields':sum(v==0 for v in groups.values()),
              'raw_proposal_f1':f1(proposal,gold),'optimizer_f1':basef,'no_cost_f1':f1(nocost['triples'],gold),
              'oracle_f1':oracle['f1'],'oracle_potential':potential,'oracle_candidates':oracle['candidate_actions'],'oracle_subsets':oracle['subsets'],
              'oracle_selected':oracle['selected_actions'],'initial_no_violations':not audit['initial_profile']['violations'],
              'stopped_reason':audit['stopped_reason'],'accepted':baseline['applied_count'],'no_cost_accepted':nocost['applied_count']}
            per.append(row)
            outputs.append({'cohort':cohort,'case_id':cid,'preprocessed':initial,'raw_proposal':proposal,'reference':gold,'oracle':oracle['triples'],'oracle_selected':oracle['selected_actions'],'optimizer':baseline['triples'],'no_cost':nocost['triples']})
            for decision in audit['decisions']:
                delta=f1(decision['after_triples'],gold)-f1(decision['before_triples'],gold)
                trials.append({'cohort':cohort,'case_id':cid,'iteration':decision['iteration'],'reason':decision['reason'],'utility':decision['utility'],'accepted':decision['accepted'],'reference_f1_change':delta,'improves_reference':delta>1e-12,'harms_reference':delta< -1e-12})
            for variant in sorted({r['variant'] for r in traces}):
                r=idx[cohort,cid,variant];delta=f1(r['triples'],gold)-basef
                changes.append({'cohort':cohort,'case_id':cid,'domain':c['domain'],'variant':variant,
                  'triples_changed':Counter(map(key,r['triples']))!=Counter(map(key,baseline['triples'])),
                  'f1_change':delta,'improved':delta>1e-12,'harmed':delta< -1e-12,'accepted':r['applied_count']})
    summary=[]
    for cohort in ['controlled','natural']:
        rs=[r for r in per if r['cohort']==cohort];ts=[r for r in trials if r['cohort']==cohort]
        summary.append({'cohort':cohort,'n':len(rs),**{k:float(np.mean([r[k] for r in rs])) for k in ['input_f1','preprocessed_f1','raw_proposal_f1','optimizer_f1','no_cost_f1','oracle_f1']},
          'oracle_can_improve':sum(r['oracle_potential'] for r in rs),
          'no_initial_violations':sum(r['initial_no_violations'] for r in rs),
          'no_violation_but_imperfect':sum(r['initial_no_violations'] and not r['preprocessed_exact'] for r in rs),
          'no_violation_but_missing_field':sum(r['initial_no_violations'] and r['missing_relation_fields']>0 for r in rs),
          'no_violation_with_available_improvement':sum(r['initial_no_violations'] and r['oracle_potential'] for r in rs),
          'improving_trials_nonpositive':sum(r['improves_reference'] and r['reason']=='non_positive_utility' for r in ts),
          'improving_trials_constraint_rejected':sum(r['improves_reference'] and r['reason'] not in ['accepted','non_positive_utility','lower_utility_than_selected'] for r in ts),
          'accepted_harmful_trials':sum(r['harms_reference'] and r['accepted'] for r in ts)})
    var_summary=[]
    for cohort in ['controlled','natural']:
        for variant in sorted({r['variant'] for r in changes}):
            rs=[r for r in changes if r['cohort']==cohort and r['variant']==variant]
            var_summary.append({'cohort':cohort,'variant':variant,'n':len(rs),**{k:sum(r[k] for r in rs) for k in ['triples_changed','improved','harmed']},**paired_stats([r['f1_change'] for r in rs])})
    strata=[]
    for cohort in ['controlled','natural']:
        for stratum in ['all','preprocessed_exact','preprocessed_imperfect']:
            for domain in ['all']+sorted({r['domain'] for r in per}):
                rs=[r for r in per if r['cohort']==cohort and (domain=='all' or r['domain']==domain) and (stratum=='all' or r['preprocessed_exact']==(stratum=='preprocessed_exact'))]
                if not rs:continue
                diff=[r['no_cost_f1']-r['optimizer_f1'] for r in rs]
                strata.append({'cohort':cohort,'domain':domain,'stratum':stratum,'improved':sum(x>1e-12 for x in diff),'harmed':sum(x< -1e-12 for x in diff),**paired_stats(diff)})
    for name,rs in [('per_case',per),('trial_outcomes',trials),('summary',summary),('variant_changes',changes),('variant_summary',var_summary),('cost_strata',strata)]:write_csv(HERE/(name+'.csv'),rs)
    (HERE/'case_outputs.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in outputs))
    results={'summary':summary,'variant_summary':var_summary,'cost_strata':strata,'total_oracle_subsets':sum(r['oracle_subsets'] for r in per),'n_reference_guided_oracles':len(per)}
    (HERE/'results.json').write_text(json.dumps(results,indent=2,allow_nan=False)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
