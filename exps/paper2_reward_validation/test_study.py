"""Behavioral and scoring regressions; never opens reserved test scenarios."""
import copy,inspect,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from exps.paper2_reward_validation.environment import RewardEnvironment,RewardConfig,WEIGHTS,VALID_DETECTORS,KG
from exps.paper2_reward_validation.metrics import score,fact_changes,facts,restoration_labels,graph_delta
from exps.paper2_reward_validation.risk_baseline import RiskRidge
from exps.paper2_reward_validation.evaluation import choose
from exps.paper2_reward_validation.protocol import freeze,DEV_SEEDS,TEST_SEEDS,TRAIN_SEEDS,ROOT as PROJECT_ROOT
from exps.math_revision_20260925.paper2.policy_study import graph
from exps.math_revision_20260925.paper2.environment import Paper2CoOptimizationEnv

class RewardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.clean=graph()
    def env(self,mode='scaled'):
        e=RewardEnvironment(self.clean,920000,reward_config=RewardConfig(mode));e.active_rules=set(VALID_DETECTORS);return e
    def test_raw_exactly_preserves_previous_environment(self):
        a=Paper2CoOptimizationEnv(self.clean,920000);b=RewardEnvironment(self.clean,920000,reward_config=RewardConfig('raw'))
        for action in [6,6,2,1,3,0,2,1]:
            sa,ra,da,ia=a.step(action);sb,rb,db,ib=b.step(action)
            np.testing.assert_array_equal(sa,sb);self.assertEqual(ra,rb);self.assertEqual(da,db);self.assertEqual(a.graph,b.graph)
    def test_modes_change_reward_not_mutations(self):
        es=[self.env(m) for m in ['raw','scaled','zero']]
        outputs=[e.step(2) for e in es]
        for e in es[1:]:self.assertEqual(e.graph,es[0].graph)
        self.assertEqual(outputs[0][3]['new_by_kind'],outputs[1][3]['new_by_kind'])
        self.assertGreater(outputs[1][1],outputs[0][1])
    def test_fixed_denominators_after_deletion(self):
        e=self.env();d=dict(e.reward_denominators);n=len(e.graph.rels)
        e.step(3);self.assertLess(len(e.graph.rels),n);self.assertEqual(d,e.reward_denominators)
    def test_rewards_and_weighted_counts(self):
        e=self.env()
        for a in [2,1,3,0]:
            _,r,_,i=e.step(a)
            self.assertAlmostEqual(r,sum(i['reward_components'].values()))
            expected=sum(WEIGHTS[k]*i['new_by_kind'][k]/i['reward_denominators'][k] for k in WEIGHTS)
            self.assertAlmostEqual(expected,i['safety_penalties']['scaled'])
            self.assertEqual(sum(v[-1] for v in i['introduced_violation_ids']),i['new_violations'])
    def test_restoration_duplicate_is_not_new_wrong_fact(self):
        e=self.env();before=copy.deepcopy(e.graph);_,_,_,i=e.step(2);change=fact_changes(self.clean,before,e.graph)
        self.assertGreater(i['new_by_kind']['duplicate'],0)
        self.assertEqual(change['added_wrong_facts'],0);self.assertEqual(change['removed_correct_facts'],0)
    def test_duplicate_cleanup_preserves_fact_set(self):
        e=self.env();e.step(2);before=copy.deepcopy(e.graph);e.step(1)
        self.assertEqual(facts(before),facts(e.graph))
    def test_edge_deletion_is_not_relation_restoration(self):
        e=self.env();initial=copy.deepcopy(e.graph);labels=restoration_labels(e)
        e.graph.rels=[r for r in e.graph.rels if r['_edge_id'] not in labels]
        s=score(self.clean,initial,e.graph,labels);self.assertEqual(s['invalid_relation_repair_rate'],0.)
    def test_correct_fact_loss_is_scored(self):
        e=self.env();initial=copy.deepcopy(e.graph);good=next(iter(facts(initial)&facts(self.clean)))
        e.graph.rels=[r for r in e.graph.rels if (r['start_id'],r['relation_type'],r['end_id'])!=good]
        s=score(self.clean,initial,e.graph,restoration_labels(e));self.assertEqual(s['lost_initial_correct_facts'],1)
        self.assertLess(s['correct_fact_preservation'],1.)
    def test_empty_guard_and_no_actions(self):
        e=self.env();e.graph=KG({'a':{'id':'a','name':'a','node_type':'Document'}},[{'start_id':'a','end_id':'missing','relation_type':'MENTIONS'}])
        _,r,done,i=e.step(3);self.assertTrue(done);self.assertEqual(i['termination_reason'],'destructive_empty_graph');self.assertEqual(len(e.graph.rels),1)
        e.available_action_mask=lambda:np.zeros(8,bool)
        _,r,done,i=e.step(0);self.assertTrue(done);self.assertEqual(r,0.)
    def test_graph_deltas_reconstruct_actual_mutations(self):
        e=self.env()
        for a in [2,1,3,0]:
            before=copy.deepcopy(e.graph);e.step(a);d=graph_delta(before,e.graph)
            edges={r['_edge_id']:r for r in before.rels}
            for k in d['removed_edge_ids']:edges.pop(k)
            for row in d['added_edges']+d['updated_edges']:edges[row['_edge_id']]=row
            self.assertEqual(edges,{r['_edge_id']:r for r in e.graph.rels})
    def test_splits_do_not_overlap(self):
        train={s*100000+ep for s in TRAIN_SEEDS for ep in range(250)}
        self.assertFalse(train&set(TEST_SEEDS));self.assertFalse(set(DEV_SEEDS)&set(TEST_SEEDS));self.assertFalse(train&set(DEV_SEEDS))

class PolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng=np.random.default_rng(42);x=rng.normal(size=(160,14));a=np.repeat(np.arange(8),20)
        y=np.column_stack([x[:,0]*.01,np.ones(160),np.full(160,.001)])
        cls.model=RiskRidge.fit(x,a,y)
    def test_ridge_only_uses_observation_and_mask(self):
        self.assertEqual(list(inspect.signature(self.model.choose).parameters),['state','mask'])
        state=np.zeros(14);mask=np.array([1,0,0,0,0,0,0,0],bool)
        a,_=self.model.choose(state,mask);self.assertEqual(a,0)
        self.assertIsNone(self.model.choose(state,np.zeros(8,bool))[0])
    def test_reference_counterfactual_cannot_change_actions(self):
        state=np.zeros(14);mask=np.ones(8,bool);a,p=self.model.choose(state,mask)
        # Reference changes affect scorer output, never the policy's argument list.
        g=KG({},[{'start_id':'a','relation_type':'r','end_id':'b','_edge_id':'x'}]);wrong=KG({},[])
        self.assertNotEqual(score(g,g,g,{})['fact_f1'],score(wrong,g,g,{})['fact_f1'])
        b,q=self.model.choose(state,mask);self.assertEqual(a,b);self.assertEqual(p,q)
        args=inspect.signature(choose).parameters
        self.assertNotIn('env',args);self.assertNotIn('reference',args)
    def test_nonnegative_cost_predictions(self):
        pred=self.model.predict(np.zeros(14));self.assertTrue(np.isfinite(pred).all());self.assertTrue((pred[:,1:]>=0).all())
    def test_training_frozen_and_legacy_untouched(self):
        freeze()
        from exps.paper2_reward_validation.protocol import sha
        m=json.loads((PROJECT_ROOT/'exps/math_revision_20260925/manifest.json').read_text())
        for p,h in m['source_sha256'].items():self.assertEqual(sha(PROJECT_ROOT/p),h,p)

if __name__=='__main__':unittest.main()
