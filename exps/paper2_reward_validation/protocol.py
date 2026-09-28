"""Preregistered settings and immutable training/test manifests. No network code."""
import hashlib,json,sys
from pathlib import Path
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper2_cooptimization.run_experiment import AgentConfig
HERE=Path(__file__).resolve().parent
CFG=AgentConfig(episodes=250)
TRAIN_SEEDS=list(range(20000,20010))
DEV_SEEDS=list(range(920000,920020))
TEST_SEEDS=list(range(930000,930030))
ARMS={'ddqn_raw':('Double DQN','raw'),'ddqn_scaled':('Double DQN','scaled'),
      'ddqn_zero':('Double DQN','zero'),'dqn_scaled':('DQN','scaled')}
POLICIES=list(ARMS)+['risk_ridge','acquire_then_deficit','rule_first_valid','random_valid']
PRIMARY_COMPARATORS=['ddqn_raw','ddqn_zero','risk_ridge','acquire_then_deficit']
PRIMARY_METRICS=['fact_f1','invalid_relation_repair_rate']
TRAIN_CODE=['environment.py','protocol.py','train.py','risk_baseline.py']
DEPENDENCIES=['exps/math_revision_20260925/paper2/environment.py','exps/math_revision_20260925/paper2/policy_study.py','exps/paper2_cooptimization/run_experiment.py']

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def hashes(paths):return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}
def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def freeze():
    m={'scope':'Unseen controlled corruption seeds on the same 450-document base graph; not unseen documents/domains or natural errors.',
       'config':asdict(CFG),'training_seeds':TRAIN_SEEDS,'development_seeds':DEV_SEEDS,'test_seeds':TEST_SEEDS,
       'training_environment_seed':'training_seed * 100000 + episode (0..249)',
       'ridge_environment_seed':'30000+run, times 100000, plus episode (0..249)',
       'arms':ARMS,'policies':POLICIES,'reward_modes':{'raw':'.01 * introduced violation count',
       'scaled':'sum_k w_k * introduced_k / max(1,initial_nodes if isolated else initial_edges); w=(.2,.2,.3,.3)',
       'zero':'0'},'unchanged':'14 observation values, 8 actions, all transition operators and masks, graph/rule weights, .004 call cost, .00002 edit cost, 18 steps',
       'ridge':{'alpha':1.,'intercept_unpenalized':True,'features':14,'targets':['joint_quality_gain','edit_count','scaled_new_burden'],
        'training_policy':'uniform over feasible actions','episodes_per_seed':250,'training_seeds':list(range(30000,30010)),
        'cost_predictions':'clip edits and burden at zero; call cost known by action; maximize predicted scaled reward; lower action ID breaks ties',
        'privileged_state_or_future_probes':False},
       'evaluation_reward':'All policies executed/scored with scaled reward; raw/zero counterfactual returns also stored.',
       'statistics':{'unit':'training/run seed, averaged over all thirty shared scenarios; conditional on this fixed scenario set',
         'paired_bootstrap':10000,'bootstrap_seed':42,'two_sided_randomization':'all 1024 signs over ten seed means',
         'holm_family':8,'comparators':PRIMARY_COMPARATORS,'metrics':PRIMARY_METRICS},
       'scoring':'Unique exact fact sets vs controlled clean graph; invalid restoration requires original edge identity with its reference relation (deletion is not restoration); references are scorer-only.',
       'development':'Implementation/behavior checks only; no coefficient, seed or epoch selection.',
       'source_sha256':hashes([HERE/p for p in TRAIN_CODE]+[ROOT/p for p in DEPENDENCIES]),
       'data_sha256':sha(ROOT/'data/train.json'),'api_calls':0,'downloads':0}
    path=HERE/'training_manifest.json'
    if path.exists():assert json.loads(path.read_text())==json.loads(json.dumps(m)),'Frozen training protocol changed'
    else:dump(path,m)
    return m

def model_paths():
    return sorted(list((HERE/'training').glob('*/checkpoint.pt'))+list((HERE/'ridge').glob('*/model.npz')))

def seal_test():
    freeze()
    assert len(list((HERE/'training').glob('*/complete.json')))==40
    assert len(list((HERE/'ridge').glob('*/complete.json')))==10
    assert (HERE/'development/verification.json').exists()
    assert json.loads((HERE/'development/verification.json').read_text())['passed']
    paths=[HERE/p for p in ['evaluation.py','metrics.py','analyze.py','test_study.py']]
    m={'test_seeds':TEST_SEEDS,'training_manifest_sha256':sha(HERE/'training_manifest.json'),
       'development_results_sha256':sha(HERE/'development/results.json'),
       'scoring_sha256':hashes(paths),'checkpoints_sha256':hashes(model_paths()),
       'test_opened_after_freeze':True,'selection':'All four neural arms and all baselines; no development selection.'}
    path=HERE/'test_manifest.json'
    if path.exists():assert json.loads(path.read_text())==m,'Test seal changed'
    else:
        assert not (HERE/'test/results.json').exists()
        dump(path,m)
    return m
if __name__=='__main__':
    {'freeze':freeze,'seal':seal_test}[sys.argv[1]]()
