"""Validate real annotations, preserve independent labels, then score adjudication."""
import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_human_review.build_package import items, COLUMNS
from exps.paper1_submission_extensions.score_human_annotations import agreement, score

LABELS={'0','1','U'}

def fingerprint(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def identity(row):return (row['task'],row['item_id'])

def read_return(path,who,public):
    if path.suffix.lower()=='.json':
        payload=json.loads(path.read_text())
        if payload.get('annotator')!=who or payload.get('version')!='2026-09-21-v1':
            raise ValueError('Wrong annotator identity or package version')
        rows=payload['labels']
    elif path.suffix.lower()=='.xlsx':
        from openpyxl import load_workbook
        wb=load_workbook(path,data_only=False);rows=[]
        for name in ['输入差异','实际修改']:
            vals=list(wb[name].values)
            if list(vals[0])!=COLUMNS:raise ValueError('Workbook columns changed')
            for values in vals[1:]:
                row=dict(zip(COLUMNS,values))
                uid=identity(row)
                if uid not in public:raise ValueError('Unknown item')
                original=public[uid]
                for key in COLUMNS[:8]:
                    actual=row[key]
                    if isinstance(original.get(key),(dict,list)):
                        try:actual=json.loads(actual)
                        except Exception as e:raise ValueError('Workbook context changed') from e
                    if actual!=original.get(key):raise ValueError(f'Workbook context changed: {uid} {key}')
                rows.append(row)
    else:raise ValueError('Expected JSON or XLSX')
    result={}
    for row in rows:
        uid=identity(row)
        if uid in result or uid not in public:raise ValueError('Duplicate or unknown item ID')
        record={k:str(row.get(k) if row.get(k) is not None else '').strip()
                for k in ['is_error','repair_acceptable','notes']}
        if any(record[k] not in LABELS for k in ['is_error','repair_acceptable']):
            raise ValueError(f'Incomplete/invalid labels: {who} {uid}')
        if ('0' in (record['is_error'],record['repair_acceptable']) or 'U' in (record['is_error'],record['repair_acceptable'])) and not record['notes']:
            raise ValueError(f'Please explain 0/U: {who} {uid}')
        result[uid]=record
    if result.keys()!=public.keys():raise ValueError('The return must contain all 400 items')
    return result

def frozen_fields(row):
    return {k:v for k,v in row.items() if k not in ['adjudicated_is_error','adjudicated_repair_acceptable','adjudication_notes']}

def write_csv(path,rows):
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)

def merge(a_path,b_path,out):
    records,_=items();public={identity(x):x for x in records}
    a=read_return(a_path,'A',public);b=read_return(b_path,'B',public)
    if out.exists():raise ValueError('Output exists; preserve existing labels/adjudication')
    out.mkdir(parents=True)
    hashes={};pre={}
    for task in ['D','E']:
        rows=[]
        for uid,context in public.items():
            if uid[0]!=task:continue
            row={k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else '' if v is None else str(v) for k,v in context.items()}
            for prefix,source in [('annotator_a',a),('annotator_b',b)]:
                row.update({prefix+'_'+k:v for k,v in source[uid].items()})
            row['disagreement']=str(any(a[uid][k]!=b[uid][k] for k in ['is_error','repair_acceptable']))
            for k in ['is_error','repair_acceptable']:
                row['adjudicated_'+k]=a[uid][k] if a[uid][k]==b[uid][k] else ''
            row['adjudication_notes']=''
            hashes[':'.join(uid)]=fingerprint(frozen_fields(row));rows.append(row)
        write_csv(out/f'{task}_adjudication.csv',rows)
        pre[task]={k:agreement([r['annotator_a_'+k] for r in rows],[r['annotator_b_'+k] for r in rows]) for k in ['is_error','repair_acceptable']}
    (out/'independent_agreement.json').write_text(json.dumps(pre,indent=2,allow_nan=False)+'\n')
    (out/'return_manifest.json').write_text(json.dumps({'a_sha256':hashlib.sha256(a_path.read_bytes()).hexdigest(),
        'b_sha256':hashlib.sha256(b_path.read_bytes()).hexdigest(),'immutable_row_hashes':hashes},indent=2)+'\n')
    print('Merged independent returns. Resolve remaining adjudication cells in',out)

def score_folder(folder):
    manifest=json.loads((folder/'return_manifest.json').read_text());seen=set();results={};allrows=[]
    _,mapping=items();private={identity(x):x for x in mapping}
    for task in ['D','E']:
        with (folder/f'{task}_adjudication.csv').open(newline='',encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
        for row in rows:
            uid=identity(row);key=':'.join(uid)
            if key in seen or uid[0]!=task or key not in manifest['immutable_row_hashes']:raise ValueError('Changed/duplicate item identity')
            if fingerprint(frozen_fields(row))!=manifest['immutable_row_hashes'][key]:raise ValueError('Independent labels or context changed after merge')
            seen.add(key)
        results[task]=score(rows);allrows.extend(rows)
    if seen!=set(manifest['immutable_row_hashes']):raise ValueError('Missing items')
    groups=defaultdict(list)
    for row in allrows:
        groups[(row['task'],private[identity(row)]['configuration'])].append(row)
    per=[]
    for (task,method),rows in sorted(groups.items()):
        m=score(rows)
        per.append({'task':task,'configuration':method,'n':len(rows),
            'acceptable':sum(r['adjudicated_repair_acceptable']=='1' for r in rows),
            'uncertain':m['repair_acceptance']['adjudicated_n_uncertain'],
            'acceptance_among_determinate':m['repair_acceptance']['adjudicated_positive_rate']})
    (folder/'human_results.json').write_text(json.dumps(results,indent=2,allow_nan=False)+'\n')
    write_csv(folder/'per_configuration.csv',per)
    lines=['# 真人标注结果','','原始标签包含 U；一致率在裁决前计算。D、E 分别统计。','', '|任务|判断|n|原始一致率|Kappa|裁决后确定数|仍为 U|裁决后正例比例|','|---|---|---:|---:|---:|---:|---:|---:|']
    for task,values in results.items():
        for name,value in values.items():
            a=value['independent_agreement']
            lines.append(f"|{task}|{name}|{a['n']}|{a['raw_agreement']:.4f}|{a['cohen_kappa']}|{value['adjudicated_n_certain']}|{value['adjudicated_n_uncertain']}|{value['adjudicated_positive_rate']}|")
    lines+=['','本结果衡量抽样差异/操作的人工判断，不能替代全图人工 F1 或总体缺陷召回率。']
    (folder/'human_results.md').write_text('\n'.join(lines)+'\n');print(folder/'human_results.md')

def main():
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
    m=s.add_parser('merge');m.add_argument('--a',type=Path,required=True);m.add_argument('--b',type=Path,required=True);m.add_argument('--out',type=Path,required=True)
    q=s.add_parser('score');q.add_argument('--folder',type=Path,required=True)
    args=p.parse_args()
    if args.command=='merge':merge(args.a,args.b,args.out)
    else:score_folder(args.folder)

if __name__=='__main__':main()
