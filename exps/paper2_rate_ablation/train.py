"""Forty matched neural training runs; fixed budgets and reward modes."""
import concurrent.futures,random,time,argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from torch import nn
from exps.paper2_rate_ablation.protocol import *
from exps.paper2_cooptimization import run_experiment as old
from exps.math_revision_20260925.paper2.policy_study import graph
from exps.paper2_reward_validation.environment import RewardEnvironment,RewardConfig
from exps.paper2_rate_ablation.environment import SmallCountEnvironment
from exps.math_revision_20260925.paper2.policy_study import observe
def train_one(task):
    variant,run=task;algorithm,mode='Double DQN','scaled';dest=HERE/'training'/f'{variant}_{run}'
    if (dest/'complete.json').exists():return {'variant':variant,'seed':run,'cached':True}
    dest.mkdir(parents=True,exist_ok=True);started=time.perf_counter();seed=TRAIN_SEEDS[run]
    old.set_all_seeds(seed);rng=random.Random(seed);clean=graph()
    online=old.QNetwork(14,8);target=old.QNetwork(14,8);target.load_state_dict(online.state_dict());target.eval()
    optimizer=torch.optim.Adam(online.parameters(),lr=CFG.learning_rate);replay=old.ReplayBuffer(CFG.replay_size);loss_fn=nn.SmoothL1Loss();global_step=0;history=[]
    for episode in range(CFG.episodes):
        env=SmallCountEnvironment(clean,seed*100000+episode,coefficient=calibration()['coefficient']) if variant=='small_count' else RewardEnvironment(clean,seed*100000+episode) 
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
                    if algorithm=='DQN':
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
    result={'variant':variant,'seed':run,'episodes':250,'wall_seconds':time.perf_counter()-started,'api_calls':0,'training_transitions':global_step,'reward_mode':variant if variant in ['small_count','no_call_penalty'] else mode,'training_seed':seed}
    (dest/'complete.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=8);args=p.parse_args();freeze()
    tasks=[(arm,run) for run in range(10) for arm in ARMS]
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(train_one,tasks):print(json.dumps(result),flush=True)
