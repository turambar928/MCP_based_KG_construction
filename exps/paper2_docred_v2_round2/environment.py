"""Versioned source-evidence constraints with fixed-rule reward accounting."""
from copy import deepcopy
from hashlib import sha256
from exps.paper2_docred.environment import GeneratedRuleEnvironment, ACTIONS, FEATURES, typed, pattern

VERSION='docred-source-constraints-v2-round2'
RECORD_KEYS={'record_id','subject_type','relation','object_type','missing_endpoint',
             'source_document_id','head_entity_id','tail_entity_id'}


class SourceRuleEnvironment(GeneratedRuleEnvironment):
    def __init__(self,records,packets,reward_mode='fixed_rule'):
        if reward_mode not in ('fixed_rule','legacy'):raise ValueError('Unknown reward mode')
        if any(set(r)-RECORD_KEYS for r in records):raise ValueError('Unexpected public record fields')
        if any(not all(isinstance(r.get(k),str) for k in ['record_id','source_document_id','head_entity_id','tail_entity_id']) for r in records):raise ValueError('Missing public identity')
        if len({r['record_id'] for r in records})!=len(records):raise ValueError('Duplicate records')
        if set(packets)!={'deletion','augmentation'}:raise ValueError('Two queues required')
        self.initial=deepcopy(records);self.queues=deepcopy(packets);self.reward_mode=reward_mode
        self.identities={r['record_id']:r['source_document_id'] for r in self.initial}
        for strategy,queue in self.queues.items():
            if len(queue)!=2:raise ValueError('Two document responses per strategy required')
            for p in queue:
                if set(p)-{'packet_id','source_document_id','strategy','parse_success','rules','provenance','rejections'}:raise ValueError('Extra packet fields')
                if p['strategy']!=strategy or type(p['parse_success']) is not bool:raise ValueError('Invalid packet metadata')
                if len(p['rules'])>20 or (not p['parse_success'] and p['rules']):raise ValueError('Invalid compiled packet')
                for r in p['rules']:
                    if r.get('family')=='type':
                        if set(r)!={'family','kind','pattern'} or r['kind'] not in ('allowed','forbidden') or len(r['pattern'])!=3:raise ValueError('Invalid type rule')
                    elif r.get('family')=='source':
                        if set(r)!={'family','verdict','record_id','evidence'} or r['verdict'] not in ('supported','contradicted') or not r['evidence']:raise ValueError('Invalid source rule')
                        if self.identities.get(r['record_id'])!=p['source_document_id']:raise ValueError('Cross-document or absent target')
                    else:raise ValueError('Unknown rule family')
            queue.sort(key=lambda p:sha256(p['source_document_id'].encode()).hexdigest())
        docs=[[p['source_document_id'] for p in q] for q in self.queues.values()]
        if docs[0]!=docs[1] or len(set(docs[0]))!=2:raise ValueError('Unmatched source queues')
        if not {r['source_document_id'] for r in records}<=set(docs[0]):raise ValueError('Records outside episode')
        if len({p['packet_id'] for q in self.queues.values() for p in q})!=4:raise ValueError('Duplicate packet ID')
        self.reset()

    def scan(self,records=None):
        result={}
        for r in self.records if records is None else records:
            terms=pattern(r)
            ta=('type','allowed',*terms) in self.active if typed(r) else False
            tf=('type','forbidden',*terms) in self.active if typed(r) else False
            support=('source','supported',r['record_id']) in self.active
            contra=('source','contradicted',r['record_id']) in self.active
            # Type permission is only compatibility, not positive factual evidence.
            conflict=(ta and tf) or (support and contra) or (support and tf)
            violation=not conflict and (contra or (tf and not ta and not support))
            result[r['record_id']]=dict(typed=typed(r),violation=bool(violation),conflict=bool(conflict),
                covered=bool((ta or tf or support or contra) and not conflict),
                allowed=bool(support or (ta and not contra)),source_supported=support,source_contradicted=contra)
        return result

    def potentials(self):
        n=max(1,len(self.initial))
        return (1-sum(r['violation'] for r in self.scan().values())/n,
                sum(r['covered'] for r in self.scan(self.initial).values())/n)

    def observe(self):
        rows=list(self.scan().values());n=max(1,len(self.initial))
        values=[len(rows)/n,sum(r['typed'] for r in rows)/n,sum(not r['typed'] for r in rows)/n,
                sum(r['violation'] for r in rows)/n,sum(r['conflict'] for r in rows)/n,
                sum(r['covered'] for r in rows)/n,len(self.active)/80,(4-sum(self.acquired.values()))/4,
                (10-self.steps)/10,self.acquired['deletion']/2,self.acquired['augmentation']/2,
                self.last_success,self.last_executable,len(self.removed)/n]
        return {'features':dict(zip(FEATURES,values)),'mask':self.mask(),'version':VERSION}

    def step(self,action):
        if action not in ACTIONS or not self.mask()[ACTIONS.index(action)]:raise ValueError('Unavailable action')
        n=max(1,len(self.initial));before_records=deepcopy(self.records);old_potential=self.potentials()
        prior={k for k,v in self.scan().items() if v['violation']}
        allowed_removed={k for k,v in self.scan(list(self.removed.values())).items() if v['allowed']}
        event=dict(action=action,packet_id=None,acquired_responses=0,removed_ids=[],late_permission_ids=[],actual_api_calls=0)
        if action.startswith('acquire_'):
            strategy=action.removeprefix('acquire_');p=self.queues[strategy][self.acquired[strategy]]
            self.acquired[strategy]+=1;event.update(packet_id=p['packet_id'],acquired_responses=1)
            self.last_success=float(p['parse_success']);self.last_executable=len(p['rules'])/20
            for r in p['rules']:
                key=('type',r['kind'],*r['pattern']) if r['family']=='type' else ('source',r['verdict'],r['record_id'])
                self.active.setdefault(key,set()).add(p['packet_id'])
            event['late_permission_ids']=sorted(k for k,v in self.scan(list(self.removed.values())).items() if v['allowed'] and k not in allowed_removed)
        elif action=='repair':
            event['removed_ids']=sorted(prior)
            self.removed.update({r['record_id']:deepcopy(r) for r in self.records if r['record_id'] in prior})
            self.records=[r for r in self.records if r['record_id'] not in prior]
        else:self.done=True
        after=self.potentials();post_flags={k for k,v in self.scan().items() if v['violation']}
        fixed_before={k for k,v in self.scan(before_records).items() if v['violation']}
        edit_created=post_flags-fixed_before
        revealed=post_flags-prior if action.startswith('acquire_') else set()
        fixed_graph_delta=(len(fixed_before)-len(post_flags))/n
        graph_delta=fixed_graph_delta if self.reward_mode=='fixed_rule' else after[0]-old_potential[0]
        penalty=len(edit_created if self.reward_mode=='fixed_rule' else post_flags-prior)/n
        components=dict(graph=.5*graph_delta,coverage=.5*(after[1]-old_potential[1]),
                        acquisition_cost=-.004*event['acquired_responses'],edit_cost=-.00002*len(event['removed_ids']),introduced_penalty=-penalty)
        reward=sum(components.values()) if action!='stop' else 0.
        self.steps+=1;self.done|=self.steps>=10
        event.update(reward=reward,reward_mode=self.reward_mode,reward_components=components,
            acquisition_revealed_ids=sorted(revealed),edit_created_ids=sorted(edit_created),
            potentials_before=old_potential,potentials_after=after,fixed_rule_graph_delta=fixed_graph_delta,terminal=self.done)
        self.events.append(deepcopy(event))
        return self.observe(),reward,self.done,event
