"""Offline post-hoc admission replay; keeps all historical artifacts frozen."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve().parent
STUDY = ROOT/'exps/paper2_rule_feasibility_20261004'
from exps.paper2_rule_admission_20261004.admission import Registry, admit_packets, digest, VERSION
from exps.paper2_rule_feasibility_20261004.common import read, sha, write_once, POLICIES, PROTOCOL
from exps.paper2_rule_feasibility_20261004.analyze import replay
from exps.papers_readiness_20261002.diagnose_loop import score, fact


def main():
    protected = read(STUDY/'execution_validation.json')['artifact_sha256']
    for path, expected in protected.items():
        assert sha(STUDY/path) == expected, path
    registry = Registry.load(HERE/'trust_registry.json')
    # This run deliberately claims no supplied independent approvals.
    assert not registry.sources, 'Use a new versioned study for actual trusted evidence'
    public = {x['document']['case_id']: x for x in read(STUDY/'local/public.json')}
    source_packets = read(STUDY/'packets.json')
    packets = {(p['source_document_id'], p['strategy']): p for p in source_packets}
    originals = read(STUDY/'traces.json')
    relations = read(ROOT/'exps/paper2_docred/relations.json')
    pairs = read(STUDY/'membership.json')['pairs']
    audits, episodes = [], []
    for i, ids in enumerate(pairs):
        records = sum((public[c]['records'] for c in ids), [])
        documents = {c: public[c]['document'] for c in ids}
        banks = {arm: [packets[c, arm] for c in ids] for arm in ('deletion', 'augmentation')}
        snapshot = digest((records, documents, banks))
        modes = {'original': deepcopy(banks)}
        for mode in ('grounded', 'validated'):
            modes[mode], rows = admit_packets(banks, documents, records, relations, registry, mode)
            audits.extend(dict(row, episode=i, mode=mode) for row in rows)
        variants = {}
        for mode, bank in modes.items():
            variants[mode] = {}
            for policy in POLICIES:
                result = replay(records, bank, policy, PROTOCOL['random_policy_seed'] + i)
                acquired = {event['packet_id'] for event in result['events'] if event.get('packet_id')}
                # Admission precedes execution; activation occurs only upon acquisition.
                result['activated_candidate_occurrences'] = sum(len(p['rules']) for q in bank.values() for p in q if p['packet_id'] in acquired)
                variants[mode][policy] = result
                if mode in ('original', 'grounded'):
                    for key in ('actions','removed_ids','events','acquisitions','discounted_return'):
                        assert digest(result[key]) == digest(originals[i]['policies'][policy][key]), (i,mode,policy,key)
                else:
                    assert not result['removed_ids'] and result['activated_candidate_occurrences'] == 0
        assert digest((records, documents, banks)) == snapshot, 'Input mutation'
        episodes.append(dict(episode=i, documents=ids, variants=variants))
    # Scorer references are read AFTER every policy decision has been materialized.
    scorer = {r['case_id']: r for r in read(STUDY/'local/scorer_only.json')}
    for e in episodes:
        ids=e['documents'];records=sum((public[c]['records'] for c in ids), [])
        reference={(c,*t) for c in ids for t in scorer[c]['reference']}
        injected={(c,*t) for c in ids for t in scorer[c]['injected']}
        injected_ids={r['record_id'] for r in records if fact(r) in injected}
        for policies in e['variants'].values():
            for result in policies.values():
                result.update(score([r for r in records if r['record_id'] not in result['removed_ids']], reference,injected))
                result['source_necessary_injected']=len(set(result['source_necessary_ids']) & injected_ids)
        e['unique_injected']={mode:{arm:len((set(ps[arm+'_only']['removed_ids'])-set(ps[other+'_only']['removed_ids'])) & injected_ids)
            for arm,other in [('deletion','augmentation'),('augmentation','deletion')]} for mode,ps in e['variants'].items()}
    summaries={}
    for mode in ('original','grounded','validated'):
        summaries[mode]={}
        for policy in POLICIES:
            rows=[e['variants'][mode][policy] for e in episodes]
            summaries[mode][policy]=dict(**{k:statistics.mean(r[k] for r in rows) for k in ('f1','preservation','acquisitions','discounted_return','activated_candidate_occurrences')},
                **{k:sum(r[k] for r in rows) for k in ('correct_lost','injected_removed','source_necessary_injected')})
    audited=[r for r in audits if r['mode']=='validated']
    counts=dict(proposed=len(audited), grounded=sum(r['grounded'] for r in audited),
        validated=sum(r['validated'] for r in audited), admitted=sum(r['admitted'] for r in audited),
        quarantined=sum(not r['admitted'] for r in audited),
        by_family_kind=dict(Counter(r['family']+'/'+r['kind'] for r in audited)),
        reasons=dict(Counter(r['reason'] for r in audited)))
    for path, expected in protected.items():
        assert sha(STUDY/path) == expected,path
    summary=dict(version=VERSION, scope='Post-hoc same-development-cache execution-contract study; no new semantic labels or held-out improvement.',
        model_api_requests=0,trained_models=0,new_human_labels=0, trusted_sources=registry.sources,
        documents=20,episodes=10,policies=8,variants=summaries,
        replays=240,original_trajectories_reproduced=80,grounding_only_trajectories_equal_original=80,
        candidate_counts=counts,unique_injected_removals={mode:{arm:sum(e['unique_injected'][mode][arm] for e in episodes)
            for arm in ('deletion','augmentation')} for mode in summaries},
        old_expansion_gate_unchanged=True,formal_training_started=False,
        interpretation='Empty independent evidence means zero admitted rules, zero repairs and zero reference losses. This verifies enforcement, not semantic-validator accuracy or improved repair quality.',
        protected_artifacts=protected, study_inputs={p:sha(STUDY/p) for p in ('local/public.json','local/scorer_only.json','packets.json','traces.json','membership.json')},
        implementation_sha256={p:sha(HERE/p) for p in ('admission.py','run.py','trust_registry.json')})
    write_once(HERE/'decisions.json',audits)
    write_once(HERE/'replays.json',episodes)
    write_once(HERE/'results.json',summary)
    print(json.dumps(dict(candidate_counts=counts,results={m:summaries[m]['acquire_then_repair'] for m in summaries}),indent=2))


if __name__=='__main__':
    main()
