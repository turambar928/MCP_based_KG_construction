"""Public-observation archive replay. This is not a trained RL environment."""
from collections import defaultdict
from copy import deepcopy
import time

ACTIONS = ('acquire_deletion', 'acquire_augmentation', 'repair', 'stop')
UNKNOWN_TYPES = {'', 'unknown'}


def usable(record):
    if record.get('missing_endpoint', False):
        return 'missing_endpoint'
    if any(str(record.get(k) or '').strip().lower() in UNKNOWN_TYPES
           for k in ('subject_type', 'object_type')):
        return 'missing_type'
    return 'typed'


def pattern(record):
    return tuple(str(record.get(k) or '').strip()
                 for k in ('subject_type', 'relation', 'object_type'))


class ArchiveReplay:
    """Four actions, aggregate public observations, no reward or reference labels.

    Acquisition loads an entire archived strategy bank, not one LLM request.
    Six decisions suffice for both acquisitions, two removals and explicit stop.
    """
    def __init__(self, records, packets, response_counts, horizon=6):
        self.initial = [{k:deepcopy(r[k]) for k in
                         ('record_id','subject_type','relation','object_type','missing_endpoint')
                         if k in r} for r in records]
        assert len({r['record_id'] for r in self.initial}) == len(self.initial)
        self.packets = deepcopy(packets)
        self.response_counts = dict(response_counts)
        self.horizon = horizon
        self.reset()

    def reset(self):
        self.records = deepcopy(self.initial)
        self.active = {}
        self.acquired = set()
        self.removed = {}
        self.steps = 0
        self.done = False
        self.events = []
        return self.observe()

    def _index(self):
        index = defaultdict(lambda: {'allowed': [], 'forbidden': []})
        for rid, r in self.active.items():
            index[tuple(r['pattern'])][r['kind']].append(rid)
        return index

    def scan(self, records=None):
        index = self._index()
        rows = []
        for r in self.records if records is None else records:
            state = usable(r)
            match = index.get(pattern(r), {'allowed': [], 'forbidden': []}) if state == 'typed' else {'allowed': [], 'forbidden': []}
            allowed, forbidden = bool(match['allowed']), bool(match['forbidden'])
            rows.append({'record_id':r['record_id'], 'status':state,
                         'allowed_rule_ids':sorted(match['allowed']),
                         'forbidden_rule_ids':sorted(match['forbidden']),
                         'conflict':allowed and forbidden,
                         'violation':forbidden and not allowed})
        return rows

    def available_actions(self):
        if self.done:
            return {a:False for a in ACTIONS}
        hits = sum(r['violation'] for r in self.scan())
        return {'acquire_'+s:s not in self.acquired and bool(self.packets[s])
                for s in ('deletion','augmentation')} | {
                    'repair':0 < hits < len(self.records), 'stop':True}

    def observe(self):
        rows = self.scan()
        return {'version':'archive-policy-interface-v1', 'records':len(rows),
                'typed_records':sum(r['status']=='typed' for r in rows),
                'untyped_records':sum(r['status']!='typed' for r in rows),
                'flagged_records':sum(r['violation'] for r in rows),
                'conflicts':sum(r['conflict'] for r in rows),
                'active_rules':len(self.active), 'acquired':sorted(self.acquired),
                'remaining_decisions':max(0,self.horizon-self.steps),
                'mask':self.available_actions()}

    def step(self, action):
        if action not in ACTIONS or not self.available_actions()[action]:
            raise ValueError('Unavailable action: '+str(action))
        start = time.perf_counter()
        before = self.observe()
        event = {'step':self.steps, 'action':action, 'before':before,
                 'activated_rule_ids':[], 'removed_records':[],
                 'late_permissions':[], 'archived_responses_loaded':0,
                 'actual_api_calls':0}
        if action.startswith('acquire_'):
            strategy = action.removeprefix('acquire_')
            for rule in self.packets[strategy]:
                rid = rule['rule_id']
                if rid not in self.active:
                    self.active[rid] = {'kind':rule['kind'], 'pattern':tuple(rule['pattern']), 'sources':[]}
                    event['activated_rule_ids'].append(rid)
                entry = self.active[rid]
                assert entry['kind']==rule['kind'] and entry['pattern']==tuple(rule['pattern'])
                origins = {tuple(sorted(s.items())):s for s in entry['sources']+rule['sources']}
                entry['sources'] = list(origins.values())
            self.acquired.add(strategy)
            event['archived_responses_loaded'] = self.response_counts[strategy]
            # A later permission cannot undo a deletion: report the hazard explicitly.
            event['late_permissions'] = [r for r in self.scan(list(self.removed.values()))
                                          if r['allowed_rule_ids']]
        elif action == 'repair':
            ids = {r['record_id'] for r in self.scan() if r['violation']}
            assert len(ids)<len(self.records), 'Refuse destructive emptying'
            event['removed_records'] = [deepcopy(r) for r in self.records if r['record_id'] in ids]
            self.removed.update({r['record_id']:deepcopy(r) for r in event['removed_records']})
            self.records = [r for r in self.records if r['record_id'] not in ids]
        else:
            self.done = True
        self.steps += 1
        self.done |= self.steps >= self.horizon
        event['after'] = self.observe()
        event['detections'] = [r for r in self.scan() if r['allowed_rule_ids'] or r['forbidden_rule_ids']]
        event['wall_seconds'] = time.perf_counter()-start
        self.events.append(event)
        return self.observe(), self.done, deepcopy(event)


def choose(observation, order, timing):
    """Schedule accepts only aggregate public observations, never records/labels."""
    mask = observation['mask']
    if timing=='immediate' and mask['repair']:
        return 'repair'
    for strategy in order:
        if mask['acquire_'+strategy]:
            return 'acquire_'+strategy
    return 'repair' if mask['repair'] else 'stop'
