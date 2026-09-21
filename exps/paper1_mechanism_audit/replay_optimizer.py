#!/usr/bin/env python3
"""Execute the actual sequential optimizer on frozen model proposals.

No API access. No tuning against held-out outcomes. Input-derived recommendations
are per-relation atomic differences between structural input and raw proposal.
Both optimizer variants use the published default cost/constraint/horizon values.
The uniform variant only substitutes an always-on uniform router for the old MLP.
"""
from __future__ import annotations
import sys,json,hashlib,time
from collections import defaultdict,Counter
from dataclasses import asdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_mechanism_audit.protocol import *
from exps.paper1_repair_benchmark.run_benchmark import parse_triples
from content_enhancement.constraint_optimizer import MultiScaleConstraintOptimizer,RouterOutput


class AuditedOptimizer(MultiScaleConstraintOptimizer):
    def __init__(self,uniform=False):
        super().__init__();self.uniform=uniform;self.trials=[];self._depth=0
    def route(self,profile):
        if self.uniform:return RouterOutput(1.,{s:1/3 for s in ['entity','graph','context']},'always_uniform')
        return super().route(profile)
    def _apply_candidate(self,triples,candidate):
        before=[dict(t) for t in triples];outer=self._depth==0;self._depth+=1
        try: after=super()._apply_candidate(triples,candidate)
        finally:self._depth-=1
        if outer:self.trials.append({'before_triples':before,'after_triples':after})
        return after
    def _check_constraints(self,before,after,candidate):
        self.trials[-1].update({'before_profile':asdict(before),'after_profile':asdict(after)})
        return super()._check_constraints(before,after,candidate)


def recommendations(initial,proposed):
    grouped_in=defaultdict(list);grouped_out=defaultdict(list)
    for t in initial:grouped_in[t['relation']].append(t)
    for t in proposed:grouped_out[t['relation']].append(t)
    result=[]
    for relation in sorted(grouped_in.keys()|grouped_out.keys()):
        before=Counter(key(t) for t in grouped_in[relation]);after=Counter(key(t) for t in grouped_out[relation])
        actions=[]
        for op,diff in [('delete',before-after),('add',after-before)]:
            for triple,n in sorted(diff.items()):
                for _ in range(n):actions.append({'action':op,'triple':dict(zip(['head','relation','tail'],triple))})
        if actions:result.append({'type':'source_proposal','module':'context','confidence':0.7,'implementation':{'actions':actions}})
    return result


def replay(inp,proposed,uniform=False):
    initial=preprocess(inp);rec=recommendations(initial,proposed);opt=AuditedOptimizer(uniform)
    start=time.perf_counter()
    final,applied,audit=opt.optimize_and_apply([{'name':inp.required_document_node}],initial,rec,inp.source_evidence)
    assert len(opt.trials)==len(audit['decisions'])
    for decision,trial in zip(audit['decisions'],opt.trials):decision.update(trial)
    return {'triples':final,'audit':audit,'recommendations':rec,'applied_count':len(applied),
            'cpu_seconds':time.perf_counter()-start,'runtime_sha256':hashlib.sha256((ROOT/'content_enhancement/constraint_optimizer.py').read_bytes()).hexdigest()}


def main():
    cases=[c for c in read_jsonl(BENCH/'benchmark.jsonl') if c['split']=='test']
    paths={'controlled':BENCH/'predictions_ours.jsonl','natural':EXT/'natural_repairs_full_claude.jsonl'}
    extraction={r['case_id']:r for r in read_jsonl(EXT/'natural_extraction_claude.jsonl')}
    dest=HERE/'optimizer_replay.jsonl'
    with dest.open('w') as handle:
        for stream,path in paths.items():
            proposals={r['case_id']:r for r in read_jsonl(path)}
            for i,c in enumerate(cases):
                cid=c['case_id'];inp=public_input(c,c['corrupted_triples'] if stream=='controlled' else extraction[cid]['triples'])
                proposal,status=parse_triples(proposals[cid]['raw_responses'][-1])
                for uniform in [False,True]:
                    result=replay(inp,proposal,uniform)
                    handle.write(json.dumps({'case_id':cid,'stream':stream,'variant':'uniform' if uniform else 'learned',
                                             'proposal_status':status,'input_sha256':digest(inp.payload()),**result},ensure_ascii=False)+'\n')
                if (i+1)%75==0:print(stream,i+1,flush=True)
    print(dest,flush=True)
if __name__=='__main__':main()
