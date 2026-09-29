import unittest
from exps.paper1_cuad.analyze import metrics,paired_difference


def t(rel,value):return dict(head='d',relation=rel,tail=value)


class Scoring(unittest.TestCase):
    def test_failure_counts_as_empty_and_loss(self):
        ref=[t('Document Name','A')]
        r=metrics([],ref,ref)
        self.assertEqual(r['f1'],0);self.assertEqual(r['lost_correct'],1)

    def test_unsupported_and_duplicate_values_are_not_dropped(self):
        ref=[t('Document Name','A')]
        pred=ref+[t('Document Name','B'),t('UNKNOWN','C')]
        self.assertEqual(metrics(pred,ref,ref)['f1'],.5)
        self.assertEqual(metrics(pred,ref,ref)['new_incorrect'],2)

    def test_whitespace_and_absence(self):
        r=metrics([t('Document Name',' A  B ')],[t('Document Name','A B')],[])
        self.assertEqual(r['f1'],1);self.assertEqual(r['raw_f1'],0);self.assertEqual(r['field_accuracy'],1)

    def test_null_contrast(self):
        r=paired_difference([.2,.5],[.2,.5])
        self.assertEqual(r['difference_pp'],0);self.assertEqual(r['ci95_pp'],[0.,0.]);self.assertEqual(r['p_sign_flip'],1)


if __name__=='__main__':unittest.main()
