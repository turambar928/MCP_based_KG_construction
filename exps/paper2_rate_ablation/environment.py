"""Fixed small-count control; transitions identical to the rate environment."""
from exps.paper2_reward_validation.environment import RewardEnvironment,RewardConfig
class SmallCountEnvironment(RewardEnvironment):
    def __init__(self,*args,coefficient,**kwargs):
        self.coefficient=coefficient;super().__init__(*args,**kwargs)
    def step(self,action):
        state,reward,done,info=super().step(action)
        rate=info['scaled_new_burden'];count=self.coefficient*info['new_violations']
        info['small_count_penalty']=count;info['training_reward_small_count']=reward+rate-count
        return state,reward+rate-count,done,info
