"""Response-level generated-rule scheduler; no reference labels or network access.

Implements generated-rule-scheduler-design-v1. This is an implementation, not
evidence of effective generated rules or of a trained policy.
"""
from collections import defaultdict
from copy import deepcopy
from hashlib import sha256

ACTIONS = ('acquire_deletion', 'acquire_augmentation', 'repair', 'stop')
FEATURES = (
    'remaining_record_fraction', 'typed_record_fraction', 'untyped_record_fraction',
    'flagged_record_fraction', 'conflict_record_fraction', 'covered_record_fraction',
    'active_rule_fraction', 'remaining_budget_fraction', 'remaining_horizon_fraction',
    'deletion_acquired_fraction', 'augmentation_acquired_fraction',
    'last_packet_parse_success', 'last_packet_executable_fraction', 'removed_record_fraction',
)
RECORD_KEYS = {'record_id', 'subject_type', 'relation', 'object_type', 'missing_endpoint'}
PACKET_KEYS = {'packet_id', 'source_document_id', 'strategy', 'parse_success',
               'rules', 'provenance', 'rejections'}


def pattern(record):
    return tuple(record.get(k, '') for k in ('subject_type', 'relation', 'object_type'))


def typed(record):
    return (not record.get('missing_endpoint', False)
            and all(str(record.get(k, '')).strip().lower() not in ('', 'unknown')
                    for k in ('subject_type', 'object_type')))


class GeneratedRuleEnvironment:
    def __init__(self, records, packets):
        if not records or any(set(r) - RECORD_KEYS for r in records):
            raise ValueError('Require nonempty public records with no extra/label fields')
        if any(not isinstance(r.get('record_id'), str) for r in records):
            raise ValueError('Record IDs must be strings')
        if len({r['record_id'] for r in records}) != len(records):
            raise ValueError('Duplicate record ID')
        if set(packets) != {'deletion', 'augmentation'}:
            raise ValueError('Both public strategy queues are required')
        self.initial = deepcopy(records)
        self.queues = deepcopy(packets)
        for strategy, queue in self.queues.items():
            if len(queue) != 2:
                raise ValueError('Exactly two document responses per strategy')
            for packet in queue:
                if set(packet) - PACKET_KEYS or packet.get('strategy') != strategy:
                    raise ValueError('Unexpected packet fields or strategy')
                if not isinstance(packet.get('parse_success'), bool):
                    raise ValueError('Explicit parsing status required')
                if not packet['parse_success'] and packet['rules']:
                    raise ValueError('Failed packet cannot have executable rules')
                if len(packet['rules']) > 20:
                    raise ValueError('Compiler must enforce 20-candidate response cap')
                for rule in packet['rules']:
                    if set(rule) != {'kind', 'pattern'}:
                        raise ValueError('Executable rule must contain kind and pattern only')
                    if rule['kind'] not in ('allowed', 'forbidden') or len(rule['pattern']) != 3:
                        raise ValueError('Invalid compiled rule')
                    if any(not isinstance(x, str) or not x.strip() for x in rule['pattern']):
                        raise ValueError('Rule terms must be nonempty strings')
            queue.sort(key=lambda p: sha256(p['source_document_id'].encode()).hexdigest())
        docs = [[p['source_document_id'] for p in self.queues[s]] for s in self.queues]
        if docs[0] != docs[1] or len(set(docs[0])) != 2:
            raise ValueError('Strategies must share the same two distinct source documents')
        ids = [p['packet_id'] for q in self.queues.values() for p in q]
        if len(set(ids)) != 4:
            raise ValueError('Packet IDs must be unique')
        self.reset()

    def reset(self):
        self.records = deepcopy(self.initial)
        self.active = {}
        self.removed = {}
        self.acquired = dict(deletion=0, augmentation=0)
        self.steps = 0
        self.done = False
        self.last_success = 0.
        self.last_executable = 0.
        self.events = []
        return self.observe()

    def scan(self, records=None):
        index = defaultdict(set)
        for kind, terms in self.active:
            index[terms].add(kind)
        result = {}
        for r in self.records if records is None else records:
            kinds = index[pattern(r)] if typed(r) else set()
            result[r['record_id']] = {
                'typed': typed(r), 'violation': kinds == {'forbidden'},
                'conflict': len(kinds) == 2, 'covered': len(kinds) == 1,
                'allowed': 'allowed' in kinds,
            }
        return result

    def potentials(self):
        n = len(self.initial)
        return (1 - sum(r['violation'] for r in self.scan().values()) / n,
                sum(r['covered'] for r in self.scan(self.initial).values()) / n)

    def mask(self):
        if self.done:
            return [False] * 4
        count = sum(self.acquired.values())
        violations = sum(r['violation'] for r in self.scan().values())
        return [count < 4 and self.acquired[s] < 2 for s in ('deletion', 'augmentation')] + [
            0 < violations < len(self.records), True]

    def observe(self):
        rows = list(self.scan().values())
        n = len(self.initial)
        values = [len(rows)/n, sum(r['typed'] for r in rows)/n,
                  sum(not r['typed'] for r in rows)/n,
                  sum(r['violation'] for r in rows)/n,
                  sum(r['conflict'] for r in rows)/n,
                  sum(r['covered'] for r in rows)/n, len(self.active)/80,
                  (4-sum(self.acquired.values()))/4, (10-self.steps)/10,
                  self.acquired['deletion']/2, self.acquired['augmentation']/2,
                  self.last_success, self.last_executable, len(self.removed)/n]
        return {'features': dict(zip(FEATURES, values)), 'mask': self.mask()}

    def step(self, action):
        if action not in ACTIONS or not self.mask()[ACTIONS.index(action)]:
            raise ValueError('Unavailable action')
        before = self.potentials()
        prior_flags = {k for k, v in self.scan().items() if v['violation']}
        prior_allowed_removed = {k for k,v in self.scan(list(self.removed.values())).items() if v['allowed']}
        event = {'action': action, 'packet_id': None, 'acquired_responses': 0,
                 'removed_ids': [], 'late_permission_ids': [], 'actual_api_calls': 0}
        if action.startswith('acquire_'):
            strategy = action.removeprefix('acquire_')
            packet = self.queues[strategy][self.acquired[strategy]]
            self.acquired[strategy] += 1
            event.update(packet_id=packet['packet_id'], acquired_responses=1)
            self.last_success = float(packet['parse_success'])
            self.last_executable = len(packet['rules'])/20
            for rule in packet['rules']:
                key = (rule['kind'], tuple(rule['pattern']))
                self.active.setdefault(key, set()).add(packet['packet_id'])
            event['late_permission_ids'] = sorted(
                k for k,v in self.scan(list(self.removed.values())).items()
                if v['allowed'] and k not in prior_allowed_removed)
        elif action == 'repair':
            event['removed_ids'] = sorted(prior_flags)
            self.removed.update({r['record_id']: r for r in self.records if r['record_id'] in prior_flags})
            self.records = [r for r in self.records if r['record_id'] not in prior_flags]
        else:
            self.done = True
        after = self.potentials()
        new = {k for k,v in self.scan().items() if v['violation']} - prior_flags
        reward = (0.5*(after[0]-before[0]) + 0.5*(after[1]-before[1])
                  - 0.004*event['acquired_responses'] - 0.00002*len(event['removed_ids'])
                  - len(new)/len(self.initial)) if action != 'stop' else 0.
        event.update(reward=reward, potentials_before=before, potentials_after=after,
                     acquisition_revealed_ids=sorted(new) if action.startswith('acquire_') else [],
                     edit_created_ids=sorted(new) if action == 'repair' else [])
        self.steps += 1
        self.done |= self.steps >= 10
        event['terminal'] = self.done
        self.events.append(deepcopy(event))
        return self.observe(), reward, self.done, event


def masked_bootstrap(next_values, next_masks, terminal):
    """Scalar test/reference helper: never bootstrap a terminal transition."""
    return 0. if terminal or not any(next_masks) else max(
        v for v,m in zip(next_values, next_masks) if m)
