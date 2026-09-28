import unittest
from dataclasses import asdict
from exps.paper1_v2_ablation.study import Variant
from exps.math_revision_20260925.paper1.study import ReplayOptimizer
from content_enhancement.constraint_optimizer_v2 import TaskContext
class Tests(unittest.TestCase):
 def setUp(self):
  self.ctx=TaskContext(document_node='doc',allowed_relations=('field','second'))
  self.entities=[{'name':'doc'}];self.text='field: value\nsecond: other';self.graph=[{'head':'doc','relation':'field','tail':'value'}]
 def test_baseline_exact_current_runtime(self):
  for relative in [False,True]:
   a=Variant(self.ctx,'uniform_always',relative);b=ReplayOptimizer(self.ctx,'uniform_'+('relative' if relative else 'absolute'))
   self.assertEqual(a.optimize_and_apply(self.entities,self.graph,[],self.text),b.optimize_and_apply(self.entities,self.graph,[],self.text))
 def test_no_rule_preserves_assessment_but_disables_all_rule_actions(self):
  a=Variant(self.ctx,'uniform_always');b=Variant(self.ctx,'no_rule_candidates')
  self.assertEqual(asdict(a.assess(self.entities,self.graph,self.text)),asdict(b.assess(self.entities,self.graph,self.text)))
  self.assertTrue(b.source_field_candidates(self.text));self.assertEqual(b._violations_to_actions(b.assess(self.entities,self.graph,self.text),self.graph),[])
  out,applied,audit=b.optimize_and_apply(self.entities,self.graph,[],self.text)
  self.assertEqual(out,self.graph);self.assertEqual(applied,[]);self.assertEqual(audit['decisions'],[])
 def test_score_no_renormalization(self):
  a=Variant(self.ctx,'no_local_score');self.assertEqual(a.weights,{'S_iso':0,'S_red':0,'S_log':.25,'S_sem':.25})
 def test_version(self):self.assertEqual(Variant(self.ctx,'learned_trigger').router.scaler['feature_version'],'public-profile-v2')
if __name__=='__main__':unittest.main()
