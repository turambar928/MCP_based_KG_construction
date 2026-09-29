import unittest
from exps.paper2_scale_control.study import replicate,KG
class Tests(unittest.TestCase):
 def test_replica_identity(self):
  g=KG({'a':{'id':'a','node_type':'Document'},'b':{'id':'b','node_type':'Entity'}},[{'start_id':'a','relation_type':'MENTIONS','end_id':'b'}]);h=replicate(g,3)
  self.assertEqual(len(h.nodes),6);self.assertEqual(len(h.rels),3);self.assertEqual(len(g.nodes),2)
  for r in h.rels:self.assertIn(r['start_id'],h.nodes);self.assertIn(r['end_id'],h.nodes);self.assertEqual(r['start_id'].split(':')[0],r['end_id'].split(':')[0])
if __name__=='__main__':unittest.main()
