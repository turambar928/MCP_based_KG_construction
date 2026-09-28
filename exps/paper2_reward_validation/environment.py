"""Three fixed reward modes over unchanged version-2 graph/rule transitions."""
from collections import Counter
from dataclasses import dataclass
from exps.math_revision_20260925.paper2.environment import *
from exps.math_revision_20260925.paper2.environment import Paper2CoOptimizationEnv as IdentityEnv

WEIGHTS = dict(zip(DEFECT_NAMES, (.2,.2,.3,.3)))

@dataclass(frozen=True)
class RewardConfig:
    mode: str = 'scaled'
    def __post_init__(self):
        if self.mode not in ('raw','scaled','zero'):
            raise ValueError('Reward mode must be raw, scaled, or zero')

class RewardEnvironment(IdentityEnv):
    def __init__(self,*args,reward_config=None,**kwargs):
        self.reward_config=reward_config or RewardConfig()
        super().__init__(*args,**kwargs)
    def reset(self):
        state=super().reset()
        self.initial_node_count=len(self.graph.nodes)
        self.initial_edge_count=len(self.graph.rels)
        self.reward_denominators={k:max(1,self.initial_node_count if k=='isolated' else self.initial_edge_count) for k in DEFECT_NAMES}
        return state
    def step(self,action):
        if not 0<=action<8:raise ValueError('Action index outside fixed action space')
        state,raw_reward,done,info=super().step(action)
        ids=info.get('introduced_violation_ids',[])
        counts=Counter()
        for kind,identity,n in ids:counts[kind]+=n
        assert sum(counts.values())==info['new_violations']
        burden=sum(WEIGHTS[k]*counts[k]/self.reward_denominators[k] for k in DEFECT_NAMES)
        penalties={'raw':.01*sum(counts.values()),'scaled':burden,'zero':0.}
        components=dict(info['reward_components'])
        components['new_violations']=-penalties[self.reward_config.mode]
        base=sum(v for k,v in components.items() if k!='new_violations')
        info.update(reward_mode=self.reward_config.mode,initial_node_count=self.initial_node_count,
            initial_edge_count=self.initial_edge_count,reward_denominators=dict(self.reward_denominators),
            introduced_violation_ids=ids,new_by_kind={k:counts[k] for k in DEFECT_NAMES},
            scaled_new_burden=burden,safety_penalties=penalties,reward_components=components,
            counterfactual_rewards={k:base-v for k,v in penalties.items()})
        reward=sum(components.values())
        assert abs(info['counterfactual_rewards']['raw']-raw_reward)<1e-9
        return state,reward,done,info
