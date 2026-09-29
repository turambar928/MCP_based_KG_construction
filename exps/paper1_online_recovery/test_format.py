import unittest
from exps.paper1_online_recovery.analyze_reextraction import compatibility
class Tests(unittest.TestCase):
 def test_only_fence(self):
  raw='{"triples":[{"head":"d","relation":"r","tail":"v"}]}'
  self.assertEqual(compatibility('```json\n'+raw+'\n```')[:2],compatibility(raw)[:2])
 def test_prose_not_salvaged(self):self.assertEqual(compatibility('Answer:\n```json\n{"triples":[]}\n```')[1],'parse_error')
 def test_bad_schema_not_repaired(self):self.assertEqual(compatibility('```json\n{"triples":[{"h":"x"}]}\n```')[1],'parse_error')
 def test_multiple_fences_not_salvaged(self):self.assertEqual(compatibility('```json\n{"triples":[]}\n```\n```\n{}\n```')[1],'parse_error')
if __name__=='__main__':unittest.main()
