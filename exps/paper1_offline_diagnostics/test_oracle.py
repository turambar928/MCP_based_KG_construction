import unittest
from exps.paper1_offline_diagnostics.analyze import proposal_oracle,key
class OracleTests(unittest.TestCase):
    def test_selects_good_relation_and_retains_correct_input(self):
        gold=[{'head':'d','relation':'r1','tail':'one'},{'head':'d','relation':'r2','tail':'two'}]
        initial=[gold[0],dict(gold[1],tail='wrong')]
        proposal=[dict(gold[0],tail='bad'),gold[1]]
        r=proposal_oracle(initial,proposal,gold)
        self.assertEqual(r['f1'],1);self.assertEqual(r['selected_actions'],1)
        self.assertEqual(set(map(key,r['triples'])),set(map(key,gold)))
    def test_empty_subset_and_no_reference_injection(self):
        gold=[{'head':'d','relation':'r','tail':'true'}]
        r=proposal_oracle(gold,[],gold);self.assertEqual(r['selected_actions'],0);self.assertEqual(r['f1'],1)
        r=proposal_oracle([],[],gold);self.assertEqual(r['triples'],[]);self.assertEqual(r['f1'],0)
    def test_runtime_duplicate_add_semantics(self):
        t={'head':'d','relation':'r','tail':'value'}
        r=proposal_oracle([],[t,t],[t,t])
        self.assertEqual(len(r['triples']),1);self.assertAlmostEqual(r['f1'],2/3)
if __name__=='__main__':unittest.main()
