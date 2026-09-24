"""Verify frozen studies, trial completeness and exact reproduction of old baselines."""
import gzip,hashlib,json,sys
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_ablation_completion.run import verify
from exps.paper1_mechanism_audit.protocol import read_jsonl,key
from exps.paper1_receipt_followup.scoring_lock import verify as old_scoring_verify
from exps.paper1_ablation_completion.offline import VARIANTS
HERE=Path(__file__).resolve().parent

def main():
    verify();old_scoring_verify()
    old={(r['stream'],r['case_id'],r['variant']):r for r in read_jsonl(ROOT/'exps/paper1_mechanism_audit/optimizer_replay.jsonl')}
    arch=json.loads((HERE/'trace_archive.json').read_text());z=(HERE/arch['archive']).read_bytes();raw=gzip.decompress(z)
    assert hashlib.sha256(z).hexdigest()==arch['compressed_sha256']
    assert hashlib.sha256(raw).hexdigest()==arch['uncompressed_sha256']
    rows=[json.loads(line) for line in raw.splitlines()];assert len(rows)==5850
    ids={(r['cohort'],r['case_id'],r['variant']) for r in rows};assert len(ids)==5850
    for cohort in ['controlled','natural']:
        for variant in VARIANTS:assert sum(r['cohort']==cohort and r['variant']==variant for r in rows)==225
    matched=0
    for r in rows:
        decisions=r['audit']['decisions']
        assert sum(d['accepted'] for d in decisions)==r['applied_count']
        assert all('before_triples' in d and 'after_triples' in d for d in decisions)
        assert all(d['utility']>0 and d['reason']=='accepted' for d in decisions if d['accepted'])
        assert len({d['iteration'] for d in decisions if d['accepted']})==r['applied_count']
        if r['variant'] in ['uniform_always','learned_trigger']:
            oldname='uniform' if r['variant']=='uniform_always' else 'learned'
            previous=old[r['cohort'],r['case_id'],oldname]
            assert Counter(map(key,r['triples']))==Counter(map(key,previous['triples']))
            assert r['applied_count']==previous['applied_count'];matched+=1
    gate=json.loads((HERE/'archived_gate_results.json').read_text());assert gate['responses']==540 and gate['scored_configurations']==4320
    new=read_jsonl(HERE/'predictions.jsonl');assert all(r['model']=='google/gemma-4-26B-A4B-it' for r in new)
    print('PASS: frozen hashes; receipt scoring lock; 5850 unique traces; 900 exact old-baseline reproductions; 4320 gate scores; Gemma-only attempted calls.')
    print('New API study successful responses:',sum(r['status']=='ok' for r in new),'of 840 planned outcomes.')
if __name__=='__main__':main()
