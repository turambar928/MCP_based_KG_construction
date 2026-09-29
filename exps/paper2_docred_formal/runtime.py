"""Public-only cached runtime and fresh masked DQN/DDQN training."""
import random
from collections import deque
import numpy as np
import torch
from torch import nn
from exps.paper2_docred_v2_round2.environment import SourceRuleEnvironment,ACTIONS,FEATURES

class Network(nn.Module):
    def __init__(self):
        super().__init__();self.layers=nn.Sequential(nn.Linear(14,64),nn.ReLU(),nn.Linear(64,64),nn.ReLU(),nn.Linear(64,4))
    def forward(self,x):return self.layers(x)


def vector(obs):return np.array([obs['features'][k] for k in FEATURES],dtype=np.float32)

def choose(obs,policy,rng,model=None):
    mask=obs['mask'];feasible=[i for i,m in enumerate(mask) if m]
    if not feasible:raise ValueError('Terminal state has no action')
    if policy=='stop':return 3
    if policy=='uniform_feasible':return rng.choice(feasible)
    if policy=='repair_asap' and mask[2]:return 2
    if policy in ('acquire_then_repair','repair_asap'):
        return next((i for i in [0,1] if mask[i]),2 if mask[2] else 3)
    with torch.no_grad():return int(model(torch.tensor(vector(obs))).masked_fill(~torch.tensor(mask),-torch.inf).argmax().item())


def bellman(online,target,next_states,masks,dones,gamma=.95,double=True):
    with torch.no_grad():
        safe=masks.any(1)&~dones.bool()
        masked=online(next_states) if double else target(next_states)
        actions=masked.masked_fill(~masks,-torch.inf).argmax(1,keepdim=True)
        values=target(next_states).gather(1,actions).squeeze(1)
        return gamma*torch.where(safe,values,torch.zeros_like(values))


def train(dataset,seed,variant,episodes=250):
    torch.set_num_threads(1);torch.manual_seed(seed);np.random.seed(seed);rng=random.Random(seed)
    online=Network();target=Network();target.load_state_dict(online.state_dict());target.eval()
    optimizer=torch.optim.Adam(online.parameters(),lr=.001);replay=deque(maxlen=10000);step=0;history=[]
    for episode in range(episodes):
        item=dataset[rng.randrange(len(dataset))];env=SourceRuleEnvironment(item['records'],item['packets'],'legacy' if variant=='legacy_ddqn' else 'fixed_rule')
        obs=env.observe();epsilon=1-.95*min(episode/249,1);total=0.;losses=[]
        while not env.done:
            action=rng.choice([i for i,m in enumerate(obs['mask']) if m]) if rng.random()<epsilon else choose(obs,variant,rng,online)
            nxt,reward,done,event=env.step(ACTIONS[action]);replay.append((vector(obs),action,reward,vector(nxt),done,nxt['mask']));obs=nxt;total+=reward;step+=1
            if len(replay)>=128:
                batch=rng.sample(list(replay),64)
                states=torch.tensor(np.stack([r[0] for r in batch]));actions=torch.tensor([r[1] for r in batch]);rewards=torch.tensor([r[2] for r in batch],dtype=torch.float32)
                next_states=torch.tensor(np.stack([r[3] for r in batch]));dones=torch.tensor([r[4] for r in batch]);masks=torch.tensor([r[5] for r in batch])
                targets=rewards+bellman(online,target,next_states,masks,dones,double=variant!='dqn')
                loss=nn.functional.smooth_l1_loss(online(states).gather(1,actions[:,None]).squeeze(1),targets)
                optimizer.zero_grad();loss.backward();nn.utils.clip_grad_norm_(online.parameters(),5);optimizer.step();losses.append(loss.item())
            if step%100==0:target.load_state_dict(online.state_dict())
        history.append(dict(episode=episode+1,reward=total,steps=env.steps,epsilon=epsilon,loss=float(np.mean(losses)) if losses else None))
    return online,history


def rollout(item,policy,seed,model=None):
    env=SourceRuleEnvironment(item['records'],item['packets']);rng=random.Random(seed)
    while not env.done:env.step(ACTIONS[choose(env.observe(),policy,rng,model)])
    return dict(records=env.records,events=env.events,acquired=sum(env.acquired.values()),actual_api_calls=0)
