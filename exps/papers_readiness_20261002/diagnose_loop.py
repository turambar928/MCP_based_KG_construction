"""Offline exhaustive development diagnosis; never generates or trains a model.

Reference labels score terminal states only. Oracle paths are diagnostics, not
deployable policies, held-out results, or independent trajectory samples.
"""
import copy
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from exps.paper2_docred_v2_round2.environment import SourceRuleEnvironment, ACTIONS

HERE = Path(__file__).resolve().parent


def fact(record):
    return tuple(record[k] for k in ('source_document_id', 'head_entity_id', 'relation', 'tail_entity_id'))


def score(records, reference, injected):
    current = {fact(r) for r in records}
    correct = current & reference
    return dict(f1=2 * len(correct) / (len(current) + len(reference)) if current or reference else 1.,
                preservation=len(correct) / len(reference) if reference else 1.,
                correct_lost=len(reference - current), injected_removed=len(injected - current))


def enumerate_paths(records, packets):
    """Explore every feasible action sequence, including early stop, within H=10.

    Scorer data are deliberately absent from this function's arguments.
    Histories are not merged: ordering can affect discounted reward and costs.
    """
    terminals = []

    def visit(env, discounted, qualities):
        if env.done:
            q = qualities + [qualities[-1]] * (11 - len(qualities))
            flags = sum(row['violation'] for row in env.scan().values())
            terminals.append(dict(actions=[e['action'] for e in env.events],
                                  removed_ids=sorted(env.removed),
                                  acquisitions=sum(env.acquired.values()),
                                  discounted_return=discounted,
                                  proxy_auc10=sum((a + b) / 2 for a, b in zip(q, q[1:])) / 10,
                                  pending_feasible_repair=0 < flags < len(env.records),
                                  late_permissions=sum(len(e['late_permission_ids']) for e in env.events)))
            return
        for action, feasible in zip(ACTIONS, env.mask()):
            if not feasible:
                continue
            child = copy.deepcopy(env)
            _, reward, _, event = child.step(action)
            quality = sum(event['potentials_after']) / 2
            visit(child, discounted + .95 ** (len(qualities) - 1) * reward, qualities + [quality])

    env = SourceRuleEnvironment(records, packets)
    visit(env, 0., [sum(env.potentials()) / 2])
    return terminals


def bank_flags(records, packets, strategies, families):
    queues = copy.deepcopy(packets)
    for strategy, queue in queues.items():
        for p in queue:
            p['rules'] = [r for r in p['rules'] if strategy in strategies and r['family'] in families]
    env = SourceRuleEnvironment(records, queues)
    for action in ('acquire_deletion', 'acquire_deletion', 'acquire_augmentation', 'acquire_augmentation'):
        env.step(action)
    scan = env.scan()
    return {k for k, row in scan.items() if row['violation']}, sum(r['conflict'] for r in scan.values())


def run_round(name):
    folder = ROOT / 'exps' / name
    # Inputs are read-only. Local source text never enters the released report.
    public = {x['document']['case_id']: x for x in json.loads((folder / 'local/pilot_public.json').read_text())}
    refs = {x['case_id']: x for x in json.loads((folder / 'local/pilot_scorer_only.json').read_text())}
    packets = {(p['source_document_id'], p['strategy']): p for p in json.loads((folder / 'pilot_packets_public.json').read_text())}
    pairs = json.loads((folder / 'pilot_membership.json').read_text())['pairs']
    archived = json.loads((folder / 'pilot_traces.json').read_text())
    episodes = []
    details = []
    for i, ids in enumerate(pairs):
        records = sum((public[c]['records'] for c in ids), [])
        queue = {s: [packets[c, s] for c in ids] for s in ('deletion', 'augmentation')}
        terminals = enumerate_paths(records, queue)
        # Only now introduce scorer-only reference and injection membership.
        reference = {(c, *t) for c in ids for t in refs[c]['reference']}
        injected = {(c, *t) for c in ids for t in refs[c]['injected']}
        correct_ids = {r['record_id'] for r in records if fact(r) in reference}
        injected_ids = {r['record_id'] for r in records if fact(r) in injected}
        for path in terminals:
            remaining = [r for r in records if r['record_id'] not in path['removed_ids']]
            path.update(score(remaining, reference, injected))
        by_actions = {tuple(p['actions']): p for p in terminals}
        # Replay coverage and original scorer agreement are independent checks.
        for policy, result in archived[i]['policies'].items():
            path = by_actions[tuple(e['action'] for e in result['events'])]
            for new, old in [('f1', 'f1'), ('preservation', 'correct_preservation'),
                             ('correct_lost', 'correct_lost'), ('injected_removed', 'injected_removed')]:
                assert abs(path[new] - result[old]) < 1e-12, (name, i, policy, new)
            old_return = sum(.95 ** j * event['reward'] for j, event in enumerate(result['events']))
            assert abs(path['discounted_return'] - old_return) < 1e-12
            assert path['acquisitions'] == result['accounted_responses']
            assert path['removed_ids'] == sorted(set().union(*(set(e['removed_ids']) for e in result['events'])))
        baseline = score(records, reference, injected)
        best = min(terminals, key=lambda p: (-p['f1'], p['correct_lost'], p['acquisitions'], len(p['actions']), p['actions']))
        reward_best = max(terminals, key=lambda p: p['discounted_return'])
        reward_ties = [p for p in terminals if abs(p['discounted_return'] - reward_best['discounted_return']) < 1e-12]
        reachable = set().union(*(set(p['removed_ids']) for p in terminals))
        # Relaxation: allow arbitrary individual removals from the reachable
        # candidate union. It does not preserve repair-bundle feasibility.
        selective = score([r for r in records if r['record_id'] not in reachable & injected_ids], reference, injected)
        banks = {}
        for s in ('deletion', 'augmentation', 'union'):
            for family in ('type', 'source', 'all'):
                flagged, conflicts = bank_flags(records, queue,
                    {'deletion', 'augmentation'} if s == 'union' else {s},
                    {'type', 'source'} if family == 'all' else {family})
                banks[s + '/' + family] = dict(flagged_ids=sorted(flagged),
                    correct_flagged=len(flagged & correct_ids), injected_flagged=len(flagged & injected_ids), conflicts=conflicts)
        full = [p for p in terminals if p['acquisitions'] == 4]
        drained = [p for p in full if not p['pending_feasible_repair']]
        row = dict(episode=i, terminal_paths=len(terminals),
                   unique_final_graphs=len({tuple(p['removed_ids']) for p in terminals}),
                   full_budget_final_graphs=len({tuple(p['removed_ids']) for p in full}),
                   full_budget_drained_final_graphs=len({tuple(p['removed_ids']) for p in drained}),
                   stop=baseline, executable_oracle=best, selective_candidate_upper_bound=selective,
                   reward_optimum=reward_best,
                   reward_optimum_f1_range=[min(p['f1'] for p in reward_ties), max(p['f1'] for p in reward_ties)],
                   full_budget_return_range=[min(p['discounted_return'] for p in full), max(p['discounted_return'] for p in full)],
                   full_budget_proxy_auc10_range=[min(p['proxy_auc10'] for p in full), max(p['proxy_auc10'] for p in full)],
                   late_permission_paths=sum(p['late_permissions'] > 0 for p in terminals), banks=banks)
        for s, other in [('deletion', 'augmentation'), ('augmentation', 'deletion')]:
            unique = set(banks[s + '/all']['flagged_ids']) - set(banks[other + '/all']['flagged_ids'])
            row[s + '_unique_injected_flags'] = len(unique & injected_ids)
            row[s + '_unique_correct_flags'] = len(unique & correct_ids)
        episodes.append(row)
        details.append(dict(episode=i, paths=terminals))
    mean = lambda fn: statistics.mean(fn(e) for e in episodes)
    summary = dict(round=name, documents=len(public), episodes=len(episodes),
                   terminal_paths=sum(e['terminal_paths'] for e in episodes),
                   stop_f1=mean(lambda e: e['stop']['f1']),
                   executable_oracle_f1=mean(lambda e: e['executable_oracle']['f1']),
                   selective_upper_f1=mean(lambda e: e['selective_candidate_upper_bound']['f1']),
                   reward_optimum_f1=mean(lambda e: e['reward_optimum']['f1']),
                   reward_optimum_f1_tie_range=[mean(lambda e: e['reward_optimum_f1_range'][j]) for j in (0, 1)],
                   oracle_correct_lost=sum(e['executable_oracle']['correct_lost'] for e in episodes),
                   oracle_injected_removed=sum(e['executable_oracle']['injected_removed'] for e in episodes),
                   oracle_mean_acquisitions=mean(lambda e: e['executable_oracle']['acquisitions']),
                   oracle_minus_acquire_then_repair_pp=100 * (mean(lambda e: e['executable_oracle']['f1']) - statistics.mean(e['policies']['acquire_then_repair']['f1'] for e in archived)),
                   episodes_with_full_budget_final_variation=sum(e['full_budget_final_graphs'] > 1 for e in episodes),
                   episodes_with_full_budget_drained_variation=sum(e['full_budget_drained_final_graphs'] > 1 for e in episodes),
                   episodes_with_full_budget_return_variation=sum(e['full_budget_return_range'][1] - e['full_budget_return_range'][0] > 1e-12 for e in episodes),
                   late_permission_paths=sum(e['late_permission_paths'] for e in episodes))
    summary['banks'] = {k: {metric: sum(e['banks'][k][metric] for e in episodes)
                           for metric in ('correct_flagged', 'injected_flagged', 'conflicts')}
                        for k in episodes[0]['banks']}
    summary['unique_strategy_flags'] = {k: sum(e[k] for e in episodes)
        for k in ('deletion_unique_injected_flags', 'augmentation_unique_injected_flags',
                  'deletion_unique_correct_flags', 'augmentation_unique_correct_flags')}
    return dict(summary=summary, episodes=episodes), details


def main():
    results = []
    for name in ('paper2_docred_v2', 'paper2_docred_v2_round2'):
        result, paths = run_round(name)
        results.append(result)
        (HERE / (name + '_all_paths.json')).write_text(json.dumps(paths, indent=2) + '\n')
        print(json.dumps(result['summary'], indent=2), flush=True)
    report = dict(scope='Post-hoc development diagnostics, same twenty documents in both rounds; references only for scoring. No learned-policy or natural-error claim.',
                  actual_api_requests=0, trained_models=0, formal_gate_changed=False, results=results)
    (HERE / 'loop_diagnostics.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
