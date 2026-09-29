"""Additional offline invariants; synthetic fixtures are never empirical observations."""
import unittest,json
from copy import deepcopy
from exps.paper2_docred_v2.test_contracts import fixture,rule
from exps.paper2_docred_v2.environment import SourceRuleEnvironment
from exps.paper2_docred_v2.generation import compile_response

class ReplayChecks(unittest.TestCase):
    def test_acquisition_budget_and_deduplication(self):
        r,p=fixture()
        for s in p:p[s][0]['rules']=[rule(),rule()]
        e=SourceRuleEnvironment(r,p)
        for s in ['deletion','augmentation']:
            e.step('acquire_'+s);e.step('acquire_'+s)
        self.assertEqual(sum(e.acquired.values()),4);self.assertEqual(len(e.active),1)
        self.assertEqual(len(next(iter(e.active.values()))),2)
        self.assertFalse(any(e.mask()[:2]))
        with self.assertRaises(ValueError):e.step('acquire_deletion')
    def test_late_support_is_logged(self):
        r,p=fixture();p['deletion'][0]['rules']=[rule()];p['augmentation'][0]['rules']=[rule('supported')]
        e=SourceRuleEnvironment(r,p)
        while not e.mask()[2]:e.step('acquire_deletion')
        e.step('repair');found=[]
        for _ in range(2):found+=e.step('acquire_augmentation')[3]['late_permission_ids']
        self.assertEqual(found,['r']);self.assertEqual(len(e.records),1)
    def test_cross_document_target_rejected(self):
        r,p=fixture();p['deletion'][1]['rules']=[rule()]
        with self.assertRaises(ValueError):SourceRuleEnvironment(r,p)
    def test_coverage_initial_denominator(self):
        r,p=fixture();p['deletion'][0]['rules']=[rule()];e=SourceRuleEnvironment(r,p)
        while not e.mask()[2]:e.step('acquire_deletion')
        before=e.potentials()[1];e.step('repair');self.assertEqual(e.potentials()[1],before)
    def test_no_hypothetical_or_offset_evidence(self):
        r,_=fixture();d=dict(case_id='a',sents=[['original','text']])
        for evidence in [[],[dict(sentence_id=1,quote='original')],[dict(sentence_id=True,quote='original')],[dict(sentence_id=0,quote='hypothetical')]]:
            c=dict(family='source',record_id='r',verdict='contradicted',evidence=evidence)
            _,rules,_=compile_response(json.dumps(dict(rules=[c],supplementary_clauses=['hypothetical'])),d,r,{'P1':'relation'})
            self.assertFalse(rules)
    def test_combined_cap_and_empty_parse(self):
        r,_=fixture();d=dict(case_id='a',sents=[['original']]);c=dict(family='type',kind='allowed',pattern=['PER','P1','ORG'])
        ok,rules,rejected=compile_response(json.dumps(dict(rules=[c]*21)),d,r,{'P1':'relation'})
        self.assertTrue(ok);self.assertEqual(len(rules),20);self.assertEqual(rejected[0]['reason'],'candidate_cap')
        self.assertFalse(compile_response('not json',d,r,{'P1':'relation'})[0])
    def test_reset_reproducible(self):
        r,p=fixture();p['deletion'][0]['rules']=[rule()];e=SourceRuleEnvironment(r,p);before=e.observe()
        e.step('acquire_deletion');e.reset();self.assertEqual(e.observe(),before)

if __name__=='__main__':unittest.main()
