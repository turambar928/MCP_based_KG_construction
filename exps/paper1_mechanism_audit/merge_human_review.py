#!/usr/bin/env python3
"""Join two completed blind sheets by ID while preserving independent labels."""
import csv,json
from pathlib import Path
HERE=Path(__file__).resolve().parent/'human_review'

def read(path):
    with path.open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
    if len({r['item_id'] for r in rows})!=len(rows):raise ValueError('Duplicate item IDs')
    return {r['item_id']:r for r in rows}

def main():
    a=read(HERE/'annotator_a.csv');b=read(HERE/'annotator_b.csv');base=read(HERE/'adjudication.csv')
    if a.keys()!=b.keys() or a.keys()!=base.keys():raise ValueError('Mismatched annotation IDs')
    rows=[]
    for uid in sorted(a):
        row=dict(base[uid])
        for who,source in [('annotator_a',a),('annotator_b',b)]:
            for field in ['is_error','repair_acceptable']:
                value=source[uid][field].strip()
                if value not in {'0','1','U'}:raise ValueError(f'Incomplete {who} {uid} {field}')
                row[who+'_'+field]=value
        row['notes']=json.dumps({'annotator_a':a[uid]['notes'],'annotator_b':b[uid]['notes'],'adjudication':row['notes']},ensure_ascii=False)
        rows.append(row)
    target=HERE/'merged_for_adjudication.csv'
    if target.exists():raise ValueError('Refusing to overwrite an existing merged/adjudicated file')
    with target.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(target)
if __name__=='__main__':main()
