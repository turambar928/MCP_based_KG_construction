"""Coverage and schedule replay over archived rules. Zero network requests."""
import csv,gzip,hashlib,json,sys
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper2_rule_integration.runtime import ArchiveReplay,choose,usable,pattern
HERE=Path(__file__).resolve().parent
LINEAGE=ROOT/'exps/paper2_offline_revision/rule_lineage.jsonl.gz'
ARCHIVE=ROOT/'exps/rule_suggestions/per_item_rule_suggestions.jsonl'


def dump(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def write_gzip(path,rows):
    with path.open('wb') as f:
        with gzip.GzipFile(fileobj=f,mode='wb',filename='',mtime=0) as z:
            for r in rows:z.write((json.dumps(r,ensure_ascii=False)+'\n').encode())


def load_rules():
    with gzip.open(LINEAGE,'rt') as f:
        rules=[{k:r[k] for k in ('rule_id','kind','pattern','sources')} for r in map(json.loads,f)]
    packets={s:[{**r,'sources':[o for o in r['sources'] if o['strategy']==s]}
                for r in rules if any(o['strategy']==s for o in r['sources'])]
             for s in ('deletion','augmentation')}
    counts=Counter()
    with ARCHIVE.open() as f:
        for line in f:counts[json.loads(line)['strategy']]+=1
    return rules,packets,dict(counts)


def load_data():
    original=json.loads((ROOT/'data/rule_test_triples.json').read_text())
    records=[];labels={}
    for i,r in enumerate(original):
        rid=f'suite-{i:03d}'
        records.append({'record_id':rid,**{k:r[k] for k in ('subject_type','relation','object_type')},'missing_endpoint':False})
        labels[rid]={'original_id':r['triple_id'],'defective':r['expected_detection']!='pass'}
    data={'RuleTest-94':records};type_counts={};inputs=[ROOT/'data/rule_test_triples.json']
    for domain in ('政务','金融','环境'):
        np=ROOT/'data'/f'{domain}_nodes.csv';ep=ROOT/'data'/f'{domain}_relationships.csv';inputs += [np,ep]
        with np.open(encoding='utf-8-sig',newline='') as f:nrows=list(csv.DictReader(f))
        nodes={r['id']:r for r in nrows};assert len(nodes)==len(nrows)
        type_counts[domain]=dict(Counter(r['node_type'] for r in nrows))
        with ep.open(encoding='utf-8-sig',newline='') as f:edges=list(csv.DictReader(f))
        data[domain]=[{'record_id':f'{domain}-{i:06d}',
             'subject_type':nodes.get(r['start_id'],{}).get('node_type'),
             'relation':r['relation_type'],'object_type':nodes.get(r['end_id'],{}).get('node_type'),
             'missing_endpoint':r['start_id'] not in nodes or r['end_id'] not in nodes}
             for i,r in enumerate(edges)]
    return data,labels,inputs,type_counts


def main():
    rules,packets,counts=load_rules();data,labels,inputs,type_counts=load_data()
    write_gzip(HERE/'rules_public.jsonl.gz',rules)
    write_gzip(HERE/'records_public.jsonl.gz',({'dataset':name,**r} for name,rs in data.items() for r in rs))
    dump(HERE/'suite_labels_scorer_only.json',labels)
    coverage=[];rule_matches=[];record_matches=[]
    for name,records in data.items():
        valid=defaultdict(list)
        for r in records:
            if usable(r)=='typed':valid[pattern(r)].append(r['record_id'])
        vocab=[{pat[i] for pat in valid} for i in range(3)]
        for arm in ('deletion','augmentation','union'):
            bank=rules if arm=='union' else packets[arm]
            matches=0
            for r in bank:
                ids=valid.get(tuple(r['pattern']),[])
                status='matched' if ids else 'no_typed_records' if not valid else 'mapped_unmatched' if all(r['pattern'][i] in vocab[i] for i in range(3)) else 'unmapped_vocabulary'
                rule_matches.append({'dataset':name,'strategy':arm,'rule_id':r['rule_id'],'kind':r['kind'],'status':status,'record_ids':ids})
                matches+=bool(ids)
            env=ArchiveReplay(records,packets,counts)
            for strategy in ('deletion','augmentation') if arm=='union' else (arm,):env.step('acquire_'+strategy)
            scans=env.scan()
            record_matches.extend({'dataset':name,'strategy':arm,**r} for r in scans)
            row={'dataset':name,'strategy':arm,'records':len(records),'typed_records':len([r for r in records if usable(r)=='typed']),
                 'missing_type':sum(usable(r)=='missing_type' for r in records),
                 'missing_endpoint':sum(usable(r)=='missing_endpoint' for r in records),
                 'compiled_rules':len(bank),'matched_rules':matches,
                 'matched_records':sum(bool(r['allowed_rule_ids'] or r['forbidden_rule_ids']) for r in scans),
                 'flagged_records':sum(r['violation'] for r in scans),'conflicts':sum(r['conflict'] for r in scans)}
            coverage.append(row)
    write_gzip(HERE/'rule_matches.jsonl.gz',rule_matches)
    write_gzip(HERE/'record_matches.jsonl.gz',record_matches)
    traces=[];summaries=[]
    for name,records in data.items():
        for order in [('deletion','augmentation'),('augmentation','deletion')]:
            for timing in ('immediate','deferred'):
                env=ArchiveReplay(records,packets,counts)
                while not env.done:
                    action=choose(env.observe(),order,timing);env.step(action)
                result={'dataset':name,'order':list(order),'timing':timing,'steps':env.steps,
                        'removed_records':len(env.removed),'remaining_records':len(env.records),
                        'active_rules':len(env.active),'late_permission_events':sum(len(e['late_permissions']) for e in env.events),
                        'archived_responses_loaded':sum(e['archived_responses_loaded'] for e in env.events),
                        'actual_api_calls':0,'wall_seconds':sum(e['wall_seconds'] for e in env.events),
                        'factual_accuracy':None,'semantic_labels_available':False}
                if name=='RuleTest-94':
                    result['removed_designed_defects']=sum(labels[r]['defective'] for r in env.removed)
                    result['removed_designed_clean']=sum(not labels[r]['defective'] for r in env.removed)
                summaries.append(result);traces.append({'summary':result,'initial_observation':ArchiveReplay(records,packets,counts).observe(),'events':env.events})
    write_gzip(HERE/'schedule_traces.jsonl.gz',traces)
    with gzip.open(ROOT/'exps/paper2_offline_revision/candidate_execution_audit.jsonl.gz','rt') as f:
        statuses=Counter((r['strategy'],r['status']) for r in map(json.loads,f))
    result={'coverage':coverage,'schedules':summaries,'archive_response_counts':counts,
            'candidate_status_counts':{'|'.join(k):v for k,v in statuses.items()},
            'policy_training_performed':False,'actual_api_calls':0,
            'interpretation':'Exact typed execution coverage and mechanism replay; no new factual labels, learned scheduling results, or natural-error accuracy.'}
    dump(HERE/'results.json',result)
    inputs += [LINEAGE,ARCHIVE,ROOT/'exps/paper2_offline_revision/candidate_execution_audit.jsonl.gz']
    dump(HERE/'input_manifest.json',{'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        'policy_information':'Aggregate public observation and current mask; suite labels and original suite IDs are scorer-only.',
        'node_type_counts':type_counts,'unknown_types':'Abstain; never infer types or aliases from names.'})
    print(json.dumps({'coverage':coverage,'schedule_count':len(summaries),'api_calls':0},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
