"""Check artifact completeness, source fingerprints, budgets, and scoring invariants."""
import csv,gzip,hashlib,json,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT))

def main():
    from exps.paper2_offline_revision.policy_study import freeze,VARIANTS,BASELINES
    from exps.paper2_offline_revision.rule_study import score
    freeze()
    rule_manifest=json.loads((HERE/'rule_manifest.json').read_text())
    for path,expected in rule_manifest['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,path
    completes=list((HERE/'training').glob('*/complete.json'));assert len(completes)==40
    episodes=0
    for p in completes:
        m=json.loads(p.read_text());assert m['api_calls']==0 and m['episodes']==250
        history=list(csv.DictReader((p.parent/'history.csv').open()));assert len(history)==250
        assert [int(r['episode']) for r in history]==list(range(1,251));episodes+=len(history)
        assert (p.parent/'checkpoint.pt').is_file()
    outcomes=json.loads((HERE/'policy_results.json').read_text());assert len(outcomes)==110
    transitions=[json.loads(l) for l in (HERE/'policy_transitions.jsonl').read_text().splitlines()]
    for r in outcomes:
        assert r['actual_api_calls']==0
        curve=r['curve18'];assert len(curve)==19 and abs(np.trapz(curve)/18-r['auc18'])<1e-12
        assert abs(curve[-1]-r['final_joint'])<1e-12
        ts=[t for t in transitions if t['policy']==r['policy'] and t['run_seed']==r['run_seed']]
        assert len(ts)==r['steps'] and sum(t['calls'] for t in ts)==r['accounted_calls']
        assert sum(not t['valid'] for t in ts)==r['invalid_actions']
        assert r['graph_edits']+r['rule_edits']==r['total_edits_including_rules']
        if r['policy']!='no_mask':assert r['invalid_actions']==0
        if r['policy']!='model_informed_lookahead':assert r['environment_probes']==0
    samples=list(csv.DictReader((HERE/'budget_per_sample.csv').open()));assert len(samples)==450
    for s in samples:
        assert int(s['documents'])*(2 if s['strategy']=='dual' else 1)==int(s['budget_calls'])
        assert int(s['declarations'])+int(s['constraint_candidates'])==int(s['unique_candidates'])
    rules=json.loads((HERE/'rule_analysis.json').read_text())
    cases=json.loads((ROOT/'data/rule_test_triples.json').read_text())
    lineage=[json.loads(l) for l in gzip.open(HERE/'rule_lineage.jsonl.gz','rt')]
    assert len(lineage)==rules['unique_compiled']==18143
    assert sum(bool(r['matched_cases']) for r in lineage)==rules['unique_compiled_with_case_match']==2
    for outcome in rules['execution']:
        active={(r['kind'],tuple(r['pattern'])) for r in lineage if outcome['strategy']=='dual' or any(s['strategy']==outcome['strategy'] for s in r['sources'])}
        measured,_=score(active,cases)
        assert all(measured[k]==outcome[k] for k in measured)
        assert outcome['tp']+outcome['fn']==64 and outcome['tn']+outcome['fp']==30
    with gzip.open(HERE/'candidate_execution_audit.jsonl.gz','rb') as f:raw=f.read()
    assert hashlib.sha256(raw).hexdigest()==rules['audit_uncompressed_sha256']
    assert len(raw.splitlines())==rules['candidate_occurrences']==181851
    correction=json.loads((HERE/'rule_scoring_correction.json').read_text())
    assert hashlib.sha256((HERE/'rule_analysis.json').read_bytes()).hexdigest()==correction['previous_result_sha256']
    for name,expected in json.loads((HERE/'prompts/manifest.json').read_text())['sha256'].items():
        assert hashlib.sha256((HERE/'prompts'/name).read_bytes()).hexdigest()==expected
    report={'passed':True,'new_models':40,'new_training_episodes':episodes,'evaluation_outcomes':110,
      'evaluation_transitions':len(transitions),'budget_samples':450,'candidate_occurrences':len(raw.splitlines()),
      'actual_api_calls':0,'frozen_inputs_unchanged':True,'original_checkpoints_reproduced':20,
      'rule_edgecase_correction_preserves_formal_outputs':True}
    # Exact original-checkpoint reproduction is also asserted in analyze_policy.py.
    assert json.loads((HERE/'policy_analysis.json').read_text())['existing_checkpoints_reproduced']==20
    (HERE/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
