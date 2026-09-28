"""Fixed local rate-reward ablations, no generated-rule integration claim."""
import hashlib,json,random,sys
from pathlib import Path
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper2_reward_validation.protocol import CFG,TRAIN_SEEDS
from exps.paper2_reward_validation.environment import RewardEnvironment
from exps.math_revision_20260925.paper2.policy_study import graph
HERE=Path(__file__).resolve().parent
ARMS=['no_graph_features','no_rule_features','no_mask','no_call_penalty','small_count']
POLICIES=['ddqn_scaled']+ARMS+['acquire_then_deficit']
DEV_SEEDS=list(range(950000,950020));TEST_SEEDS=list(range(940000,940030))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def calibration():
    p=HERE/'calibration.json'
    if p.exists():return json.loads(p.read_text())
    clean=graph();burden=0.;count=0;records=[]
    for seed in DEV_SEEDS:
        env=RewardEnvironment(clean,seed);rng=random.Random(seed)
        for step in range(18):
            mask=env.available_action_mask();valid=[i for i in range(8) if mask[i]]
            if not valid:break
            a=rng.choice(valid);_,_,done,info=env.step(a);burden+=info['scaled_new_burden'];count+=info['new_violations']
            records.append({'scenario':seed,'step':step,'action':a,'count':info['new_violations'],'rate_burden':info['scaled_new_burden']})
            if done:break
    assert count>0
    result={'rule':'Sum rate burden / sum introduced counts on 20 fixed uniform-valid development rollouts; no reference/gold or outcome-based coefficient search.','coefficient':burden/count,'sum_rate':burden,'sum_count':count,'records':records}
    dump(p,result);return result
def freeze():
    calibration()
    deps=[HERE/p for p in ['environment.py','protocol.py','train.py','evaluation.py','analyze.py','test_study.py','calibration.json']]
    deps +=[ROOT/p for p in ['exps/paper2_reward_validation/environment.py','exps/paper2_reward_validation/protocol.py','exps/paper2_reward_validation/metrics.py','exps/math_revision_20260925/paper2/policy_study.py','exps/math_revision_20260925/paper2/environment.py','exps/paper2_cooptimization/run_experiment.py','data/train.json']]
    deps+=sorted((ROOT/'exps/paper2_reward_validation/training').glob('ddqn_scaled_*/checkpoint.pt'))
    m={'arms':ARMS,'policies':POLICIES,'config':asdict(CFG),'training_seeds':TRAIN_SEEDS,'development_seeds':DEV_SEEDS,'scenario_seeds':TEST_SEEDS,'training_runs':50,'baseline':'Ten existing ddqn_scaled checkpoints, same seeds/budget/transition environment; no retraining or epoch selection.','scope':'New corruption seeds on the same existing 450-document base graph; not new documents/domains and not generated-rule RL.','observation_removal':'Graph [0,1,2,3,7,8,9,10]; rule [4,5,6,12,13]; masked values zero at train and eval; other features/mask retained.','no_mask':'All eight actions at train/eval; environment rejects unavailable actions with existing penalty; unavailable action count reported.','no_call_penalty':'Remove call term from training reward only; common scaled evaluation reward and counted calls retained.','small_count':'Fixed development calibration, identical transitions and features; evaluation uses common scaled reward.','statistics':'Seed as unit, average 30 scenarios; 10000 paired bootstrap and exact 1024-sign permutation; Holm 12 contrasts (6 alternatives x F1/restoration).','sha256':{str(p.relative_to(ROOT)):sha(p) for p in deps},'api_calls':0}
    p=HERE/'manifest.json'
    if p.exists():assert json.loads(p.read_text())==m,'Frozen experiment changed'
    else:dump(p,m)
    return m
if __name__=='__main__':freeze()
