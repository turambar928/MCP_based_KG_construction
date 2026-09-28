import unittest
from exps.paper1_online_recovery.run import MODEL,payload,strict_parse,identify
class RunnerTests(unittest.TestCase):
 def test_reject_other_models(self):
  for name in ['gpt-5.6-sol','claude-sonnet-5','Qwen3.8-27B-no-thinking']:
   with self.assertRaises(ValueError):payload({'request':{'model':name}},'reextraction')
 def test_payload_unmodified(self):
  p={'model':MODEL,'messages':[{'role':'user','content':'frozen'}],'max_tokens':4000}
  self.assertIs(payload({'request':p},'reextraction'),p)
 def test_parse_strict(self):
  for raw in ['not JSON','```json\n{"triples":[]}\n```','{"triples":[{"head":5,"relation":"r","tail":"v"}]}']:
   self.assertEqual(strict_parse(raw),([], 'parse_error'))
  self.assertEqual(strict_parse('{"triples":[]}'),([], 'ok'))
 def test_cohort_identity(self):
  self.assertNotEqual(identify({'case_id':'x','arm':'p0d0','cohort':'natural'},'ablation'),identify({'case_id':'x','arm':'p0d0','cohort':'controlled'},'ablation'))
if __name__=='__main__':unittest.main()
