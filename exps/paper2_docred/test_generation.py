import json
import unittest
from exps.paper2_docred.generation import request,compile_response


class Compilation(unittest.TestCase):
    def test_vocab_cap_and_parse(self):
        rule=dict(kind='forbidden',pattern=['PER','P19','ORG'])
        raw=json.dumps(dict(rules=[rule]*21+[dict(kind='allowed',pattern=['ALIEN','P19','ORG'])]))
        ok,r,rejections=compile_response(raw,{'P19':'place of birth'})
        self.assertTrue(ok);self.assertEqual(len(r),20);self.assertEqual(len(rejections),2)
        self.assertFalse(compile_response('{"rules":null}',{})[0])

    def test_label_free_both_strategies(self):
        doc=dict(case_id='d',sents=[['John','was','born','here','.']],entities=[],labels='SECRET')
        for strategy in ['deletion','augmentation']:
            p=request(doc,strategy,{'P19':'place of birth'})
            self.assertNotIn('SECRET',json.dumps(p));self.assertEqual(p['model'],'google/gemma-4-26B-A4B-it')
            self.assertIn('Both allowed and forbidden',p['messages'][0]['content'])


if __name__=='__main__':unittest.main()
