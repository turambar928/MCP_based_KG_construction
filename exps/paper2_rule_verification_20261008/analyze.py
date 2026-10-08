"""Freeze all decisions/trajectories before opening scorer-only references."""
from collections import Counter
from copy import deepcopy
import json
import statistics
from exps.paper2_rule_verification_20261008.common import *
from exps.paper2_rule_verification_20261008.prepare import verify, context
from exps.paper2_rule_verification_20261008.review import parse_review, overall, project
from exps.paper2_rule_verification_20261008.runner import states
from exps.paper2_rule_admission_20261004.admission import binding
from exps.paper2_rule_feasibility_20261004.analyze import replay, assess, bootstrap
from exps.papers_readiness_20261002.diagnose_loop import enumerate_paths, score, fact


def execute(public,packets,pairs,relations,reviews,modes):
    indexed={(p['source_document_id'],p['strategy']):p for p in packets}
    episodes=[]; audit=[]
    for i,ids in enumerate(pairs):
        records=sum((public[c]['records'] for c in ids),[])
        documents={c:public[c]['document'] for c in ids}
        banks={arm:[indexed[c,arm] for c in ids] for arm in ('deletion','augmentation')}
        variants={}
        for mode in modes:
            # schema_audit has no sound hard mapping; no inferred allow/deny list.
            admitted,rows=project(banks,documents,records,relations,reviews,{},mode)
            audit.extend(dict(r,episode=i) for r in rows)
            fixed={p:replay(records,admitted,p,PROTOCOL['random_policy_seed']+i) for p in POLICIES}
            for p in fixed.values():
                acquired={ev['packet_id'] for ev in p['events'] if ev.get('packet_id')}
                p['activated_candidate_occurrences']=sum(len(pkt['rules']) for q in admitted.values() for pkt in q if pkt['packet_id'] in acquired)
            variants[mode]=dict(episode=i,documents=ids,policies=fixed,paths=enumerate_paths(records,admitted))
        episodes.append(dict(episode=i,documents=ids,variants=variants))
    return episodes,audit


def score_all(episodes,public,scorer):
    for episode in episodes:
        ids=episode['documents']; records=sum((public[c]['records'] for c in ids),[])
        reference={(c,*t) for c in ids for t in scorer[c]['reference']}
        injected={(c,*t) for c in ids for t in scorer[c]['injected']}
        injected_ids={r['record_id'] for r in records if fact(r) in injected}
        correct_ids={r['record_id'] for r in records if fact(r) in reference}
        baseline=episode['variants']['grounded']['policies']['acquire_then_repair']
        for variant in episode['variants'].values():
            for p in list(variant['policies'].values())+variant['paths']:
                p.update(score([r for r in records if r['record_id'] not in p['removed_ids']],reference,injected))
            by_actions={tuple(p['actions']):p for p in variant['paths']}
            for p in variant['policies'].values():
                p['source_necessary_injected']=len(set(p['source_necessary_ids']) & injected_ids)
                matching=by_actions[tuple(p['actions'])]
                for key in ('f1','preservation','correct_lost','injected_removed','acquisitions','discounted_return'):
                    if abs(p[key]-matching[key])>1e-12: raise ValueError('Enumeration mismatch: '+key)
            fixed=variant['policies']
            variant['unique_injected']={arm:len((set(fixed[arm+'_only']['removed_ids'])-set(fixed[other+'_only']['removed_ids'])) & injected_ids)
                for arm,other in [('deletion','augmentation'),('augmentation','deletion')]}
            kept=set(fixed['acquire_then_repair']['removed_ids']); old=set(baseline['removed_ids'])
            variant['edit_audit']=dict(prevented_reference_losses=sorted((old-kept)&correct_ids),
                lost_baseline_injected_removals=sorted((old-kept)&injected_ids),
                new_reference_losses=sorted((kept-old)&correct_ids),
                new_injected_removals=sorted((kept-old)&injected_ids))


def analyze():
    tasks=verify(); public,packets,pairs,relations=context()
    rows=states(read_events(HERE/'local/journal.jsonl'),tasks)
    complete=len(rows)==len(tasks) and all(r['outcome'] is not None for r in rows.values())
    if rows and not complete and not (HERE/'local/journal.stopped.json').exists():
        raise ValueError('Collection incomplete without a terminal outage; finish/recover first')
    modes=MODES if complete else MODES[:3]
    member={c:ids for ids in pairs for c in ids}; indexed={p['packet_id']:p for p in packets}
    reviews={}; parsed=[]; costs=[]; valid=0
    for task in tasks:
        row=rows.get(task['task_id']); out=row['outcome'] if row else None
        packet=indexed[task['task_id']]; ids=member[packet['source_document_id']]
        docs={c:public[c]['document'] for c in ids}; records=sum((public[c]['records'] for c in ids),[])
        checks=[]; state=out['status'] if out else 'not_requested'
        if out and state=='ok':
            try:
                checks=parse_review(out['raw_response'],packet,docs,records)
                valid+=1; state='valid_review'
            except (ValueError,TypeError,KeyError) as err: state='review_contract_error'
        parsed.append(dict(task_id=task['task_id'],status=state))
        for ordinal,rule in enumerate(packet['rules']):
            review=checks[ordinal]['checks'] if checks else []
            bound=binding(packet,rule,docs[packet['source_document_id']],records,relations,docs)
            reviews[packet['packet_id'],ordinal]=dict(binding=bound,verdict=overall(review),
                evidence_class='automatic_review',version=VERSION,model=MODEL,review_status=state,
                checks_sha256=digest(review),request_sha256=digest(task['request']),
                response_sha256=digest(out['raw_response']) if out else None)
        attempts=row['finished'] if row else []
        costs.append(dict(task_id=task['task_id'],status=state,dispatch_intents=len(row['started']) if row else 0,
            uncertain_dispatches=(len(row['started'])-len(attempts)) if row else 0,
            attempts=[{k:v for k,v in a.items() if k!='raw_response'} for a in attempts]))
    episodes,audit=execute(public,packets,pairs,relations,reviews,modes)
    # All proposed actions and paths now fixed. Only this boundary opens labels.
    scorer={r['case_id']:r for r in read(STUDY/'local/scorer_only.json')}
    score_all(episodes,public,scorer)
    originals=read(STUDY/'traces.json')
    for e,orig in zip(episodes,originals):
        for policy,p in e['variants']['grounded']['policies'].items():
            for k in ('actions','removed_ids','events','acquisitions','discounted_return'):
                if digest(p[k])!=digest(orig['policies'][policy][k]): raise ValueError('Historical replay changed')
    results={}
    for mode in modes:
        es=[e['variants'][mode] for e in episodes]
        result=assess(es,sum(p['parse_success'] for p in packets))
        result['gates']['historical_generation_schema']=result['gates'].pop('schema')
        result['schema_gate_interpretation']='39/40 original generation outputs; automatic-review validity is reported separately.'
        result['delta_f1_from_grounded_ci95']=bootstrap([e['variants'][mode]['policies']['acquire_then_repair']['f1']-e['variants']['grounded']['policies']['acquire_then_repair']['f1'] for e in episodes])
        result['edit_audit_totals']={k:sum(len(e['edit_audit'][k]) for e in es) for k in es[0]['edit_audit']}
        rr=[r for r in audit if r['mode']==mode]
        result['candidate_counts']={kind:dict(proposed=sum(r['family']+'/'+r['kind']==kind for r in rr),
            admitted=sum(r['family']+'/'+r['kind']==kind and r['admitted'] for r in rr))
            for kind in sorted({r['family']+'/'+r['kind'] for r in rr})}
        result['activated_candidate_occurrences']=sum(e['policies']['acquire_then_repair']['activated_candidate_occurrences'] for e in es)
        result['terminal_paths']=sum(len(e['paths']) for e in es)
        results[mode]=result
    observed=[a for c in costs for a in c['attempts']]
    result=dict(version=VERSION,status='completed_development_only' if complete else 'offline_complete_api_blocked' if rows else 'offline_only_not_collected',
        model=MODEL,documents=20,episodes=10,candidates=407,planned_review_tasks=len(tasks),
        finalized_review_tasks=sum(r['outcome'] is not None for r in rows.values()),valid_review_outputs=valid,
        review_status_counts=dict(Counter(r['status'] for r in parsed)),
        review_verdict_counts=dict(Counter(r['verdict'] for r in reviews.values())),
        evaluated_modes=list(modes),unavailable_modes=[m for m in MODES if m not in modes],
        fixed_replays=len(modes)*len(POLICIES)*len(pairs),historical_replays_reproduced=80,
        observed_request_attempts=len(observed),dispatch_intents=sum(c['dispatch_intents'] for c in costs),
        uncertain_dispatches=sum(c['uncertain_dispatches'] for c in costs),
        retries=sum(max(0,c['dispatch_intents']-1) for c in costs),
        usage_totals={k:sum((a.get('usage') or {}).get(k,0) or 0 for a in observed) for k in ('prompt_tokens','completion_tokens','total_tokens')},
        mean_attempt_seconds=statistics.mean(a['latency_seconds'] for a in observed) if observed else None,
        measured_total_attempt_seconds=sum(a['latency_seconds'] for a in observed),
        usage_missing_attempts=sum(a.get('usage') is None for a in observed),billed_cost=None,
        cost_note='No current independently verified tariff. Do not infer dollars from old per-request prices; unknown usage is not zero usage.',
        schema_hard_mappings=0,schema_note=read(HERE/'schema_audit.json')['reason'],
        variants=results,trained_models=0,independent_human_labels=0,old_gate_changed=False,
        manifest_sha256=sha(HERE/'manifest.json'),
        interpretation='Automatic model review on previously inspected development data. No semantic accuracy, human verification, held-out gain or learned policy claim. Missing automatic arms are not zero-performance results.')
    verify()
    for filename,value in [('results.json',result),('decisions.json',audit),('automatic_reviews.json',list(reviews.values())),
                           ('replays.json',episodes),('costs.json',costs),('review_status.json',parsed)]:write_once(HERE/filename,value)
    print(json.dumps({k:result[k] for k in ('status','fixed_replays','observed_request_attempts','valid_review_outputs','unavailable_modes')},indent=2))
