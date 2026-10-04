"""Offline post-hoc loss attribution. No API, new labels, or frozen-code edits."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve().parent
from exps.paper2_rule_feasibility_20261004.common import read, sha, digest, write_once, POLICIES, PROTOCOL
from exps.paper2_rule_feasibility_20261004.prepare import verify
from exps.paper2_rule_feasibility_20261004.generation import compile_response
from exps.paper2_rule_feasibility_20261004.runner import states
from exps.paper2_rule_feasibility_20261004.common import read_events
from exps.paper2_rule_feasibility_20261004.analyze import replay
from exps.paper2_docred_v2_round2.environment import SourceRuleEnvironment
from exps.papers_readiness_20261002.diagnose_loop import fact, score

STUDY = ROOT / 'exps/paper2_rule_feasibility_20261004'
VARIANTS = ('original', 'quarantine_type_forbidden', 'quarantine_source_contradicted', 'quarantine_both')


def filter_packets(packets, variant):
    """Uses candidate family/kind only; never receives reference labels or IDs to protect."""
    if variant not in VARIANTS:
        raise ValueError('Unknown diagnostic variant')
    result = deepcopy(packets)
    for queue in result.values():
        for packet in queue:
            packet['rules'] = [r for r in packet['rules'] if not (
                r['family'] == 'type' and r['kind'] == 'forbidden'
                and variant in ('quarantine_type_forbidden', 'quarantine_both')) and not (
                r['family'] == 'source' and r['verdict'] == 'contradicted'
                and variant in ('quarantine_source_contradicted', 'quarantine_both'))]
    return result


def key(rule):
    return (('type', rule['kind'], *rule['pattern']) if rule['family'] == 'type'
            else ('source', rule['verdict'], rule['record_id']))


def deletion_states(records, packets, actions):
    env = SourceRuleEnvironment(records, packets)
    rows = {}
    for action in actions:
        if action == 'repair':
            for record in env.records:
                rid = record['record_id']
                scan = env.scan()[rid]
                if not scan['violation']:
                    continue
                pattern = (record['subject_type'], record['relation'], record['object_type'])
                matching = {k: sorted(v) for k, v in env.active.items()
                            if (k[0] == 'type' and k[2:] == pattern) or
                               (k[0] == 'source' and k[2] == rid)}
                without = {}
                for family in ('type', 'source'):
                    counterfactual = deepcopy(env)
                    counterfactual.active = {k: v for k, v in env.active.items() if not (
                        family == 'type' and k[:2] == ('type', 'forbidden') or
                        family == 'source' and k[:2] == ('source', 'contradicted'))}
                    without[family] = counterfactual.scan()[rid]['violation']
                rows[rid] = dict(scan=scan, active_matching_rules=[dict(key=list(k), packet_ids=v) for k, v in matching.items()],
                                 violation_without_type_forbidden=without['type'],
                                 violation_without_source_contradicted=without['source'])
        env.step(action)
    return rows, sorted(env.removed)


def quote_checks(document, record, rule):
    """Surface provenance/co-mention checks, explicitly NOT an entailment test."""
    entities = {e['entity_id']: e for e in document['entities']}
    checks = []
    for evidence in rule['evidence']:
        sentence = ' '.join(document['sents'][evidence['sentence_id']])
        quote = sentence[evidence['start']:evidence['end']]
        import hashlib
        assert hashlib.sha256(quote.encode()).hexdigest() == evidence['quote_sha256']
        checks.append(dict(sentence_id=evidence['sentence_id'], quote_sha256=evidence['quote_sha256'],
            head_surface_in_quote=any(m['name'].casefold() in quote.casefold() for m in entities[record['head_entity_id']]['mentions']),
            tail_surface_in_quote=any(m['name'].casefold() in quote.casefold() for m in entities[record['tail_entity_id']]['mentions']),
            provenance_valid=True, entails_contradiction='not_determined_by_this_check'))
    return checks


def main():
    tasks = verify()
    historical = read(STUDY / 'execution_validation.json')['artifact_sha256']
    for path, expected in historical.items():
        assert sha(STUDY / path) == expected, path
    public = {x['document']['case_id']: x for x in read(STUDY / 'local/public.json')}
    packets = read(STUDY / 'packets.json')
    relations = read(ROOT / 'exps/paper2_docred/relations.json')
    archived = read(STUDY / 'traces.json')
    pairs = read(STUDY / 'membership.json')['pairs']
    by_packet = {(p['source_document_id'], p['strategy']): p for p in packets}
    journal = states(read_events(STUDY / 'local/journal.jsonl'), tasks)
    for t in tasks:
        x = public[t['case_id']]
        ok, rules, rejects = compile_response(journal[t['task_id']]['outcome']['raw_response'], x['document'], x['records'], relations)
        p = by_packet[t['case_id'], t['arm']]
        assert ok == p['parse_success'] and rules == p['rules']
        assert [{k: r[k] for k in ('reason', 'ordinal', 'path', 'validator') if k in r} for r in rejects] == p['rejections']
    # All interventions and action selections occur before opening scorer references.
    replayed = []
    for i, ids in enumerate(pairs):
        records = sum((public[c]['records'] for c in ids), [])
        banks = {arm: [by_packet[c, arm] for c in ids] for arm in ('deletion', 'augmentation')}
        variants = {v: {p: replay(records, filter_packets(banks, v), p, PROTOCOL['random_policy_seed'] + i)
                        for p in POLICIES} for v in VARIANTS}
        states_before, removed = deletion_states(records, banks, variants['original']['acquire_then_repair']['actions'])
        assert removed == variants['original']['acquire_then_repair']['removed_ids']
        for p in POLICIES:
            for field in ('actions', 'removed_ids', 'events', 'acquisitions', 'discounted_return'):
                assert digest(variants['original'][p][field]) == digest(archived[i]['policies'][p][field]), (i, p, field)
        replayed.append(dict(episode=i, documents=ids, variants=variants, pre_deletion=states_before))
    scorer = {s['case_id']: s for s in read(STUDY / 'local/scorer_only.json')}
    cases, local_cases = [], []
    for episode in replayed:
        ids = episode['documents']
        records = sum((public[c]['records'] for c in ids), [])
        reference = {(c, *t) for c in ids for t in scorer[c]['reference']}
        injected = {(c, *t) for c in ids for t in scorer[c]['injected']}
        for policies in episode['variants'].values():
            for p in policies.values():
                p.update(score([r for r in records if r['record_id'] not in p['removed_ids']], reference, injected))
        lost = [r for r in records if fact(r) in reference and r['record_id'] in episode['variants']['original']['acquire_then_repair']['removed_ids']]
        for record in lost:
            cid, rid = record['source_document_id'], record['record_id']
            doc = public[cid]['document']
            entities = {e['entity_id']: e for e in doc['entities']}
            pre = episode['pre_deletion'][rid]
            relevant = []
            for packet in packets:
                for rule in packet['rules']:
                    if not any(list(key(rule)) == a['key'] and packet['packet_id'] in a['packet_ids'] for a in pre['active_matching_rules']):
                        continue
                    entry = dict(packet_id=packet['packet_id'], strategy=packet['strategy'], origin_document=packet['source_document_id'], rule=rule)
                    if rule['family'] == 'source':
                        entry['quote_checks'] = quote_checks(doc, record, rule)
                    relevant.append(entry)
            case = dict(episode=episode['episode'], record=record, relation_name=relations[record['relation']],
                head_mentions=sorted({m['name'] for m in entities[record['head_entity_id']]['mentions']}),
                tail_mentions=sorted({m['name'] for m in entities[record['tail_entity_id']]['mentions']}),
                scoring_status='reference-backed loss; not independent semantic truth',
                pre_deletion=pre, relevant_rules=relevant, human_semantic_verdict=None)
            cases.append(case)
            local_cases.append(dict(case=case, document=doc))
    summaries = {}
    for v in VARIANTS:
        summaries[v] = {}
        for p in POLICIES:
            rows = [e['variants'][v][p] for e in replayed]
            summaries[v][p] = dict(
                **{k: statistics.mean(r[k] for r in rows) for k in ('f1', 'preservation', 'acquisitions', 'discounted_return')},
                **{k: sum(r[k] for r in rows) for k in ('correct_lost', 'injected_removed')})
    assert len(cases) == 4
    for path, expected in historical.items():
        assert sha(STUDY / path) == expected, path
    write_once(HERE / 'cases.json', cases)
    write_once(HERE / 'local/source_dossiers.json', local_cases)
    write_once(HERE / 'replays.json', replayed)
    write_once(HERE / 'summary.json', dict(scope='Post-hoc same-development-bank diagnosis; no new empirical labels or confirmation study.',
        model_api_requests=0,trained_models=0,human_annotations_added=0,old_gate_unchanged=True,
        historical_response_compilations_identical=40,original_fixed_replays_identical=80,
        total_diagnostic_replays=len(replayed)*len(VARIANTS)*len(POLICIES),cases=4,
        variants=summaries,input_artifact_sha256=historical,script_sha256=sha(Path(__file__)),
        interpretation='Packet quarantine uses rule family only; it removes unvalidated deletion authority, not certified errors. No variant is promoted or used to rerun the frozen gate.'))
    print(json.dumps({v: summaries[v]['acquire_then_repair'] for v in VARIANTS}, indent=2))


if __name__ == '__main__':
    main()
