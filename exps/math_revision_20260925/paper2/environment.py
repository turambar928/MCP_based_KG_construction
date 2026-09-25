"""Versioned controlled environment; legacy environment/checkpoints are immutable."""
from collections import Counter
import copy
from exps.paper2_cooptimization.run_experiment import *
from exps.paper2_cooptimization.run_experiment import Paper2CoOptimizationEnv as LegacyEnv

ENVIRONMENT_VERSION = 'identity-violations-v2'

class Paper2CoOptimizationEnv(LegacyEnv):
    def reset(self):
        self._edge_serial = 0
        result = super().reset()
        self._ensure_ids()
        return result

    def _ensure_ids(self):
        used = {r['_edge_id'] for r in self.graph.rels if '_edge_id' in r}
        for rel in self.graph.rels:
            if '_edge_id' not in rel:
                while f'e{self._edge_serial}' in used:
                    self._edge_serial += 1
                rel['_edge_id'] = f'e{self._edge_serial}'
                used.add(rel['_edge_id'])
                self._edge_serial += 1
        assert len({r['_edge_id'] for r in self.graph.rels}) == len(self.graph.rels)

    def violation_identities(self):
        self._ensure_ids()
        nodes = set(self.graph.nodes)
        connected = {r[k] for r in self.graph.rels for k in ('start_id','end_id') if r[k] in nodes}
        result = Counter({('isolated', n): 1 for n in nodes - connected})
        seen = set()
        for rel in self.graph.rels:
            identity = rel['_edge_id']
            key = tuple(rel[k] for k in ('start_id','relation_type','end_id'))
            if key in seen: result['duplicate', identity] += 1
            seen.add(key)
            if rel['relation_type'] not in ALLOWED_RELATIONS: result['invalid_relation', identity] += 1
            if rel['start_id'] not in nodes or rel['end_id'] not in nodes: result['dangling', identity] += 1
        return result

    def _repair_graph(self, action):
        before = self.violation_identities()
        saved = copy.deepcopy(self.graph)
        edits, _ = super()._repair_graph(action)
        if ((saved.nodes and not self.graph.nodes) or (saved.rels and not self.graph.rels)):
            self.graph = saved
            self._blocked_empty = True
            return 0, 0
        return edits, sum((self.violation_identities() - before).values())

    def step(self, action):
        before = self.violation_identities()
        before_joint = self.joint_quality()
        self._blocked_empty = False
        if not self.available_action_mask().any():
            return self.state(), 0., True, {'termination_reason':'no_feasible_action', 'action':ACTION_NAMES[action],
                'calls':0,'edits':0,'new_violations':0,'reward_components':{'quality_gain':0.,'calls':0.,'edits':0.,'new_violations':0.},
                'normalized_joint':self.normalized_joint_quality()}
        state, reward, done, info = super().step(action)
        after = self.violation_identities()
        introduced = after - before
        actual = sum(introduced.values())
        assert actual == info['new_violations']
        info['introduced_violation_ids'] = [[*k, n] for k,n in sorted(introduced.items())]
        info['reward_components'] = {'quality_gain': self.joint_quality()-before_joint,
            'calls':-self.call_penalty*info['calls'], 'edits':-self.edit_penalty*info['edits'],
            'new_violations':-self.new_violation_penalty*actual}
        assert abs(sum(info['reward_components'].values())-reward)<1e-10
        no_actions = not self.available_action_mask().any()
        info['termination_reason'] = ('destructive_empty_graph' if self._blocked_empty else
            'quality_target' if info['terminal_quality'] else 'budget' if self.step_index>=self.max_steps else
            'no_feasible_action' if no_actions else 'continue')
        return state, reward, done or no_actions or self._blocked_empty, info
