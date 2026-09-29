"""Prepare source-grouped public inputs separately from scorer-only references."""
import json
import sys
import zipfile
from collections import Counter
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from exps.paper1_cuad.protocol import FIELDS, normalize, digest
HERE = Path(__file__).resolve().parent


def write_once(path, text):
    if path.exists():
        if path.read_text() != text: raise ValueError('Frozen output differs: '+str(path))
    else: path.write_text(text)


def prepare():
    archive = ROOT/'exps/submission_week_20260929/sources/cuad_data.zip'
    z = zipfile.ZipFile(archive)
    full = json.loads(z.read('CUADv1.json'))['data']
    tests = json.loads(z.read('test.json'))['data']
    test_names = {d['title'] for d in tests}
    test_hashes = {sha256(normalize(d['paragraphs'][0]['context']).encode()).hexdigest() for d in tests}
    eligible = {'dev': [], 'test': []}
    audit = []
    seen = set()
    for d in sorted(full, key=lambda d: (d['title'] not in test_names, d['title'])):
        source = d['paragraphs'][0]['context']
        h = sha256(normalize(source).encode()).hexdigest()
        split = 'test' if d['title'] in test_names else 'dev'
        reasons = []
        if len(d['paragraphs']) != 1: reasons.append('multiple_paragraphs')
        if len(source) > 40000: reasons.append('over_40000_characters')
        if h in seen or (split=='dev' and h in test_hashes): reasons.append('duplicate_source')
        seen.add(h)
        qas = {q['id'].split('__')[-1]: q for q in d['paragraphs'][0]['qas']}
        gold = []
        for field in FIELDS:
            if field not in qas:
                reasons.append('missing_question:'+field);continue
            answers = qas[field]['answers']
            values = {normalize(a['text']) for a in answers}
            if len(values) > 1: reasons.append('multiple_values:'+field)
            for a in answers:
                if source[a['answer_start']:a['answer_start']+len(a['text'])] != a['text']:
                    reasons.append('invalid_span:'+field)
            if len(values)==1: gold.append({'relation':field,'tail':next(iter(values))})
        if not gold: reasons.append('no_positive_fields')
        case_id = 'cuad-'+h[:16]
        audit.append(dict(title=d['title'],case_id=case_id,official_split=split,
                          source_sha256=h,characters=len(source),exclusion_reasons=reasons))
        if not reasons:
            eligible[split].append((dict(case_id=case_id,title=d['title'],source=source),gold))
    selection = {s:sorted(rows,key=lambda r:sha256(('20260929:'+r[0]['case_id']).encode()).hexdigest())[:n]
                 for s,rows,n in [('dev',eligible['dev'],20),('test',eligible['test'],60)]}
    assert len(selection['dev'])==20
    for split, rows in selection.items():
        write_once(HERE/(split+'_public.jsonl'), ''.join(json.dumps(r,ensure_ascii=False)+'\n' for r,g in rows))
        write_once(HERE/(split+'_scorer_only.jsonl'), ''.join(json.dumps(dict(case_id=r['case_id'],triples=[dict(head=r['case_id'],**t) for t in g]),ensure_ascii=False)+'\n' for r,g in rows))
    write_once(HERE/'eligibility.json',json.dumps(audit,indent=2,ensure_ascii=False)+'\n')
    report = dict(dataset='CUAD v1',source_url='https://github.com/The-Atticus-Project/cuad',
                  archive_sha256=sha256(archive.read_bytes()).hexdigest(),
                  license='CC BY 4.0, stated at https://www.atticusprojectai.org/cuad',
                  attribution='Hendrycks, Burns, Chen, Ball (2021), CUAD',
                  total=len(full),eligible={s:len(r) for s,r in eligible.items()},
                  selected={s:len(r) for s,r in selection.items()},
                  exclusions=dict(Counter(x for r in audit for x in r['exclusion_reasons'])),
                  public_reference_separation=True,
                  note='All five fields must be single-value compatible; repeated identical spans count as one value. All eligible official-test contracts up to 60, no relaxed eligibility. This is an exact source-span field task, not the official CUAD QA benchmark.')
    write_once(HERE/'data_manifest.json',json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':prepare()
