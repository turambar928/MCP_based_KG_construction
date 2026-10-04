"""Fixed schedules and scorer-only opportunity diagnostics after all 40 outcomes."""
from collections import Counter
from copy import deepcopy
import json
import random
import statistics
from exps.paper2_rule_feasibility_20261004.common import HERE, OLD, MODEL, ARMS, POLICIES, PROTOCOL, read, digest, write_once, read_events
from exps.paper2_rule_feasibility_20261004.prepare import verify
from exps.paper2_rule_feasibility_20261004.generation import compile_response
from exps.paper2_rule_feasibility_20261004.runner import states
from exps.paper2_docred_v2_round2.environment import SourceRuleEnvironment, ACTIONS
from exps.papers_readiness_20261002.diagnose_loop import enumerate_paths, score, fact


def replay(records, packets, policy, seed):
    if policy not in POLICIES:
        raise ValueError('Unknown fixed policy')
    env = SourceRuleEnvironment(records, packets)
    rng = random.Random(seed)
    source_associated, source_necessary = set(), set()
    while not env.done:
        feasible = {a for a, valid in zip(ACTIONS, env.mask()) if valid}
        if policy == 'stop':
            action = 'stop'
        elif policy == 'uniform_feasible':
            action = rng.choice([a for a in ACTIONS if a in feasible])
        elif policy.endswith('asap') and 'repair' in feasible:
            action = 'repair'
        else:
            order = ['acquire_augmentation', 'acquire_deletion'] if policy.startswith('augmentation_first') else list(ACTIONS[:2])
            if policy in ('deletion_only', 'augmentation_only'):
                order = ['acquire_' + policy.removesuffix('_only')]
            action = next((a for a in order if a in feasible), 'repair' if 'repair' in feasible else 'stop')
        scan = env.scan()
        # Counterfactual at the same pre-edit state: remove only contradiction rules.
        without = deepcopy(env)
        without.active = {k: v for k, v in env.active.items() if k[:2] != ('source', 'contradicted')}
        counterfactual = without.scan()
        _, _, _, event = env.step(action)
        source_associated.update(k for k in event['removed_ids'] if scan[k]['source_contradicted'])
        source_necessary.update(k for k in event['removed_ids'] if scan[k]['source_contradicted'] and not counterfactual[k]['violation'])
    return dict(actions=[e['action'] for e in env.events], removed_ids=sorted(env.removed),
                acquisitions=sum(env.acquired.values()), events=env.events,
                discounted_return=sum(.95 ** i * e['reward'] for i, e in enumerate(env.events)),
                source_associated_ids=sorted(source_associated), source_necessary_ids=sorted(source_necessary))


def bootstrap(values):
    rng = random.Random(20261004)
    n = len(values)
    draws = sorted(statistics.mean(rng.choices(values, k=n)) for _ in range(10000))
    return [draws[249], draws[9749]]


def assess(episodes, valid_outputs):
    average = lambda f: statistics.mean(f(e) for e in episodes)
    summary = {p: {key: average(lambda e: e['policies'][p][key]) for key in
                  ('f1', 'preservation', 'acquisitions', 'discounted_return')} for p in POLICIES}
    for p in POLICIES:
        summary[p].update(correct_lost=sum(e['policies'][p]['correct_lost'] for e in episodes),
            injected_removed=sum(e['policies'][p]['injected_removed'] for e in episodes),
            source_necessary_injected_episodes=sum(e['policies'][p]['source_necessary_injected'] > 0 for e in episodes))
        summary[p]['delta_f1_from_stop_ci95'] = bootstrap([e['policies'][p]['f1'] - e['policies']['stop']['f1'] for e in episodes])
    gates = PROTOCOL['gates']
    deterministic = [p for p in POLICIES if p != 'uniform_feasible']
    qualified = [p for p in deterministic if p != 'stop'
        and summary[p]['f1'] > summary['stop']['f1'] + 1e-12
        and summary[p]['preservation'] >= gates['min_mean_preservation']
        and summary[p]['source_necessary_injected_episodes'] >= gates['min_source_repair_episodes']]
    unique = {arm: sum(e['unique_injected'][arm] for e in episodes) for arm in ARMS}
    complementary = all(unique[arm] >= gates['min_unique_injected_per_strategy'] and
                        summary[arm + '_only']['correct_lost'] <= gates['max_single_bank_correct_losses'] for arm in ARMS)
    # One globally best deterministic comparator; never feed this choice to a policy.
    best = min(deterministic, key=lambda p: (-summary[p]['f1'], -summary[p]['preservation'], summary[p]['acquisitions'], p))
    oracle = [min((p for p in e['paths'] if p['preservation'] >= gates['min_mean_preservation']),
                  key=lambda p: (-p['f1'], p['correct_lost'], p['acquisitions'], p['actions'])) for e in episodes]
    headroom = 100 * (statistics.mean(p['f1'] for p in oracle) - summary[best]['f1'])
    savings = []
    for e in episodes:
        target = e['policies'][best]
        feasible = [p for p in e['paths'] if p['f1'] >= target['f1'] - 1e-12
            and p['preservation'] >= gates['min_mean_preservation'] and p['correct_lost'] <= target['correct_lost']]
        savings.append(target['acquisitions'] - min(p['acquisitions'] for p in feasible) if feasible else None)
    cost_opportunity = all(s is not None for s in savings) and statistics.mean(savings) >= gates['min_mean_oracle_acquisition_saving'] and sum(s >= 1 for s in savings) >= gates['min_cost_saving_episodes']
    flags = dict(schema=valid_outputs >= gates['min_valid_responses'], reference_recovery=bool(qualified),
                 strategy_complementarity=complementary,
                 decision_opportunity=headroom >= gates['min_oracle_headroom_pp'] or cost_opportunity)
    return dict(fixed_policies=summary, reference_gate_policies=qualified, unique_injected_removals=unique,
        strongest_fixed_policy=best, safe_executable_oracle_f1=statistics.mean(p['f1'] for p in oracle),
        safe_oracle_headroom_pp=headroom, oracle_acquisition_savings_by_episode=savings,
        gates=flags, numerical_feasibility_pass=all(flags.values()),
        decision='eligible_for_separate_formal_design' if all(flags.values()) else 'stop_without_expansion',
        semantic_review='pending; not established by quote or reference checks',
        formal_training_authorized_by_this_result=False,
        interpretation='Development diagnostics only. Oracles use scorer references; cost savings are not deployable results. No learned policy was evaluated.')


def analyze():
    tasks = verify()
    rows = states(read_events(HERE / 'local/journal.jsonl'), tasks)
    if len(rows) != len(tasks) or any(r['outcome'] is None for r in rows.values()):
        raise ValueError('All 40 outcomes, including failures, must be finalized before analysis')
    public = read(HERE / 'local/public.json')
    by_id = {x['document']['case_id']: x for x in public}
    relations = read(OLD / 'relations.json')
    packets, audit, costs = {}, [], []
    for t in tasks:
        row = rows[t['task_id']]
        result = row['outcome']
        x = by_id[t['case_id']]
        if result['status'] == 'ok':
            ok, rules, rejects = compile_response(result['raw_response'], x['document'], x['records'], relations)
        else:
            ok, rules, rejects = False, [], [dict(reason=result['status'])]
        safe_rejects = [{k: r[k] for k in ('reason', 'ordinal', 'path', 'validator') if k in r} for r in rejects]
        packets[t['case_id'], t['arm']] = dict(packet_id=t['case_id'] + ':' + t['arm'], source_document_id=t['case_id'],
            strategy=t['arm'], parse_success=ok, rules=rules, rejections=safe_rejects,
            provenance=dict(model=MODEL, response_sha256=digest(result['raw_response']), request_sha256=result['request_sha256']))
        audit.append(dict(task_id=t['task_id'], rejections=rejects))
        costs.append(dict(task_id=t['task_id'], status=result['status'], observed_request_attempts=result['observed_request_attempts'],
            uncertain_dispatches=result['uncertain_dispatches'], dispatch_intents=result['dispatch_intents'],
            attempts=[{k: v for k, v in a.items() if k != 'raw_response'} for a in row['finished']]))
    # References are opened after response compilation. Replay and enumeration accept public inputs only.
    scorer = {r['case_id']: r for r in read(HERE / 'local/scorer_only.json')}
    episodes = []
    for i, ids in enumerate(read(HERE / 'membership.json')['pairs']):
        records = sum((by_id[c]['records'] for c in ids), [])
        queue = {arm: [packets[c, arm] for c in ids] for arm in ARMS}
        fixed = {p: replay(records, queue, p, PROTOCOL['random_policy_seed'] + i) for p in POLICIES}
        paths = enumerate_paths(records, queue)
        reference = {(c, *t) for c in ids for t in scorer[c]['reference']}
        injected = {(c, *t) for c in ids for t in scorer[c]['injected']}
        injected_ids = {r['record_id'] for r in records if fact(r) in injected}
        for p in list(fixed.values()) + paths:
            p.update(score([r for r in records if r['record_id'] not in p['removed_ids']], reference, injected))
        for p in fixed.values():
            p['source_necessary_injected'] = len(set(p['source_necessary_ids']) & injected_ids)
        by_actions = {tuple(p['actions']): p for p in paths}
        for p in fixed.values():
            counterpart = by_actions[tuple(p['actions'])]
            for k in ('f1', 'preservation', 'correct_lost', 'injected_removed', 'acquisitions', 'discounted_return'):
                if abs(counterpart[k] - p[k]) > 1e-12:
                    raise ValueError('Fixed replay and exhaustive paths disagree: ' + k)
        unique = {arm: len((set(fixed[arm + '_only']['removed_ids']) - set(fixed[other + '_only']['removed_ids'])) & injected_ids)
                  for arm, other in [('deletion', 'augmentation'), ('augmentation', 'deletion')]}
        episodes.append(dict(episode=i, documents=ids, policies=fixed, paths=paths, unique_injected=unique))
    valid = sum(p['parse_success'] for p in packets.values())
    result = assess(episodes, valid)
    result.update(status='completed_development_only', documents=20, episodes=10, outcomes=40, schema_valid_outputs=valid,
        observed_request_attempts=sum(c['observed_request_attempts'] for c in costs),
        uncertain_dispatches=sum(c['uncertain_dispatches'] for c in costs),
        dispatch_intents=sum(c['dispatch_intents'] for c in costs),
        compiled_rule_counts=dict(Counter(r['family'] + '/' + r.get('kind', r.get('verdict', ''))
                                         for p in packets.values() for r in p['rules'])),
        rejection_counts=dict(Counter(r['reason'] for p in packets.values() for r in p['rejections'])),
        input_manifest_sha256=digest(read(HERE / 'manifest.json')))
    for name, value in [('packets.json', list(packets.values())), ('traces.json', episodes),
                        ('costs.json', costs), ('local/compiler_audit.json', audit), ('results.json', result)]:
        write_once(HERE / name, value)
    print(json.dumps(result, indent=2))
