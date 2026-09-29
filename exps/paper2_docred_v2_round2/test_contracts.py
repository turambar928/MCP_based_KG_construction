import unittest,json
from copy import deepcopy
from exps.paper2_docred_v2_round2.environment import SourceRuleEnvironment,ACTIONS
from exps.paper2_docred_v2_round2.generation import compile_response


def fixture():
    records=[dict(record_id=x,subject_type='PER',relation='P1',object_type='ORG',source_document_id=d,head_entity_id='0',tail_entity_id='1') for x,d in [('r','a'),('s','b')]]
    packets={s:[dict(packet_id=d+s,source_document_id=d,strategy=s,parse_success=True,rules=[],provenance={},rejections=[]) for d in ['a','b']] for s in ['deletion','augmentation']}
    return records,packets

def rule(verdict='contradicted'):
    return dict(family='source',verdict=verdict,record_id='r',evidence=[dict(sentence_id=0,start=0,end=1,quote_sha256='0'*64)])

class Contracts(unittest.TestCase):
    def env(self,mode='fixed_rule'):
        r,p=fixture();p['deletion'][0]['rules']=[rule()];return SourceRuleEnvironment(r,p,mode)
    def acquire_target(self,e):
        rewards=[]
        while not e.scan()['r']['violation']:
            rewards.append(e.step('acquire_deletion')[1])
        return rewards
    def test_fixed_reward(self):
        e=self.env();rewards=self.acquire_target(e);last=e.events[-1]
        self.assertAlmostEqual(rewards[-1],.246);self.assertEqual(last['edit_created_ids'],[])
        self.assertEqual(last['acquisition_revealed_ids'],['r']);self.assertEqual(last['fixed_rule_graph_delta'],0)
        self.assertAlmostEqual(e.step('repair')[1],.24998)
        self.assertAlmostEqual(.246+.95*.24998,.483481)
    def test_legacy_counterexample(self):
        e=self.env('legacy');self.assertAlmostEqual(self.acquire_target(e)[-1],-.504)
        self.assertAlmostEqual(-.504+.95*e.step('repair')[1],-.266519)
    def test_source_over_type_compatibility(self):
        e=self.env();self.acquire_target(e);e.active[('type','allowed','PER','P1','ORG')]={'test'}
        self.assertTrue(e.scan()['r']['violation'])
    def test_source_conflict_abstains(self):
        e=self.env();self.acquire_target(e);e.active[('source','supported','r')]={'test'}
        self.assertTrue(e.scan()['r']['conflict']);self.assertFalse(e.scan()['r']['violation'])
    def test_supported_vs_forbidden_abstains(self):
        r,p=fixture();e=SourceRuleEnvironment(r,p);e.active={('source','supported','r'):{'x'},('type','forbidden','PER','P1','ORG'):{'y'}}
        self.assertFalse(e.scan()['r']['violation']);self.assertTrue(e.scan()['r']['conflict'])
    def test_terminal_and_emptying(self):
        r,p=fixture();e=SourceRuleEnvironment(r,p);e.active={('type','forbidden','PER','P1','ORG'):{'x'}}
        self.assertFalse(e.mask()[2]);e.step('stop');self.assertFalse(any(e.mask()))
        with self.assertRaises(ValueError):e.step('stop')
    def test_labels_and_unseen_hidden(self):
        r,p=fixture();e=SourceRuleEnvironment(r,p);p['deletion'][0]['rules']=[rule()]
        self.assertEqual(e.observe(),SourceRuleEnvironment(r,p).observe())
        r[0]['gold']=True
        with self.assertRaises(ValueError):SourceRuleEnvironment(r,p)
    def test_empty_input(self):
        _,p=fixture();e=SourceRuleEnvironment([],p);self.assertEqual(len(e.observe()['features']),14);self.assertFalse(e.mask()[2])
    def test_quote_compiler(self):
        records,_=fixture();doc=dict(case_id='a',sents=[['Alice','joined','Acme','.']])
        candidate=dict(family='source',record_id='r',verdict='contradicted',evidence=[dict(sentence_id=0,quote='joined Acme')])
        ok,r,_=compile_response(json.dumps(dict(rules=[candidate])),doc,records,{'P1':'member'})
        self.assertTrue(ok);self.assertEqual(r[0]['evidence'][0]['start'],6)
        for change,reason in [({'record_id':'s'},'target_outside_document'),({'verdict':'insufficient'},'insufficient_abstention'),({'evidence':[dict(sentence_id=0,quote='hypothetical')]},'quote_not_in_original')]:
            c=deepcopy(candidate);c.update(change);ok,r,rejected=compile_response(json.dumps(dict(rules=[c])),doc,records,{'P1':'member'})
            self.assertEqual(r,[]);self.assertEqual(rejected[0]['reason'],reason)

if __name__=='__main__':unittest.main()
