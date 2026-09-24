import random,unittest
import numpy as np
from exps.paper2_offline_revision.policy_study import choose_simple,observe,BASELINES,old
from exps.paper2_offline_revision.analyze_policy import paired,holm
class PolicyTests(unittest.TestCase):
    def test_all_baselines_respect_every_nonempty_mask(self):
        state=np.zeros(14,dtype=np.float32)
        for bits in range(1,256):
            mask=np.array([bool(bits&(1<<a)) for a in range(8)])
            for name in BASELINES:
                for step in [0,1,6,7,17]:
                    a=choose_simple(name,state,mask,step,random.Random(42));self.assertTrue(mask[a])
        self.assertIsNone(choose_simple('random_valid',state,np.zeros(8,bool),0,random.Random(0)))
    def test_feature_switches(self):
        state=np.arange(14,dtype=np.float32)+1
        a=observe(state,'no_graph_features');b=observe(state,'no_rule_features')
        self.assertTrue(np.all(a[[0,1,2,3,7,8,9,10]]==0));self.assertTrue(np.all(b[[4,5,6,12,13]]==0))
        self.assertEqual(a[11],state[11]);self.assertEqual(b[11],state[11]);self.assertEqual(state[0],1)
    def test_heuristic_uses_feasible_weighted_deficit(self):
        s=np.array([.5,.7,.3,.9]+[0]*8+[1,0],dtype=np.float32)
        self.assertEqual(choose_simple('acquire_then_deficit',s,np.ones(8,bool),2,random.Random(0)),2)
        s[12]=0;self.assertEqual(choose_simple('acquire_then_deficit',s,np.ones(8,bool),0,random.Random(0)),6)
    def test_exact_paired_statistics(self):
        self.assertEqual(paired([0]*10)['two_sided_p'],1)
        self.assertEqual(paired([1]*10)['two_sided_p'],2/1024)
        rows=[{'two_sided_p':.01},{'two_sided_p':.03},{'two_sided_p':.5}];holm(rows)
        self.assertEqual([r['p_holm'] for r in rows],[.03,.06,.5])
if __name__=='__main__':unittest.main()
