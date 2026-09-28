import unittest
import numpy as np
from exps.paper2_rate_ablation.environment import SmallCountEnvironment
from exps.paper2_reward_validation.environment import RewardEnvironment
from exps.math_revision_20260925.paper2.policy_study import graph,observe
class Tests(unittest.TestCase):
 def test_reward_changes_not_transition(self):
  clean=graph();a=RewardEnvironment(clean,950000);b=SmallCountEnvironment(clean,950000,coefficient=.0001)
  for step in range(10):
   self.assertEqual(a.graph.rels,b.graph.rels);np.testing.assert_array_equal(a.state(),b.state())
   valid=np.flatnonzero(a.available_action_mask());action=int(valid[step%len(valid)])
   _,ra,da,ia=a.step(action);_,rb,db,ib=b.step(action)
   self.assertAlmostEqual(rb,ra+ia['scaled_new_burden']-.0001*ia['new_violations']);self.assertEqual(da,db)
   if da:break
 def test_feature_switches(self):
  x=np.arange(14,dtype=float)+1
  np.testing.assert_array_equal(observe(x,'no_graph_features')[[0,1,2,3,7,8,9,10]],0)
  np.testing.assert_array_equal(observe(x,'no_rule_features')[[4,5,6,12,13]],0)
  np.testing.assert_array_equal(x,np.arange(14,dtype=float)+1)
if __name__=='__main__':unittest.main()
