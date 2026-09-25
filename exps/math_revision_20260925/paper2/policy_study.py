"""Offline matched-policy study. Original environment and artifacts remain untouched."""
import argparse,concurrent.futures,csv,hashlib,json,random,sys,time
from dataclasses import asdict
from pathlib import Path
import numpy as np
import torch
from torch import nn
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from exps.math_revision_20260925.paper2 import environment as old
HERE=Path(__file__).resolve().parent
VARIANTS=['DQN','Double DQN','no_graph_features','no_rule_features','no_mask','no_call_penalty']
SCENARIOS=list(range(900000,900010))
BASELINES=['random_valid','alternating_valid','rule_first_valid','acquire_then_deficit']
CFG=old.AgentConfig(episodes=250)

def observe(state,variant):
    x=state.copy()
    if variant=='no_graph_features':x[[0,1,2,3,7,8,9,10]]=0
    if variant=='no_rule_features':x[[4,5,6,12,13]]=0
    return x

def choose_simple(name,state,mask,step,rng):
    """Only public observation and feasible mask; no environment/proposal lookup."""
    feasible=np.flatnonzero(mask).tolist()
    if not feasible:return None
    if name=='random_valid':return rng.choice(feasible)
    if name=='alternating_valid':
        cycle=step//2
        preferred=list(range(4,8)) if step%2==0 else list(range(4))
        preferred=preferred[cycle%4:]+preferred[:cycle%4]
        fallback=list(range(4)) if step%2==0 else list(range(4,8))
        order=preferred+fallback
    elif name=='rule_first_valid':
        schedule=[4,5,6,4,5,7,6]
        if step<7:
            preferred=schedule[step:]+schedule[:step];order=preferred+list(range(8))
        else:
            start=(step-7)%4;order=list(range(start,4))+list(range(start))+[7,6,4,5]
    elif name=='acquire_then_deficit':
        if state[12]<1-1e-7:
            for a in [6,4,5]:
                if mask[a]:return a
        graph=[a for a in feasible if a<4]
        if graph:return max(graph,key=lambda a:([.2,.2,.3,.3][a]*(1-float(state[a])),-a))
        order=[7,6,4,5,0,1,2,3]
    else:raise ValueError(name)
    return next(a for a in order if mask[a])

def graph():return old.build_clean_graph(old.balanced_sample(old.read_jsonl(old.TNEWS_PATH),30,20260917))
def freeze():
    paths=['exps/math_revision_20260925/paper2/environment.py','exps/math_revision_20260925/paper2/policy_study.py',
        'exps/paper2_cooptimization/run_experiment.py','data/train.json']
    m={'scope':'Offline corrected-environment follow-up on existing scenarios; not new holdout.',
       'sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
       'config':asdict(CFG),'run_seeds':list(range(10)),'training_seeds':list(range(10000,10010)),
       'scenario_seeds':SCENARIOS,'training_runs':60,'variants':VARIANTS,'baselines':BASELINES,
       'api_calls':0,'environment_version':old.ENVIRONMENT_VERSION,
       'statistics':'10000 paired bootstrap and exact two-sided sign randomization; Holm over DDQN-vs-heuristic and four ablations, final quality/AUC; seed42'}
    path=HERE/'policy_manifest.json'
    if path.exists(): assert json.loads(path.read_text())==m,'Frozen revision changed'
    else:path.write_text(json.dumps(m,indent=2)+'\n')
    return m

def train_one(task):
    variant,run=task;dest=HERE/'training'/f'{variant}_{run}'
    if (dest/'complete.json').exists():return {'variant':variant,'seed':run,'cached':True}
    dest.mkdir(parents=True,exist_ok=True);started=time.perf_counter();seed=10000+run
    old.set_all_seeds(seed);rng=random.Random(seed);clean=graph()
    online=old.QNetwork(14,8);target=old.QNetwork(14,8);target.load_state_dict(online.state_dict());target.eval()
    optimizer=torch.optim.Adam(online.parameters(),lr=CFG.learning_rate);replay=old.ReplayBuffer(CFG.replay_size);loss_fn=nn.SmoothL1Loss();global_step=0;history=[]
    for episode in range(CFG.episodes):
        env=old.Paper2CoOptimizationEnv(clean,seed*100000+episode)
        state=observe(env.state(),variant);epsilon=old.epsilon_for_episode(episode,CFG);losses=[];reward_sum=0;done=False
        while not done:
            mask=np.ones(8,bool) if variant=='no_mask' else env.available_action_mask().astype(bool)
            feasible=np.flatnonzero(mask).tolist()
            if not feasible:break
            if rng.random()<epsilon:action=rng.choice(feasible)
            else:
                with torch.no_grad():action=int(online(torch.tensor(state).unsqueeze(0)).masked_fill(torch.tensor(~mask).unsqueeze(0),-torch.inf).argmax(1).item())
            next_raw,reward,done,info=env.step(action)
            if variant=='no_call_penalty':reward+=env.call_penalty*info['calls']
            next_state=observe(next_raw,variant)
            next_mask=np.ones(8,bool) if variant=='no_mask' else env.available_action_mask().astype(bool)
            replay.add((state.copy(),action,reward,next_state.copy(),float(done),next_mask.copy()));state=next_state;reward_sum+=reward;global_step+=1
            if len(replay)>=max(CFG.warmup,CFG.batch_size):
                states,actions,rewards,next_states,dones,next_masks=replay.sample(CFG.batch_size,rng)
                predicted=online(states).gather(1,actions.unsqueeze(1)).squeeze(1)
                with torch.no_grad():
                    if variant=='DQN':
                        values=target(next_states).masked_fill(~next_masks,-torch.inf).max(1).values
                    else:
                        nxt=online(next_states).masked_fill(~next_masks,-torch.inf).argmax(1,keepdim=True)
                        values=target(next_states).gather(1,nxt).squeeze(1)
                    values=torch.where(next_masks.any(1),values,torch.zeros_like(values))
                    targets=rewards+CFG.gamma*(1-dones)*values
                loss=loss_fn(predicted,targets);optimizer.zero_grad();loss.backward();nn.utils.clip_grad_norm_(online.parameters(),5);optimizer.step();losses.append(float(loss.item()))
            if global_step%CFG.target_update==0:target.load_state_dict(online.state_dict())
        history.append({'variant':variant,'run_seed':run,'episode':episode+1,'epsilon':epsilon,'reward':reward_sum,'loss':float(np.mean(losses)) if losses else None,'steps':env.step_index,'joint':env.normalized_joint_quality()})
    torch.save({'variant':variant,'run_seed':run,'model_state_dict':online.state_dict(),'agent_config':asdict(CFG)},dest/'checkpoint.pt')
    old.write_csv(dest/'history.csv',history)
    result={'variant':variant,'seed':run,'episodes':250,'wall_seconds':time.perf_counter()-started,'api_calls':0}
    (dest/'complete.json').write_text(json.dumps(result,indent=2)+'\n');return result

def evaluate(name,run,clean,model=None):
    env=old.Paper2CoOptimizationEnv(clean,SCENARIOS[run]);rng=random.Random(70000+run)
    curve=[env.normalized_joint_quality()];rows=[];invalid=0;start=time.perf_counter();probes=0
    for step in range(18):
        state=env.state();mask=env.available_action_mask().astype(bool)
        if not mask.any():break
        if name in BASELINES:action=choose_simple(name,state,mask,step,rng)
        elif name=='model_informed_lookahead':
            probes+=int(mask.sum());action=old.policy_myopic(env,step)
        else:
            observed=observe(state,name)
            effective=np.ones(8,bool) if name=='no_mask' else mask
            with torch.no_grad():action=int(model(torch.tensor(observed).unsqueeze(0)).masked_fill(torch.tensor(~effective).unsqueeze(0),-torch.inf).argmax(1).item())
        valid=bool(mask[action]);invalid+=not valid
        next_state,reward,done,info=env.step(action);curve.append(env.normalized_joint_quality())
        rows.append({'policy':name,'run_seed':run,'scenario_seed':SCENARIOS[run],'state':state.tolist(),'observed_state':observe(state,name).tolist(),'mask':mask.astype(int).tolist(),'action_id':action,'valid':valid,'reward':reward,'next_state':next_state.tolist(),'done':done,**info})
        if done:break
    padded=curve+[curve[-1]]*(19-len(curve));assert len(padded)==19
    result={'policy':name,'run_seed':run,'scenario_seed':SCENARIOS[run],'final_joint':curve[-1],'auc18':float(np.trapz(padded)/18),
      'q_graph':env.q_graph(),'q_rule':env.q_rule(),'steps':env.step_index,'invalid_actions':int(invalid),'accounted_calls':env.total_calls,'actual_api_calls':0,
      'new_violations':sum(r['new_violations'] for r in rows),'total_edits_including_rules':env.total_edits,'graph_edits':sum(r['edits'] for r in rows if r['action'] in old.ACTION_NAMES[:4]),
      'rule_edits':sum(r['edits'] for r in rows if r['action'] in old.ACTION_NAMES[4:]),'environment_probes':probes,
      'wall_seconds':time.perf_counter()-start,'curve18':padded}
    return result,rows

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['freeze','baselines','train','evaluate']);p.add_argument('--workers',type=int,default=4);args=p.parse_args();freeze()
    if args.mode=='freeze':print('Frozen: 60 corrected-environment training runs, 10 paired scenarios.');return
    old.set_all_seeds(42)
    if args.mode=='train':
        tasks=[(v,r) for r in range(10) for v in VARIANTS]
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
            for result in pool.map(train_one,tasks):print(json.dumps(result),flush=True)
        return
    clean=graph();results=[];transitions=[]
    names=BASELINES+['model_informed_lookahead']
    if args.mode=='evaluate':names+=VARIANTS
    for run in range(10):
        for name in names:
            model=None
            if name in VARIANTS:path=HERE/'training'/f'{name}_{run}'/'checkpoint.pt'
            else:path=None
            if path:
                saved=torch.load(path,map_location='cpu',weights_only=True);model=old.QNetwork(14,8);model.load_state_dict(saved['model_state_dict']);model.eval()
            result,rows=evaluate(name,run,clean,model);results.append(result);transitions+=rows
    label='policy' if args.mode=='evaluate' else 'baseline'
    (HERE/(label+'_results.json')).write_text(json.dumps(results,indent=2)+'\n')
    (HERE/(label+'_transitions.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in transitions))
    print('Evaluated',len(results),'paired policy outcomes.',flush=True)
if __name__=='__main__':main()
