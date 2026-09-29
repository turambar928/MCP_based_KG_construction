"""Frozen 20-document development gate. No test selection or reference-aware generation."""
import concurrent.futures,json,os,random,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper2_docred_v2_round2.generation import request,compile_response,MODEL
from exps.paper2_docred_v2_round2.environment import SourceRuleEnvironment,ACTIONS
from exps.paper2_docred_v2_round2.prepare import prepare
from exps.paper2_docred.prepare import digest,write_once
from exps.paper1_online_recovery.run import execute,sha,read
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'paper2_docred'


def tasks():
    public=json.loads((HERE/'local/pilot_public.json').read_text())
    rel=json.loads((OLD/'relations.json').read_text());rows=[]
    for x in public:
        for s in ['deletion','augmentation']:
            p=request(x['document'],s,rel,x['records'])
            rows.append(dict(case_id=x['document']['case_id'],arm=s,request=p,prompt_sha256=digest(p)))
    return public,rel,rows


def freeze():
    prepare();public,rel,rows=tasks()
    import unittest
    from exps.paper2_docred_v2_round2 import test_contracts
    result=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromModule(test_contracts))
    assert result.wasSuccessful()
    write_once(HERE/'protocol.json',dict(version='source-evidence-v2-round2',model=MODEL,
        scope='Controlled reference recovery; document-specific source constraints; original text only. Not natural factual accuracy.',
        public_features=14,actions=list(ACTIONS),response_budget=4,horizon=10,candidate_cap=20,discount=.95,
        reward='0.5 fixed-post-rule graph delta + 0.5 coverage delta -0.004 acquisition -0.00002 deleted -edit_created/N',
        emptying_protection=True,coverage_denominator='initial records',max_development_rounds=2,
        pilot='first 10 fixed dev pairs; 20 documents; no favorable replacement',
        gate='Contract tests pass; source rules cause actual removal in >=2 episodes; at least one fixed non-stop schedule improves aggregate reference F1 over stop without reducing correct retention below 0.99. This conservative safety criterion is fixed before calls; not an RL advantage requirement.',
        failure_branch='Do not expand training. Retain results; at most one separately versioned development revision.',
        formal_if_pass=dict(algorithms=['DDQN','DQN','legacy-reward DDQN'],seeds=list(range(20000,20010)),episodes_per_seed=250,
            shared_cached_packets=True,comparators=['stop','acquire_then_repair','repair_asap','uniform_feasible','same_model_two_call_simple'],
            primary='DDQN versus DQN/acquire_then_repair/repair_asap/simple; F1 and correct preservation; Holm across eight tests',
            inference_calls='zero for cached replay; generation requests separately measured'),
        human_review='deferred; quote matching validates executable provenance only'))
    deps=[HERE/n for n in ['environment.py','generation.py','prepare.py','pilot.py','test_contracts.py','amendment.json','protocol.json','pilot_membership.json']]
    deps += [OLD/'environment.py',OLD/'generation.py',ROOT/'exps/paper1_online_recovery/run.py']
    write_once(HERE/'pilot_manifest.json',dict(code={str(p.relative_to(ROOT)):sha(p) for p in deps},requests=[dict(case_id=t['case_id'],arm=t['arm'],sha256=digest(t['request'])) for t in rows],contract_tests=result.testsRun))


def collect():
    manifest=json.loads((HERE/'pilot_manifest.json').read_text())
    assert all(sha(ROOT/p)==h for p,h in manifest['code'].items()),'Frozen code changed'
    public,rel,t=tasks();assert [dict(case_id=x['case_id'],arm=x['arm'],sha256=digest(x['request'])) for x in t]==manifest['requests']
    dest=HERE/'local/pilot_responses.jsonl';done=read(dest);seen={(r['case_id'],r['arm']) for r in done}
    assert len(seen)==len(done);pending=[x for x in t if (x['case_id'],x['arm']) not in seen];random.Random(20260929).shuffle(pending)
    config=(ROOT/'apis').read_text();secret=re.search(r'sk-[A-Za-z0-9_-]+',config).group();url=re.search(r'https?://[^\s\x27\x22<>]+',config).group().rstrip('/');credentials=(secret,url if url.endswith('/v1') else url+'/v1')
    with concurrent.futures.ThreadPoolExecutor(2) as pool,dest.open('a') as f:
        for off in range(0,len(pending),2):
            wave=pending[off:off+2];failed=0
            for fut in concurrent.futures.as_completed([pool.submit(execute,x,'reextraction',credentials) for x in wave]):
                r=fut.result();r['transport_status']='error' if r['status']=='transport_error' else 'ok';failed+=r['transport_status']=='error'
                f.write(json.dumps(r,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno());done.append(r)
                print('v2 pilot',len(done),'/40',r['arm'],r['transport_status'],flush=True)
            if failed==len(wave):raise RuntimeError('Transport wave failed; stop preserving outcomes')
    analyze()


def metrics(records,reference,injected):
    predicted={(r['source_document_id'],r['head_entity_id'],r['relation'],r['tail_entity_id']) for r in records}
    tp=len(predicted & reference);den=len(predicted)+len(reference)
    return dict(f1=2*tp/den if den else 1.,correct_preservation=tp/len(reference) if reference else 1.,
                correct_lost=len(reference-predicted),injected_removed=len(injected-predicted),injected_total=len(injected),remaining=len(predicted))


def analyze():
    public,rel,_=tasks();rows=read(HERE/'local/pilot_responses.jsonl');lookup={(r['case_id'],r['arm']):r for r in rows};assert len(lookup)==len(rows)==40
    packets={};rules=[];audit=[]
    for x in public:
        d=x['document'];cid=d['case_id']
        for strategy in ['deletion','augmentation']:
            row=lookup[cid,strategy];ok,compiled,rejected=compile_response(row['raw_response'],d,x['records'],rel)
            p=dict(packet_id=cid+':'+strategy,source_document_id=cid,strategy=strategy,parse_success=ok,rules=compiled,rejections=[{'ordinal':r.get('ordinal'),'reason':r['reason']} for r in rejected],provenance=dict(response_sha256=digest(row['raw_response']),request_sha256=row['request_sha256'],model=MODEL))
            packets[cid,strategy]=p;rules.extend(compiled);audit.append(dict(case_id=cid,strategy=strategy,rejections=rejected))
    # Scoring file is opened only after generation/compilation has ended.
    references={r['case_id']:r for r in json.loads((HERE/'local/pilot_scorer_only.json').read_text())}
    by_id={x['document']['case_id']:x for x in public};pairs=json.loads((HERE/'pilot_membership.json').read_text())['pairs'];episodes=[]
    for i,ids in enumerate(pairs):
        reference={(c,*t) for c in ids for t in references[c]['reference']};injected={(c,*t) for c in ids for t in references[c]['injected']}
        records=sum([by_id[c]['records'] for c in ids],[]);q={s:[packets[c,s] for c in ids] for s in ['deletion','augmentation']};out={}
        for policy in ['stop','acquire_then_repair','repair_asap','uniform_feasible']:
            env=SourceRuleEnvironment(records,q);rng=random.Random(20260929+i);source_removed=set()
            while not env.done:
                mask=env.mask()
                if policy=='stop':action='stop'
                elif policy=='uniform_feasible':action=rng.choice([a for a,m in zip(ACTIONS,mask) if m])
                elif policy=='repair_asap' and mask[2]:action='repair'
                else:action=next((a for a,m in zip(ACTIONS[:2],mask[:2]) if m),'repair' if mask[2] else 'stop')
                source_flags={k for k,v in env.scan().items() if v['source_contradicted'] and v['violation']}
                _,_,_,event=env.step(action);source_removed.update(set(event['removed_ids'])&source_flags)
            out[policy]=dict(**metrics(env.records,reference,injected),accounted_responses=sum(env.acquired.values()),source_removed=sorted(source_removed),events=env.events)
        episodes.append(dict(episode=i,documents=ids,policies=out))
    summary={p:{k:sum(e['policies'][p][k] for e in episodes)/len(episodes) for k in ['f1','correct_preservation','accounted_responses']} for p in episodes[0]['policies']}
    source_episodes=sum(any(e['policies'][p]['source_removed'] for p in e['policies']) for e in episodes)
    effective=any(v['f1']>summary['stop']['f1'] and v['correct_preservation']>=.99 for p,v in summary.items() if p!='stop')
    result=dict(status='development_only',documents=20,episodes=10,actual_requests=sum(r['calls'] for r in rows),transport_failures=sum(r['transport_status']=='error' for r in rows),parse_success=sum(p['parse_success'] for p in packets.values()),
                rules=dict(type=sum(r['family']=='type' for r in rules),source_supported=sum(r.get('verdict')=='supported' for r in rules),source_contradicted=sum(r.get('verdict')=='contradicted' for r in rules)),
                source_repair_episodes=source_episodes,summary=summary,gate_passed=source_episodes>=2 and effective,
                human_review=False,semantic_scope='reference recovery and injected-item removal, not natural factual correctness')
    write_once(HERE/'pilot_results.json',result);write_once(HERE/'pilot_traces.json',episodes);write_once(HERE/'pilot_packets_public.json',list(packets.values()));write_once(HERE/'local/compilation_audit.json',audit)
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':
    {'freeze':freeze,'collect':collect,'analyze':analyze}[sys.argv[1]]()
