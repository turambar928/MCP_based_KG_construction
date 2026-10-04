"""Synthetic authority fixtures test enforcement, never empirical human labels."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from exps.paper2_rule_admission_20261004.admission import (
    VERSION, Registry, admit_packets, binding, digest)
from exps.paper2_rule_feasibility_20261004.test_pipeline import fixture
from exps.paper2_rule_feasibility_20261004.analyze import replay
from exps.paper2_docred_v2_round2.environment import SourceRuleEnvironment


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.records, self.packets, doc = fixture()
        self.documents = {'a': doc, 'b': dict(deepcopy(doc), case_id='b')}
        self.relations = {'P1': 'member', 'P2': 'other'}
        sentence = ' '.join(doc['sents'][0])
        self.rule = dict(family='source', verdict='contradicted', record_id='r', evidence=[
            dict(sentence_id=0, start=0, end=len(sentence), quote_sha256=sha256(sentence.encode()).hexdigest())])
        self.packets['deletion'][0]['rules'] = [self.rule]

    def bound(self, rule=None):
        p = self.packets['deletion'][0]
        return binding(p, rule or self.rule, self.documents['a'],
                       self.records, self.relations, self.documents)

    def registry(self, verdict='approve', kind='independent_review', more=None):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.tmp = Path(directory.name)
        artifact = dict(version=VERSION, source_id='synthetic-fixture', kind=kind,
            authority='SYNTHETIC UNIT TEST ONLY, not a real reviewer', decisions=[
                dict(binding=self.bound(), verdict=verdict, basis='Synthetic contract test', rationale='Exercise interface only')])
        if more:
            artifact['decisions'].append(dict(artifact['decisions'][0], verdict=more))
        data = json.dumps(artifact).encode()
        (self.tmp/'test.json').write_bytes(data)
        manifest = dict(version=VERSION, trusted_sources=[dict(source_id=artifact['source_id'], kind=kind,
                    path='test.json', sha256=sha256(data).hexdigest())])
        self.manifest = self.tmp/'registry.json'
        self.manifest.write_text(json.dumps(manifest))
        return Registry.load(self.manifest)

    def admit(self, registry=None, mode='validated'):
        return admit_packets(self.packets, self.documents, self.records, self.relations,
                             registry or Registry(), mode)

    def test_no_independent_evidence_has_no_deletion_authority(self):
        packets, rows = self.admit()
        self.assertTrue(rows[0]['grounded'])
        self.assertFalse(rows[0]['validated'])
        self.assertFalse(rows[0]['admitted'])
        self.assertEqual(replay(self.records, packets, 'acquire_then_repair', 1)['removed_ids'], [])

    def test_approved_synthetic_rule_changes_actual_repair(self):
        packets, rows = self.admit(self.registry())
        self.assertTrue(rows[0]['validated'])
        self.assertEqual(replay(self.records, packets, 'acquire_then_repair', 1)['removed_ids'], ['r'])

    def test_grounding_and_entity_comention_are_not_validation(self):
        packets, rows = self.admit(mode='grounded')
        self.assertTrue(rows[0]['admitted'])
        self.assertFalse(rows[0]['validated'])
        self.assertEqual(replay(self.records, packets, 'acquire_then_repair', 1)['removed_ids'], ['r'])

    def test_allow_and_support_do_not_earn_unvalidated_coverage(self):
        self.packets['deletion'][0]['rules'] = [dict(self.rule, verdict='supported'),
            dict(family='type', kind='allowed', pattern=['PER', 'P1', 'ORG'])]
        packets, _ = self.admit()
        env = SourceRuleEnvironment(self.records, packets)
        for action in ['acquire_deletion', 'acquire_deletion']:
            env.step(action)
        self.assertEqual(env.potentials()[1], 0)
        self.assertEqual(len(env.active), 0)

    def test_type_review_allows_general_pattern_not_gold_id_exception(self):
        self.rule = dict(family='type', kind='forbidden', pattern=['PER', 'P1', 'ORG'])
        self.packets['deletion'][0]['rules'] = [self.rule]
        self.records[1]['object_type'] = 'LOC'
        packets, rows = self.admit(self.registry(kind='trusted_schema_review'))
        self.assertTrue(rows[0]['admitted'])
        self.assertEqual(replay(self.records, packets, 'deletion_only', 1)['removed_ids'], ['r'])

    def test_schema_authority_cannot_certify_source_semantics(self):
        _, rows = self.admit(self.registry(kind='trusted_schema_review'))
        self.assertFalse(rows[0]['admitted'])

    def test_reject_uncertain_and_conflicting_review_abstain(self):
        for verdict, more in [('reject', None), ('uncertain', None), ('approve', 'reject'), ('approve', 'uncertain')]:
            with self.subTest(verdict=verdict, more=more):
                _, rows = self.admit(self.registry(verdict, more=more))
                self.assertFalse(rows[0]['admitted'])

    def test_quote_hash_and_invalid_offsets_reject_even_with_approval(self):
        for field, value in [('quote_sha256', '0'*64), ('start', -1), ('end', 999), ('sentence_id', True)]:
            original = deepcopy(self.rule)
            self.rule['evidence'][0][field] = value
            _, rows = self.admit(self.registry())
            self.assertFalse(rows[0]['grounded'])
            self.assertFalse(rows[0]['admitted'])
            self.rule.clear(); self.rule.update(original)

    def test_source_content_change_invalidates_attestation(self):
        registry = self.registry()
        self.documents['a']['sents'].append(['Additional', 'sentence'])
        _, rows = self.admit(registry)
        self.assertTrue(rows[0]['grounded'])
        self.assertFalse(rows[0]['admitted'])

    def test_other_document_change_invalidates_episode_scoped_approval(self):
        registry = self.registry()
        self.documents['b']['sents'].append(['Changed', 'partner', 'document'])
        self.assertFalse(self.admit(registry)[1][0]['admitted'])

    def test_response_change_invalidates_attestation(self):
        registry = self.registry()
        self.packets['deletion'][0]['provenance']['response_sha256'] = 'changed'
        self.assertFalse(self.admit(registry)[1][0]['admitted'])

    def test_record_relation_change_invalidates_attestation(self):
        registry = self.registry()
        self.records[0]['relation'] = 'P2'
        self.assertFalse(self.admit(registry)[1][0]['admitted'])

    def test_relation_meaning_change_invalidates_attestation(self):
        registry = self.registry()
        self.relations['P1'] = 'a different meaning'
        self.assertFalse(self.admit(registry)[1][0]['admitted'])

    def test_cross_document_target_rejected(self):
        self.rule['record_id'] = 's'
        self.assertFalse(self.admit(self.registry())[1][0]['grounded'])

    def test_model_cannot_self_approve(self):
        self.rule['validated'] = True
        self.assertFalse(self.admit()[1][0]['admitted'])
        self.rule.pop('validated')
        self.packets['deletion'][0]['validation'] = {'approved': True}
        with self.assertRaises(ValueError):
            self.admit()

    def test_reference_labels_cannot_enter_public_input(self):
        self.records[0]['is_gold'] = True
        with self.assertRaises(ValueError):
            self.admit()

    def test_approved_type_rule_still_cannot_clear_entire_graph(self):
        self.rule = dict(family='type', kind='forbidden', pattern=['PER', 'P1', 'ORG'])
        self.packets['deletion'][0]['rules'] = [self.rule]
        packets, rows = self.admit(self.registry(kind='trusted_schema_review'))
        self.assertTrue(rows[0]['admitted'])
        self.assertEqual(replay(self.records, packets, 'acquire_then_repair', 1)['removed_ids'], [])

    def test_two_approved_conflicting_source_rules_still_abstain(self):
        self.registry()
        support = dict(deepcopy(self.rule), verdict='supported')
        p = self.packets['augmentation'][0]
        p['rules'] = [support]
        artifact = json.loads((self.tmp/'test.json').read_text())
        artifact['decisions'].append(dict(binding=binding(p, support, self.documents['a'],
            self.records, self.relations, self.documents), verdict='approve',
            basis='Synthetic conflict test', rationale='Not a real annotation'))
        data = json.dumps(artifact).encode()
        (self.tmp/'test.json').write_bytes(data)
        manifest = json.loads(self.manifest.read_text())
        manifest['trusted_sources'][0]['sha256'] = sha256(data).hexdigest()
        self.manifest.write_text(json.dumps(manifest))
        packets, rows = self.admit(Registry.load(self.manifest))
        self.assertEqual(sum(r['validated'] for r in rows), 2)
        self.assertEqual(replay(self.records, packets, 'acquire_then_repair', 1)['removed_ids'], [])

    def test_no_mutation_and_deterministic_output(self):
        before = deepcopy((self.records, self.packets, self.documents))
        self.assertEqual(self.admit(), self.admit())
        self.assertEqual((self.records, self.packets, self.documents), before)

    def test_changed_trust_artifact_rejected(self):
        self.registry()
        with (self.tmp/'test.json').open('a') as f:
            f.write(' ')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            Registry.load(self.manifest)

    def test_path_escape_rejected(self):
        self.registry()
        obj = json.loads(self.manifest.read_text())
        obj['trusted_sources'][0]['path'] = '../other.json'
        self.manifest.write_text(json.dumps(obj))
        with self.assertRaises(ValueError):
            Registry.load(self.manifest)

    def test_duplicate_record_and_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            self.admit(mode='protect_reference')
        self.records.append(deepcopy(self.records[0]))
        with self.assertRaises(ValueError):
            self.admit()


if __name__ == '__main__':
    unittest.main()
