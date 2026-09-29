"""Read-only checks of split isolation, frozen code, provenance and preservation."""
import hashlib
import json
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):return [json.loads(x) for x in path.read_text().splitlines()]


def verify():
    original=json.loads((HERE/'preservation.json').read_text())
    changed=[s for s,h in original.items() if not (ROOT/s).is_file() or sha(ROOT/s)!=h]
    assert not changed,changed
    p1=ROOT/'exps/paper1_cuad';p2=ROOT/'exps/paper2_docred'
    for s,h in json.loads((p1/'implementation_manifest.json').read_text()).items():assert sha(ROOT/s)==h,s
    for s,h in json.loads((p1/'scoring_manifest.json').read_text()).items():assert sha(p1/s)==h,s
    dev=rows(p1/'dev_public.jsonl');test=rows(p1/'test_public.jsonl')
    assert len(dev)==20 and len(test)==56
    assert not ({r['case_id'] for r in dev}&{r['case_id'] for r in test})
    assert not ({' '.join(r['source'].split()) for r in dev}&{' '.join(r['source'].split()) for r in test})
    collection={}
    for split,public in [('dev',dev),('test',test)]:
        path=p1/(split+'_responses.jsonl')
        if not path.exists():continue
        rs=rows(path);keys={(r['case_id'],r['arm']) for r in rs}
        assert len(keys)==len(rs)
        expected={(r['case_id'],a) for r in public for a in ['initial','repair_simple','repair_index','extract_index']}
        assert keys<=expected
        assert all(r['model']=='google/gemma-4-26B-A4B-it' for r in rs)
        assert all(r['calls']==len(r['attempts']) for r in rs)
        assert all(r['returned_model']=='google/gemma-4-26B-A4B-it' for r in rs if r['status']=='ok')
        assert all(t['head']==r['case_id'] for r in rs for t in r['triples'])
        collection[split]=dict(outcomes=len(rs),expected=len(expected),complete=keys==expected,actual_requests=sum(r['calls'] for r in rs))
    members=json.loads((p2/'membership.json').read_text());episodes=json.loads((p2/'episodes.json').read_text())
    observed=[]
    for split,pairs in episodes.items():
        for pair in pairs:
            assert len(pair)==2 and all(members[c]['split']==split for c in pair)
            observed.extend(pair)
    assert len(observed)==300 and len(set(observed))==300 and set(observed)==set(members)
    for split in ['train','dev','test']:
        public=json.loads((p2/'local'/f'{split}_public.json').read_text())
        for doc in public:
            assert set(doc)=={'case_id','title','sents','entities'}
            h=hashlib.sha256(json.dumps(doc,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            assert members[doc['case_id']]['public_sha256']==h
    pilot=json.loads((p2/'pilot_summary.json').read_text())
    assert pilot['documents']==10 and pilot['transport_ok']==30
    figure_changes=subprocess.check_output(['git','diff','--name-only','745c7f1','--','paper1/figure/method','paper2/figure/method'],cwd=ROOT,text=True).splitlines()
    assert not figure_changes,figure_changes
    report=dict(protected_files_unchanged=len(original),method_figures_unchanged=True,paper1=collection,
                paper2_source_disjoint_documents=300,paper2_pilot=pilot,credentials_file_excluded_from_staging=True)
    staged=subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).splitlines()
    assert 'apis' not in staged and 'api' not in staged
    (HERE/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':verify()
