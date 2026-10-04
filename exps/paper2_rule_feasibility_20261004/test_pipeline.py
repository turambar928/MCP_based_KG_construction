"""Synthetic and mocked offline checks; never call a model or write study results."""
from copy import deepcopy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx

from exps.paper2_rule_feasibility_20261004.common import MODEL, POLICIES, digest, read_events, append_event, write_once
from exps.paper2_rule_feasibility_20261004.generation import compile_response, request, strict_json
from exps.paper2_rule_feasibility_20261004.prepare import select_pairs, construct
from exps.paper2_rule_feasibility_20261004.runner import transport, collect_with, states, recover
from exps.paper2_rule_feasibility_20261004.analyze import replay, assess
from exps.papers_readiness_20261002.diagnose_loop import enumerate_paths


def fixture():
    records = [dict(record_id=x, subject_type='PER', relation='P1', object_type='ORG',
        source_document_id=d, head_entity_id='0', tail_entity_id='1') for x, d in [('r', 'a'), ('s', 'b')]]
    packets = {s: [dict(packet_id=d+s, source_document_id=d, strategy=s,
        parse_success=True, rules=[], provenance={}, rejections=[]) for d in ['a', 'b']]
        for s in ['deletion', 'augmentation']}
    doc = dict(case_id='a', sents=[['Alice', 'joined', 'Acme', '.']], entities=[
        dict(entity_id='0', type='PER', mentions=[dict(name='Alice', sent_id=0, pos=[0, 1])]),
        dict(entity_id='1', type='ORG', mentions=[dict(name='Acme', sent_id=0, pos=[2, 3])])])
    return records, packets, doc


def candidate(**changes):
    r = dict(family='source', record_id='r', verdict='contradicted',
             evidence=[dict(sentence_id=0, quote='joined Acme')])
    r.update(changes)
    return r


def compiled():
    return dict(family='source', verdict='contradicted', record_id='r',
                evidence=[dict(sentence_id=0, start=6, end=17, quote_sha256='0'*64)])


def body(rules=None):
    return dict(supplementary_clauses=[], rules=[] if rules is None else rules)


class ContractTests(unittest.TestCase):
    def check(self, obj):
        records, _, doc = fixture()
        return compile_response(json.dumps(obj), doc, records, {'P1': 'member'})

    def test_empty_and_fence(self):
        self.assertEqual(self.check(body()), (True, [], []))
        self.assertEqual(strict_json('```json\n' + json.dumps(body()) + '\n```'), body())

    def test_duplicate_and_nonfinite_and_extra_prose(self):
        for text in ['{"rules":[],"rules":[]}', '{"x":NaN}', 'prefix ```json\n{}\n```']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                strict_json(text)

    def test_schema_rejects_entire_mixed_response(self):
        bad = dict(family='type', kind='allowed|forbidden', pattern=['PER', 'P1', 'ORG'])
        ok, rules, rejected = self.check(body([candidate(), bad]))
        self.assertFalse(ok)
        self.assertEqual(rules, [])
        self.assertEqual(rejected[0]['reason'], 'schema_error')

    def test_caps_and_missing_fields(self):
        for obj in [body([candidate()] * 21), dict(rules=[]), dict(body(), supplementary_clauses=['x']*4)]:
            self.assertFalse(self.check(obj)[0])

    def test_provenance_not_truth_and_rejections(self):
        # Exact quote passes even though it does not establish contradiction.
        ok, rules, _ = self.check(body([candidate()]))
        self.assertTrue(ok)
        self.assertEqual(rules[0]['evidence'][0]['start'], 6)
        for changes, reason in [({'record_id': 's'}, 'target_outside_document'),
                ({'verdict': 'insufficient', 'evidence': []}, 'insufficient_abstention'),
                ({'evidence': [dict(sentence_id=0, quote='invented')]}, 'quote_not_in_original')]:
            ok, rules, rejected = self.check(body([candidate(**changes)]))
            self.assertTrue(ok)
            self.assertEqual(rules, [])
            self.assertEqual(rejected[0]['reason'], reason)

    def test_unknown_vocabulary(self):
        ok, rules, rejected = self.check(body([dict(family='type', kind='forbidden', pattern=['PER', 'UNKNOWN', 'ORG'])]))
        self.assertTrue(ok)
        self.assertFalse(rules)
        self.assertEqual(rejected[0]['reason'], 'unknown_vocabulary')

    def test_prompt_has_only_public_inputs(self):
        records, _, doc = fixture()
        for arm in ('deletion', 'augmentation'):
            p = request(doc, arm, {'P1': 'member'}, records[:1])
            self.assertEqual(p['model'], MODEL)
            self.assertNotIn('allowed|forbidden', json.dumps(p))
            public = json.loads(p['messages'][1]['content'])
            self.assertIn('output_schema', public)
            self.assertIn('original_sentences', public)
            self.assertFalse({'reference', 'injected', 'condition', 'gold'} & set(public))


class PreparationTests(unittest.TestCase):
    def test_selection_order_and_exclusions(self):
        pairs = [[str(2*i), str(2*i+1)] for i in range(12)]
        self.assertEqual(select_pairs(pairs, {'0', '23'}), pairs[1:11])
        with self.assertRaises(ValueError):
            select_pairs(pairs, {'0', '2', '4'})
        with self.assertRaises(ValueError):
            select_pairs([['a', 'b']] * 10, set())

    def test_construction_determinism_and_separation(self):
        _, _, doc = fixture()
        docs = {c: dict(doc, case_id=c) for c in ['a', 'b']}
        refs = {c: dict(labels=[dict(h=0, r='P1', t=1)]) for c in docs}
        args = ([['a', 'b']], docs, refs, {'P1': 'member', 'P2': 'other'})
        public, scorer = construct(*args)
        self.assertEqual((public, scorer), construct(*args))
        self.assertEqual(scorer[0]['injected'], [])
        self.assertEqual(len(scorer[1]['injected']), 1)
        for x in public:
            self.assertEqual(set(x), {'document', 'records'})
            self.assertTrue(all(not {'gold', 'condition', 'injected'} & set(r) for r in x['records']))

    def test_immutable_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'f.json'
            write_once(p, {'a': 1})
            write_once(p, {'a': 1})
            with self.assertRaises(ValueError):
                write_once(p, {'a': 2})


class TransportTests(unittest.TestCase):
    def send(self, handler, payload=None):
        with httpx.Client(transport=httpx.MockTransport(handler), trust_env=False) as client:
            return transport(payload or dict(model=MODEL), ('synthetic-secret', 'http://example.invalid/v1'), client)

    def response(self, model=MODEL, finish='stop'):
        return httpx.Response(200, json=dict(model=model, choices=[dict(finish_reason=finish, message=dict(content=json.dumps(body())))], usage=dict(total_tokens=3)))

    def test_forbidden_models_never_dispatched(self):
        for model in ['gpt-6-astra', 'claude-sonnet-5', 'Qwen3.8-27B']:
            with self.assertRaises(ValueError):
                self.send(lambda _: self.fail('network called'), dict(model=model))

    def test_model_mismatch_and_incomplete(self):
        self.assertEqual(self.send(lambda _: self.response('gpt-6-astra'))['status'], 'model_mismatch')
        result = self.send(lambda _: self.response(finish='length'))
        self.assertEqual(result['status'], 'incomplete_output')
        self.assertFalse(result['retryable'])
        self.assertTrue(result['raw_response'])

    def test_http_and_exception_redaction(self):
        self.assertTrue(self.send(lambda _: httpx.Response(503))['retryable'])
        self.assertFalse(self.send(lambda _: httpx.Response(401))['retryable'])
        def fail(request):
            raise httpx.ConnectError('synthetic-secret', request=request)
        result = self.send(fail)
        self.assertTrue(result['retryable'])
        self.assertNotIn('synthetic-secret', json.dumps(result))


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.journal = Path(self.temp.name) / 'journal.jsonl'
        self.tasks = [dict(task_id=str(i), request=dict(model=MODEL, synthetic_id=i)) for i in range(3)]

    def run_collect(self, send, tasks=None):
        with contextlib.redirect_stdout(io.StringIO()):
            return collect_with(tasks or self.tasks, self.journal, send, sleep=lambda _: None)

    def test_retry_count_and_resume_no_duplicates(self):
        replies = iter([dict(status='transport_error', retryable=True), dict(status='ok', retryable=False, raw_response='{}')])
        rows = self.run_collect(lambda _: next(replies), self.tasks[:1])
        self.assertEqual(rows['0']['outcome']['observed_request_attempts'], 2)
        self.run_collect(lambda _: self.fail('resent'), self.tasks[:1])

    def test_outage_stops_before_third_task(self):
        with self.assertRaises(RuntimeError):
            self.run_collect(lambda _: dict(status='transport_error', retryable=True))
        rows = states(read_events(self.journal), self.tasks)
        self.assertEqual(set(rows), {'0', '1'})
        self.assertEqual(sum(len(r['finished']) for r in rows.values()), 4)

    def test_crash_after_dispatch_not_resent(self):
        def crash(_):
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.run_collect(crash, self.tasks[:1])
        rows = self.run_collect(lambda _: self.fail('uncertain request resent'), self.tasks[:1])
        self.assertEqual(rows['0']['outcome']['status'], 'interrupted')
        self.assertEqual(rows['0']['outcome']['uncertain_dispatches'], 1)
        self.assertEqual(rows['0']['outcome']['observed_request_attempts'], 0)

    def test_finished_response_recovers_without_network(self):
        started = dict(kind='attempt_started', task_id='0', attempt=1, request_sha256=digest(self.tasks[0]['request']))
        append_event(self.journal, started)
        append_event(self.journal, dict(started, kind='attempt_finished', status='ok', retryable=False, raw_response='{}'))
        rows = recover(self.journal, self.tasks)
        self.assertEqual(rows['0']['outcome']['status'], 'ok')

    def test_corruption_and_duplicate_rejected(self):
        self.journal.write_text('{"partial":')
        with self.assertRaises(ValueError):
            recover(self.journal, self.tasks)
        event = dict(kind='attempt_started', task_id='0', attempt=1, request_sha256=digest(self.tasks[0]['request']))
        with self.assertRaises(ValueError):
            states([event, event], self.tasks)


class ReplayTests(unittest.TestCase):
    def test_fixed_policies_are_feasible_enumerated_paths(self):
        records, packets, _ = fixture()
        packets['deletion'][0]['rules'] = [compiled()]
        paths = {tuple(p['actions']): p for p in enumerate_paths(records, packets)}
        for policy in POLICIES:
            p = replay(records, packets, policy, 7)
            q = paths[tuple(p['actions'])]
            self.assertEqual(p['removed_ids'], q['removed_ids'])
            self.assertAlmostEqual(p['discounted_return'], q['discounted_return'])
            self.assertEqual(p['acquisitions'], q['acquisitions'])

    def test_source_necessity_not_redundant_type_credit(self):
        records, packets, _ = fixture()
        records[1]['object_type'] = 'LOC'  # Keep another record to allow repair.
        packets['deletion'][0]['rules'] = [compiled()]
        self.assertEqual(replay(records, packets, 'acquire_then_repair', 7)['source_necessary_ids'], ['r'])
        packets['deletion'][0]['rules'].append(dict(family='type', kind='forbidden', pattern=['PER', 'P1', 'ORG']))
        p = replay(records, packets, 'acquire_then_repair', 7)
        self.assertEqual(p['source_associated_ids'], ['r'])
        self.assertEqual(p['source_necessary_ids'], [])


class GateTests(unittest.TestCase):
    def episodes(self):
        policy = dict(f1=.9, preservation=1., acquisitions=0, discounted_return=0., correct_lost=0,
                      injected_removed=0, source_necessary_injected=0)
        return [dict(policies={p: dict(policy) for p in POLICIES}, unique_injected=dict(deletion=0, augmentation=0),
            paths=[dict(policy, actions=['stop'])]) for _ in range(10)]

    def assess(self, episodes, valid=40):
        # Gate logic is the subject here; bootstrap is separately checked below.
        with patch('exps.paper2_rule_feasibility_20261004.analyze.bootstrap', return_value=[0., 0.]):
            return assess(episodes, valid)

    def test_format_alone_never_passes(self):
        r = self.assess(self.episodes())
        self.assertTrue(r['gates']['schema'])
        self.assertFalse(r['numerical_feasibility_pass'])
        self.assertFalse(r['gates']['decision_opportunity'])

    def test_recovery_criteria_must_hold_for_same_schedule(self):
        es = self.episodes()
        for e in es:
            e['policies']['acquire_then_repair'].update(f1=.95, preservation=.98)
            e['policies']['repair_asap'].update(source_necessary_injected=1)
        self.assertFalse(self.assess(es)['gates']['reference_recovery'])

    def test_complementarity_and_oracle_not_training_authorization(self):
        es = self.episodes()
        for e in es:
            e['policies']['acquire_then_repair'].update(f1=.95, acquisitions=4, source_necessary_injected=1)
            e['unique_injected'] = dict(deletion=1, augmentation=1)
            e['paths'].append(dict(e['policies']['acquire_then_repair'], actions=['synthetic'], acquisitions=2))
        r = self.assess(es)
        self.assertTrue(r['numerical_feasibility_pass'])
        self.assertFalse(r['formal_training_authorized_by_this_result'])
        es[0]['policies']['augmentation_only']['correct_lost'] = 1
        self.assertFalse(self.assess(es)['gates']['strategy_complementarity'])
        self.assertFalse(self.assess(es, 35)['gates']['schema'])

    def test_bootstrap_deterministic_pair_unit(self):
        from exps.paper2_rule_feasibility_20261004.analyze import bootstrap
        self.assertEqual(bootstrap([.1]*10), [.1, .1])
        self.assertEqual(bootstrap([0., 1.]), bootstrap([0., 1.]))


class EndToEndTests(unittest.TestCase):
    def test_mocked_40_output_analysis_and_incomplete_guard(self):
        from exps.paper2_rule_feasibility_20261004 import analyze as module
        with tempfile.TemporaryDirectory() as directory:
            here = Path(directory)
            (here / 'local').mkdir()
            public, scorer, pairs, tasks = [], [], [], []
            for i in range(10):
                ids = ['a' + str(i), 'b' + str(i)]
                pairs.append(ids)
                for cid in ids:
                    records, _, doc = fixture()
                    doc['case_id'] = cid
                    record = dict(records[0], source_document_id=cid, record_id=cid + ':r')
                    public.append(dict(document=doc, records=[record]))
                    scorer.append(dict(case_id=cid, reference=[['0', 'P1', '1']], injected=[]))
                    for arm in ('deletion', 'augmentation'):
                        tasks.append(dict(task_id=cid+'/'+arm, case_id=cid, arm=arm, request=dict(model=MODEL)))
            for name, value in [('local/public.json', public), ('local/scorer_only.json', scorer),
                                ('membership.json', dict(pairs=pairs)), ('manifest.json', dict(synthetic=True)),
                                ('relations.json', {'P1': 'member'})]:
                write_once(here / name, value)
            with patch.object(module, 'HERE', here), patch.object(module, 'OLD', here), patch.object(module, 'verify', return_value=tasks):
                with self.assertRaises(ValueError):
                    module.analyze()
                with contextlib.redirect_stdout(io.StringIO()):
                    collect_with(tasks, here / 'local/journal.jsonl',
                        lambda _: dict(status='ok', retryable=False, raw_response=json.dumps(body())), sleep=lambda _: None)
                    module.analyze()
                results = json.loads((here / 'results.json').read_text())
                self.assertEqual(results['outcomes'], 40)
                self.assertEqual(results['schema_valid_outputs'], 40)
                self.assertEqual(results['decision'], 'stop_without_expansion')
                self.assertEqual(results['compiled_rule_counts'], {})
                self.assertTrue((here / 'costs.json').exists())
                self.assertTrue((here / 'traces.json').exists())


if __name__ == '__main__':
    unittest.main()
