import unittest
from exps.paper1_index_localization.analyze import locate,classify
class Tests(unittest.TestCase):
 def test_no_noncontiguous_join(self):self.assertEqual(locate(['A','unrelated','B'],'A B'),[])
 def test_complete_span_required(self):
  spans=locate(['A','B'],'A B');self.assertEqual(spans,[[1,2]]);self.assertEqual(classify(spans,[1]),'outside_index');self.assertEqual(classify(spans,[1,2]),'indexed')
 def test_any_real_occurrence(self):self.assertEqual(classify(locate(['A','B','A'],'A'),[3]),'indexed')
 def test_normalization(self):
  self.assertEqual(locate([' A  B\t C '],'A B C'),[[1]]);self.assertEqual(locate(['A B'],'a b'),[])
 def test_empty(self):self.assertEqual(classify(locate(['x'],''),[1]),'not_source_matched')
if __name__=='__main__':unittest.main()
