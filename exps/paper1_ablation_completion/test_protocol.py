"""Behavioral checks for matched inputs, controls and redundant gate checks."""
import json,unittest
from dataclasses import replace
from exps.paper1_ablation_completion.protocol import *
from exps.paper1_mechanism_audit.protocol import gate,read_jsonl,public_input
from exps.paper1_receipt_followup.protocol import filter_response
from exps.paper1_external_receipts.run import input_object
class ProtocolTests(unittest.TestCase):
    def test_factorial_and_filter_equivalence(self):
        rows=read_jsonl(ROOT/'exps/paper1_repair_benchmark/benchmark.jsonl')
        for c in rows[:100]:
            inp=public_input(c,c['corrupted_triples']);payloads={a:json.loads(factorial_prompt(inp,a)[1]) for a in FACTORIAL_ARMS}
            for p in [0,1]:
                a=payloads[f'p{p}d0'];b=dict(payloads[f'p{p}d1']);b.pop('diagnostic_context');self.assertEqual(a,b)
            a=dict(payloads['p0d0']);b=dict(payloads['p1d0']);a.pop('input_triples');b.pop('input_triples');self.assertEqual(a,b)
            self.assertEqual(filter_candidates(inp,list(inp.triples))[0],gate(inp,list(inp.triples))[0])
            changed=dict(c);changed['clean_triples']=[dict(t,tail='HIDDEN REFERENCE CHANGED') for t in c['clean_triples']]
            self.assertEqual(factorial_prompt(inp,'p1d1'),factorial_prompt(public_input(changed,c['corrupted_triples']),'p1d1'))
    def test_receipt_controls(self):
        folder=ROOT/'exps/paper1_receipt_followup/test';ext={r['case_id']:r for r in read_jsonl(folder/'extraction.jsonl')}
        for r in read_jsonl(folder/'inputs.jsonl'):
            triples=ext[r['case_id']]['triples'];ps={a:json.loads(index_prompt(r,triples,a)[1]) for a in INDEX_ARMS}
            full=ps['full'];random=ps['random'];self.assertEqual(random,json.loads(index_prompt(r,triples,'random')[1]))
            for field,f in full['field_evidence_index'].items():
                x=random['field_evidence_index'][field]
                self.assertEqual(len(f['anchor_lines']),len(x['anchor_lines']));self.assertEqual(len(f['nearby_lines']),len(x['nearby_lines']))
                for anchor in x['anchors']:self.assertEqual(anchor['text'],r['source_lines'][anchor['line']-1])
            for arm in ['simple','full']:
                expected=dict(ps[arm]);expected.pop('field_definitions');self.assertEqual(expected,ps['no_def_'+arm])
            inp=input_object(r,triples)
            self.assertEqual(filter_candidates(inp,triples,whitespace=True)[0],filter_response(r,triples)[0])
    def test_duplicate_cardinality_interaction_and_scan_order(self):
        t={'head':'doc','relation':'r','tail':'supported'};inp=PublicInput('id','test','supported extra','doc',('r',),(t,))
        self.assertEqual(len(filter_candidates(inp,[t,t],('duplicate',))[0]),1)
        self.assertEqual(len(filter_candidates(inp,[t,t],('cardinality',))[0]),1)
        self.assertEqual(len(filter_candidates(inp,[t,t],('duplicate','cardinality'))[0]),2)
        bad=dict(t,tail='absent')
        self.assertEqual(filter_candidates(inp,[bad,t])[0],[t])
        self.assertEqual(filter_candidates(inp,[bad,t],('support',))[0],[bad])
    def test_optimizer_switches(self):
        from exps.paper1_ablation_completion.offline import VariantOptimizer
        base=VariantOptimizer('uniform_always');no=VariantOptimizer('no_source_score')
        self.assertEqual(no.weights['S_sem'],0);self.assertEqual(no.weights['S_log'],base.weights['S_log'])
        self.assertNotIn('S_sem',no.lower_bounds);self.assertTrue(no.enforce_upper_bounds)
        self.assertEqual(VariantOptimizer('no_profile_bounds').lower_bounds,{})
        self.assertEqual(VariantOptimizer('single_step').max_iterations,1)
if __name__=='__main__':unittest.main()
