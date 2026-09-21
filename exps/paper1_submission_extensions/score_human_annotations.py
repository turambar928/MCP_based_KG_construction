#!/usr/bin/env python3
"""Score independent, pre-adjudication human labels without overwriting U labels."""
from __future__ import annotations
import argparse,csv,json,math
from pathlib import Path
from sklearn.metrics import cohen_kappa_score
HERE=Path(__file__).resolve().parent


def labels(rows,column,allowed):
    values=[row[column].strip() for row in rows]
    invalid=sorted(set(values)-set(allowed))
    if invalid:raise ValueError(f'{column}: missing/invalid labels {invalid}; independent judgments must remain unchanged')
    return values


def agreement(a,b):
    if not a:raise ValueError('No annotations')
    kappa=float(cohen_kappa_score(a,b,labels=['0','1','U'])) if len(set(a+b))>1 else None
    return {'n':len(a),'raw_agreement':sum(x==y for x,y in zip(a,b))/len(a),
            'cohen_kappa':kappa if kappa is not None and math.isfinite(kappa) else None,
            'uncertain_a':a.count('U'),'uncertain_b':b.count('U'),
            'positive_rate_a':a.count('1')/len(a),'positive_rate_b':b.count('1')/len(b)}


def score(rows):
    if not rows:raise ValueError('Empty annotation sheet')
    results={}
    for task,column in [('error_detection','is_error'),('repair_acceptance','repair_acceptable')]:
        a=labels(rows,'annotator_a_'+column,{'0','1','U'})
        b=labels(rows,'annotator_b_'+column,{'0','1','U'})
        consensus=labels(rows,'adjudicated_'+column,{'0','1','U'})
        certain=[v for v in consensus if v!='U']
        results[task]={'independent_agreement':agreement(a,b),'adjudicated_n_certain':len(certain),
                       'adjudicated_n_uncertain':len(consensus)-len(certain),
                       'adjudicated_positive_rate':certain.count('1')/len(certain) if certain else None}
    return results


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=HERE/'natural_error_annotation_sample.csv')
    p.add_argument('--output',type=Path,default=HERE/'human_annotation_results.json');args=p.parse_args()
    with args.input.open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
    result=score(rows)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
