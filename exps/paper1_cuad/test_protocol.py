import unittest
from exps.paper1_cuad.protocol import task, parse, evidence_index


class PublicProtocol(unittest.TestCase):
    def test_fences_ids_and_failures(self):
        raw='```json\n{"triples":[{"head":"wrong","relation":"Agreement Date","tail":"today"}]}\n```'
        triples,status=parse(raw,'doc')
        self.assertEqual(status,'ok');self.assertEqual(triples[0]['head'],'doc')
        for raw in ['{"triples":[3]}','{"triples":{}}','{"triples":null}','explanation {"triples":[]}']:
            self.assertEqual(parse(raw,'doc'),([], 'parse_error'))

    def test_no_reference_leakage(self):
        row=dict(case_id='doc',source='agreement made today',reference_triples=['SECRET'])
        a=task(row,'extract_index');self.assertNotIn('SECRET',str(a))
        self.assertNotIn('input_triples',a['request']['messages'][1]['content'])
        with self.assertRaises(ValueError):task(row,'repair_index')

    def test_index_offsets_preserve_source(self):
        source='x'*200+' Effective date today. Governing law: France.'+'y'*400
        for spans in evidence_index(source).values():
            for span in spans:self.assertEqual(span['text'],source[span['start']:span['end']])


if __name__=='__main__':unittest.main()
