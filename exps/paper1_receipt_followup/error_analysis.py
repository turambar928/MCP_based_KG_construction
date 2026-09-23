"""Reference-based descriptive analysis of the previously completed 60-case study."""
import csv,json,re,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_mechanism_audit.protocol import read_jsonl
from content_enhancement.source_validation import normalize_source_whitespace
HERE=Path(__file__).resolve().parent;OLD=ROOT/'exps/paper1_external_receipts'

def classify(source,prediction,reference,relation):
    compact=lambda s:re.sub(r'\s+','',s).casefold()
    alnum=lambda s:re.sub(r'[^\w]','',s).casefold()
    if prediction==reference:return 'exact'
    if compact(prediction)==compact(reference):return 'case_or_whitespace'
    if not prediction:return 'missing_field'
    if relation=='total':
        amount=lambda s:re.sub(r'^(?:RM|MYR|\$)\s*','',s.strip(),flags=re.I).replace(',','')
        if amount(prediction)==amount(reference):return 'amount_surface_format'
    if alnum(prediction)==alnum(reference):return 'punctuation_only'
    if normalize_source_whitespace(reference) not in normalize_source_whitespace(source):
        return 'reference_not_literal_after_whitespace_fix'
    if compact(prediction) in compact(reference) or compact(reference) in compact(prediction):
        return 'span_boundary'
    return 'different_source_value'

def main():
    inputs={r['case_id']:r for r in read_jsonl(OLD/'inputs.jsonl')}
    starts={r['case_id']:r for r in read_jsonl(OLD/'extraction.jsonl')}
    rows=[]
    for ref in read_jsonl(OLD/'references.jsonl'):
        cid=ref['case_id'];pred={t['relation']:t['tail'] for t in starts[cid]['triples']}
        for t in ref['triples']:
            value=pred.get(t['relation'],'')
            rows.append({'case_id':cid,'relation':t['relation'],'category':classify(inputs[cid]['source_evidence'],value,t['tail'],t['relation']),
                         'input_value':value,'reference_value':t['tail']})
    with (HERE/'prior_error_cases.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    unchanged={arm:sum(r['triples']==starts[r['case_id']]['triples'] for r in read_jsonl(OLD/'repairs.jsonl') if r['arm']==arm)
               for arm in ['base','diagnosis','shacl_context']}
    report={'n_fields':len(rows),'categories':dict(Counter(r['category'] for r in rows)),
            'by_field':{field:dict(Counter(r['category'] for r in rows if r['relation']==field)) for field in ['company','date','address','total']},
            'unchanged_graphs_of_60':unchanged,
            'interpretation':'Mechanical mismatch categories, not new human factual labels; a boundary/punctuation disagreement may still be semantically acceptable.'}
    (HERE/'prior_error_analysis.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
