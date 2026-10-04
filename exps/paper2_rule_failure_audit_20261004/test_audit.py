"""Offline regression cases for candidate quarantine and loss attribution."""
from copy import deepcopy
import hashlib
import unittest
from exps.paper2_rule_failure_audit_20261004.audit import filter_packets, deletion_states, quote_checks
from exps.paper2_rule_feasibility_20261004.analyze import replay
from exps.paper2_rule_feasibility_20261004.test_pipeline import fixture, compiled


class AuditTests(unittest.TestCase):
    def test_quarantine_never_changes_original_or_support_rules(self):
        records, packets, _ = fixture()
        packets['deletion'][0]['rules'] = [compiled(), dict(family='type', kind='forbidden', pattern=['PER', 'P1', 'ORG']),
            dict(family='type', kind='allowed', pattern=['PER', 'P1', 'LOC'])]
        before = deepcopy(packets)
        filtered = filter_packets(packets, 'quarantine_both')
        self.assertEqual(packets, before)
        self.assertEqual(filtered['deletion'][0]['rules'], [before['deletion'][0]['rules'][2]])
        self.assertEqual(replay(records, filtered, 'acquire_then_repair', 1)['removed_ids'], [])

    def test_quote_provenance_and_comention_are_not_entailment(self):
        records, _, doc = fixture()
        text = ' '.join(doc['sents'][0])
        rule = compiled()
        rule['evidence'] = [dict(sentence_id=0, start=0, end=len(text), quote_sha256=hashlib.sha256(text.encode()).hexdigest())]
        result = quote_checks(doc, records[0], rule)[0]
        self.assertTrue(result['head_surface_in_quote'] and result['tail_surface_in_quote'])
        self.assertEqual(result['entails_contradiction'], 'not_determined_by_this_check')

    def test_source_attribution_and_redundant_type_rule(self):
        records, packets, _ = fixture()
        records[1]['object_type'] = 'LOC'
        packets['deletion'][0]['rules'] = [compiled()]
        actions = replay(records, packets, 'acquire_then_repair', 1)['actions']
        states, removed = deletion_states(records, packets, actions)
        self.assertEqual(removed, ['r'])
        self.assertFalse(states['r']['violation_without_source_contradicted'])
        packets['deletion'][0]['rules'].append(dict(family='type', kind='forbidden', pattern=['PER', 'P1', 'ORG']))
        states, _ = deletion_states(records, packets, actions)
        self.assertTrue(states['r']['violation_without_source_contradicted'])

    def test_support_conflict_still_abstains(self):
        records, packets, _ = fixture()
        packets['deletion'][0]['rules'] = [compiled()]
        support = compiled()
        support['verdict'] = 'supported'
        packets['augmentation'][0]['rules'] = [support]
        for variant in ['original', 'quarantine_type_forbidden', 'quarantine_source_contradicted', 'quarantine_both']:
            self.assertEqual(replay(records, filter_packets(packets, variant), 'acquire_then_repair', 1)['removed_ids'], [])

    def test_invalid_filter_cannot_silently_change_protocol(self):
        _, packets, _ = fixture()
        with self.assertRaises(ValueError):
            filter_packets(packets, 'protect_gold_ids')


if __name__ == '__main__':
    unittest.main()
