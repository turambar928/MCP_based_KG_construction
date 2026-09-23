"""Freeze scoring before test inference and verify before scoring test labels."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
FILES=['exps/paper1_receipt_followup/analyze.py','exps/paper1_receipt_followup/error_analysis.py',
       'exps/paper1_external_receipts/analyze.py','exps/paper1_mechanism_audit/analyze.py',
       'exps/paper1_submission_extensions/analyze_experiments.py','exps/paper1_repair_benchmark/analyze_results.py',
       'exps/paper1_receipt_followup/scoring_lock.py']
def current():return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FILES}
def verify():
    record=json.loads((HERE/'scoring_lock.json').read_text())
    assert record['sha256']==current(),'Scoring changed after test lock'
    return record

def main():
    p=HERE/'scoring_lock.json'
    record={'sha256':current(),'primary':'macro exact multiset triple F1; evidence_gate minus simple_gate',
            'secondary':['exact graph match','case/whitespace-normalized triple F1','preservation and overrepair','field error transitions','numeric total accuracy after removing RM/MYR/$ prefix and thousands commas'],
            'reference_source':'test references downloaded only after all test predictions',
            'numeric_amount_metric':'same scalar amount, not a whole-graph semantic correctness score'}
    if p.exists():assert json.loads(p.read_text())==record
    else:
        assert not (HERE/'test/extraction.jsonl').exists(),'Freeze scoring before test calls'
        p.write_text(json.dumps(record,indent=2)+'\n')
    print('Scoring protocol frozen.')
if __name__=='__main__':main()
