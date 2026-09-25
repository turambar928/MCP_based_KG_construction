"""Offline regression tests for behavioral fixes, leakage, and legacy integrity."""
import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import numpy as np
from content_enhancement.constraint_optimizer_v2 import (MultiScaleConstraintOptimizer, TaskContext,
    CandidateAction, FphiRouter, RouterOutput, FEATURES, SCALES, public_profile)
from exps.math_revision_20260925.paper1.study import diagnosis,context,ReplayOptimizer
from exps.paper1_mechanism_audit.protocol import PublicInput,public_input
from exps.math_revision_20260925.paper2.environment import Paper2CoOptimizationEnv,KG,VALID_DETECTORS
from exps.math_revision_20260925.paper2.policy_study import graph
from exps.math_revision_20260925.paper2.rule_bridge import RuleBridge

class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.ctx=TaskContext(document_node='doc',allowed_relations=('company','total'))
        self.opt=MultiScaleConstraintOptimizer(task_context=self.ctx)
        self.triple={'head':'doc','relation':'company','tail':'ABC'}
    def test_empty_tail(self):
        inp=PublicInput('toy','toy','ABC','doc',('company',),())
        self.assertEqual(diagnosis(inp,[dict(self.triple,tail='')])['unsupported_indices'],[0])
        self.assertEqual(diagnosis(inp,[dict(self.triple,tail=' ')])['unsupported_indices'],[0])
    def test_hierarchy_direction_and_abstention(self):
        f=self.opt._hierarchy_reversal
        self.assertFalse(f('甲县','隶属于','乙省'))
        self.assertTrue(f('乙省','隶属于','甲县'))
        self.assertTrue(f('甲县','监管','乙省'))
        self.assertFalse(f('乙省','监管','甲县'))
        self.assertFalse(f('甲县','上级','乙省'))
        self.assertFalse(f('广西壮族自治区','管理','甲县'))
    def test_literal_not_dangling(self):
        p=self.opt.assess([{'name':'doc'}],[self.triple],'ABC')
        self.assertFalse(any(v['type']=='dangling_endpoint' for v in p.violations))
    def test_explicit_entity_universe(self):
        o=MultiScaleConstraintOptimizer(task_context=TaskContext(declared_entities=('doc',),entity_endpoints=('head','tail')))
        p=o.assess([{'name':'doc'}],[self.triple],'ABC')
        self.assertTrue(any(v['type']=='dangling_endpoint' for v in p.violations))
    def test_optional_not_missing(self):
        self.assertEqual(self.opt.source_field_candidates('company: ABC'),[self.triple])
        p=self.opt.assess([{'name':'doc'}],[self.triple],'company: ABC')
        self.assertFalse(any(v['type']=='evidence_supported_missing_field' for v in p.violations))
    def test_explicit_missing_and_ambiguous(self):
        p=self.opt.assess([{'name':'doc'}],[self.triple],'company: ABC; total: 120')
        self.assertEqual([v['triple']['relation'] for v in p.violations if v['type']=='evidence_supported_missing_field'],['total'])
        self.assertEqual(self.opt.source_field_candidates('total: 100; total: 120'),[])
    def test_candidates_bypass_no_violation_stop(self):
        rec=[{'triple':{'head':'doc','relation':'total','tail':'120'}}]
        _,_,audit=self.opt.optimize_and_apply([{'name':'doc'}],[self.triple],rec,'ABC 120')
        self.assertGreater(len(audit['decisions']),0)
        self.assertNotEqual(audit['stopped_reason'],'no_detected_violations')
    def test_empty_bundle_blocked(self):
        b=self.opt.assess([{'name':'doc'}],[self.triple],'ABC');a=copy.deepcopy(b);a.n_e=0
        c=CandidateAction('bundle',{}, {},'graph',.7)
        self.assertEqual(self.opt._check_constraints(b,a,c),(False,'destructive_empty_graph'))
    def test_context_does_not_leak_across_calls(self):
        self.opt.optimize_and_apply([],[],[],'',TaskContext(document_node='other'))
        self.assertEqual(self.opt.task_context,self.ctx)
    def test_version_rejects_legacy_weights(self):
        r=FphiRouter(str(ROOT/'exps/decision_network'))
        self.assertFalse(r.available)
        self.assertIn('incompatible',r.fallback_reason)
        p=self.opt.assess([],[],'')
        self.assertEqual(set(r.predict(p).pi.values()),{1/3})
    def test_corrupt_weights_fail_to_explicit_fallback(self):
        import shutil
        with tempfile.TemporaryDirectory() as folder:
            source=ROOT/'exps/math_revision_20260925/paper1/router'
            shutil.copy(source/'scaler.json',Path(folder)/'scaler.json')
            with np.load(source/'fphi_model.npz') as saved: params={k:saved[k] for k in saved.files}
            params['Ws']=np.full((16,3),np.nan)
            np.savez(Path(folder)/'fphi_model.npz',**params)
            router=FphiRouter(folder)
            self.assertFalse(router.available)
            self.assertEqual(router.fallback_reason,'invalid_weights')

    def test_shared_features_all_rows(self):
        import gzip,pandas as pd
        df=pd.read_csv(ROOT/'exps/math_revision_20260925/paper1/router/dataset.csv')
        with gzip.open(ROOT/'exps/math_revision_20260925/paper1/public_inputs.jsonl.gz','rt') as f:
            for i,line in enumerate(f):
                r=json.loads(line);ctx=TaskContext(r['required_document_node'],tuple(r['allowed_relations']))
                p=public_profile([{'name':ctx.document_node}],r['input_triples'],r['source_evidence'],ctx)
                np.testing.assert_allclose(p.fphi_vector(),df.loc[i,list(FEATURES)].to_numpy(float),atol=1e-10)
    def test_reference_values_do_not_change_features_or_decisions(self):
        with (ROOT/'exps/paper1_repair_benchmark/benchmark.jsonl').open() as f:c=json.loads(next(f))
        changed=copy.deepcopy(c)
        for t in changed['clean_triples']:t['tail']='counterfactual';t['relation']='oracle-only'
        changed['defects']=[]
        a=public_input(c,c['corrupted_triples']);b=public_input(changed,c['corrupted_triples'])
        self.assertEqual(a.payload(),b.payload())
        outputs=[]
        for inp in (a,b):
            opt=MultiScaleConstraintOptimizer(task_context=context(inp))
            outputs.append(opt.optimize_and_apply([{'name':inp.required_document_node}],list(inp.triples),[],inp.source_evidence))
        self.assertEqual(outputs[0],outputs[1])
    def test_relative_prior_is_zero_at_uniform(self):
        p=self.opt.assess([{'name':'doc'}],[self.triple],'ABC')
        c=CandidateAction('complete',self.triple,{},'entity',.7);r=RouterOutput(1.,dict.fromkeys(SCALES,1/3),'test')
        o=MultiScaleConstraintOptimizer(relative_prior=True)
        u,_,_,_=o._utility(p,p,c,r)
        self.assertAlmostEqual(u,-.35*.06+.02*.7)

class EnvironmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.clean=graph()
    def env(self,pairs):
        e=Paper2CoOptimizationEnv(self.clean,123)
        e.graph=KG({n:{'id':n,'name':n,'node_type':'Document'} for n in 'abcd'},
                   [{'start_id':h,'end_id':t,'relation_type':'MENTIONS'} for h,t in pairs])
        e.active_rules=set(VALID_DETECTORS);e.initial_defects=e.defect_counts()
        return e
    def test_new_identity_not_net_count(self):
        e=self.env([('a','b'),('b','c'),('d','missing')]);_,r,_,info=e.step(3)
        self.assertEqual(sum(info['before_defects'].values()),sum(info['defects'].values()))
        self.assertEqual(info['new_violations'],1)
        self.assertAlmostEqual(r,sum(info['reward_components'].values()))
    def test_aggregate_observation_not_markov(self):
        a=self.env([('a','b'),('b','c'),('d','missing')]);b=self.env([('a','b'),('c','d'),('a','missing')])
        np.testing.assert_array_equal(a.state(),b.state());np.testing.assert_array_equal(a.available_action_mask(),b.available_action_mask())
        sa,ra,_,ia=a.step(3);sb,rb,_,ib=b.step(3)
        self.assertNotEqual(ia['new_violations'],ib['new_violations']);self.assertNotEqual(ra,rb)
    def test_duplicate_identity_stable(self):
        e=self.env([('a','b'),('a','b'),('a','b'),('c','d')]);before=e.violation_identities();e.step(1)
        self.assertEqual(sum((e.violation_identities()-before).values()),0)
    def test_empty_graph_guard(self):
        e=self.env([('a','missing')]);_,_,done,info=e.step(3)
        self.assertTrue(done);self.assertEqual(info['termination_reason'],'destructive_empty_graph')
        self.assertEqual(len(e.graph.rels),1)
    def test_no_feasible_action_termination(self):
        e=self.env([('a','b'),('c','d')]);e.available_action_mask=lambda:np.zeros(8,dtype=bool)
        _,r,done,i=e.step(0);self.assertTrue(done);self.assertEqual(r,0);self.assertEqual(i['termination_reason'],'no_feasible_action')
    def test_rule_bridge_conflict_unsupported(self):
        e=RuleBridge([{'subject_type':'A','relation':'r','object_type':'B','triple_id':'x'}])
        e.acquire([{'candidate_id':'f','field':'type_conflict_rules_forbidden','value':['A','r','B']}])
        self.assertTrue(e.action_mask()['remove_forbidden'])
        e.acquire([{'candidate_id':'a','field':'type_conflict_rules_allowed','value':['A','r','B']},
                   {'candidate_id':'u','field':'unknown','value':'text'}])
        self.assertFalse(e.action_mask()['remove_forbidden']);self.assertEqual(e.repair(),[]);self.assertEqual(len(e.rejections),1)
    def test_rule_bridge_no_label_access(self):
        row={'subject_type':'A','relation':'r','object_type':'B','triple_id':'x'}
        entry={'candidate_id':'f','field':'type_conflict_rules_forbidden','value':['A','r','B']}
        a=RuleBridge([row]);b=RuleBridge([dict(row,expected_detection='anything')]);a.acquire([entry]);b.acquire([entry])
        self.assertEqual(a.scan(),b.scan());self.assertEqual(a.repair(),b.repair())

class FrozenTests(unittest.TestCase):
    def test_frozen_sources_unchanged(self):
        for rel,keys in [('exps/paper1_ablation_completion/manifest.json',['code_sha256','source_sha256']),
                         ('exps/paper2_offline_revision/policy_manifest.json',['sha256']),
                         ('exps/paper2_offline_revision/rule_manifest.json',['source_sha256'])]:
            manifest=json.loads((ROOT/rel).read_text())
            for k in keys:
                for path,digest in manifest[k].items():
                    self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest,path)

if __name__=='__main__':unittest.main()
