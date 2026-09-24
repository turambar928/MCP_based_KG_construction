import unittest
from exps.paper2_offline_revision.rule_study import compile_candidate,predict,label,score
class RuleTests(unittest.TestCase):
    def test_no_implicit_closed_world(self):
        case=dict(subject_type='a',relation='r',object_type='b',expected_detection='pass',triple_id='x')
        self.assertEqual(predict({('allowed',('x','r','y'))},case),(False,False,False))
        self.assertEqual(predict({('forbidden',('a','r','b'))},case),(True,False,False))
        self.assertEqual(predict({('forbidden',('a','r','b')),('allowed',('a','r','b'))},case),(False,True,True))
    def test_strict_compilation(self):
        self.assertEqual(compile_candidate('procedural_rules','text'),(None,'unsupported_family'))
        self.assertEqual(compile_candidate('type_conflict_rules_forbidden',['a','b']),(None,'malformed'))
        self.assertEqual(compile_candidate('type_conflict_rules_forbidden',['a','r','b'])[0],('forbidden',('a','r','b')))
    def test_labels_are_data_not_detector(self):
        c=dict(subject_type='a',relation='r',object_type='b',expected_detection='specialist_miss',triple_id='x')
        self.assertTrue(label(c));self.assertEqual(score(set(),[c])[0]['fn'],1)
if __name__=='__main__':unittest.main()
