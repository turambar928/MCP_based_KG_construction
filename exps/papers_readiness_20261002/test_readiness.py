"""Synthetic checks only: contract boundaries, exhaustive replay and human input."""
import json
from pathlib import Path
import tempfile
import unittest
from jsonschema import Draft202012Validator, ValidationError

from exps.papers_readiness_20261002.output_contract import schema, examples, compile_response
from exps.papers_readiness_20261002.diagnose_loop import enumerate_paths, score
from exps.paper1_human_review.process_returns import read_return
from exps.papers_readiness_20261002.human_effects import validate


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.doc = dict(case_id='doc', sents=[['Alice wrote Book A.'], ['Bob did not write Book A.']])
        self.records = [dict(record_id='synthetic:' + str(i), source_document_id='doc') for i in range(3)]
        self.validator = Draft202012Validator(schema())

    def test_synthetic_examples_and_empty(self):
        for x in examples():
            self.validator.validate(x)
            ok, rules, rejects = compile_response(json.dumps(x), self.doc, self.records, {'P50': 'author'})
            self.assertTrue(ok)
            if x['rules'] and x['rules'][0].get('verdict') == 'insufficient':
                self.assertEqual(rejects[0]['reason'], 'insufficient_abstention')
                self.assertFalse(rules)
            else:
                self.assertFalse(rejects)

    def test_illegal_enum_is_not_guessed(self):
        x = examples()[0]
        x['rules'][0]['kind'] = 'allowed or forbidden'
        with self.assertRaises(ValidationError):
            self.validator.validate(x)
        ok, rules, rejected = compile_response(json.dumps(x), self.doc, self.records, {'P50': 'author'})
        self.assertTrue(ok)
        self.assertEqual(rules, [])
        self.assertEqual(rejected[0]['reason'], 'invalid_kind')

    def test_candidate_cap_and_truncation(self):
        x = examples()[0]
        x['rules'] *= 21
        with self.assertRaises(ValidationError):
            self.validator.validate(x)
        ok, rules, rejected = compile_response(json.dumps(x), self.doc, self.records, {'P50': 'author'})
        self.assertTrue(ok)
        self.assertEqual(len(rules), 20)
        self.assertEqual(rejected[0]['reason'], 'candidate_cap')
        self.assertFalse(compile_response('{"rules":[', self.doc, self.records, {})[0])

    def test_schema_cannot_replace_provenance(self):
        x = examples()[2]
        x['rules'][0]['evidence'][0]['quote'] = 'Hypothetical invented sentence.'
        self.validator.validate(x)
        ok, rules, rejected = compile_response(json.dumps(x), self.doc, self.records, {'P50': 'author'})
        self.assertTrue(ok)
        self.assertFalse(rules)
        self.assertEqual(rejected[0]['reason'], 'quote_not_in_original')


class EnumerationTests(unittest.TestCase):
    def test_late_permission_requires_order_sensitive_search(self):
        records = [dict(record_id='r' + str(i), source_document_id='d' + str(i),
                        head_entity_id='h', tail_entity_id='t', subject_type='PER',
                        relation='P50' if i == 0 else 'P1', object_type='PER', missing_endpoint=False)
                   for i in range(2)]
        queues = {s: [dict(packet_id=s + str(i), source_document_id='d' + str(i), strategy=s,
                          parse_success=True, rules=[]) for i in range(2)] for s in ('deletion', 'augmentation')}
        queues['deletion'][0]['rules'] = [dict(family='type', kind='forbidden', pattern=['PER', 'P50', 'PER'])]
        queues['augmentation'][0]['rules'] = [dict(family='type', kind='allowed', pattern=['PER', 'P50', 'PER'])]
        paths = enumerate_paths(records, queues)
        self.assertTrue(any(p['removed_ids'] == ['r0'] for p in paths))
        self.assertTrue(any(not p['removed_ids'] and p['acquisitions'] == 4 for p in paths))
        self.assertTrue(any(p['late_permissions'] for p in paths))
        self.assertTrue(all(len(p['actions']) <= 10 for p in paths))
        self.assertEqual(len({tuple(p['actions']) for p in paths}), len(paths))


class HumanReturnTests(unittest.TestCase):
    def test_effects_are_not_inferred_from_blank_labels(self):
        row = dict(task='E', item_id='synthetic', semantic_effect='', evidence_notes='')
        with self.assertRaises(ValueError): validate([row], {('E', 'synthetic')})
        row.update(semantic_effect='uncertain', evidence_notes='Synthetic fixture, no actual human label.')
        self.assertEqual(validate([row], {('E', 'synthetic')})['uncertain'], 1)

    def read(self, labels, who='A', version='2026-09-21-v1'):
        public = {('E', 'synthetic'): {}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'return.json'
            path.write_text(json.dumps(dict(annotator=who, version=version, labels=labels)))
            return read_return(path, 'A', public)

    def test_uncertain_requires_reason(self):
        row = dict(task='E', item_id='synthetic', is_error='U', repair_acceptable='U', notes='')
        with self.assertRaises(ValueError):
            self.read([row])
        row['notes'] = 'Synthetic insufficient context; not a human result.'
        self.assertEqual(self.read([row])[('E', 'synthetic')]['is_error'], 'U')

    def test_blank_duplicate_identity_and_version_rejected(self):
        row = dict(task='E', item_id='synthetic', is_error='', repair_acceptable='', notes='')
        with self.assertRaises(ValueError): self.read([row])
        row.update(is_error='1', repair_acceptable='1')
        for labels, who, version in [([row, row], 'A', '2026-09-21-v1'),
                                     ([row], 'B', '2026-09-21-v1'), ([row], 'A', 'wrong')]:
            with self.assertRaises(ValueError): self.read(labels, who, version)


if __name__ == '__main__':
    unittest.main()
