"""Meaningful integrity checks; all labels below are synthetic test fixtures."""
import csv
import json
from pathlib import Path

import pytest
from exps.paper1_human_review import process_returns as review
from exps.paper1_external_receipts.analyze import score_case
from exps.paper1_external_receipts.shacl import receipt_shacl_context
from exps.paper1_mechanism_audit.protocol import PublicInput


def fake_items():
    public=[{'task':task,'item_id':f'test-{task}','source':'Alpha', 'schema':['name'],
             'input_graph':[],'output_graph':None,'operation':'add',
             'triple':{'head':'doc','relation':'name','tail':'Alpha'}} for task in ['D','E']]
    private=[{'task':x['task'],'item_id':x['item_id'],'configuration':'synthetic_test','case_id':'test-doc'} for x in public]
    return public,private


def make_return(path,who,uncertain=False):
    labels=[{'task':t,'item_id':f'test-{t}','is_error':'U' if uncertain else '1',
             'repair_acceptable':'1','notes':'Synthetic test fixture.'} for t in ['D','E']]
    path.write_text(json.dumps({'version':'2026-09-21-v1','annotator':who,'labels':labels}))


def test_rejects_wrong_identity_and_missing_labels(tmp_path):
    path=tmp_path/'a.json';make_return(path,'A')
    public={review.identity(x):x for x in fake_items()[0]}
    with pytest.raises(ValueError,match='identity'):review.read_return(path,'B',public)
    data=json.loads(path.read_text());data['labels'][0]['is_error']='';path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='Incomplete'):review.read_return(path,'A',public)


def test_adjudication_preserves_independent_uncertainty_and_rejects_tampering(tmp_path,monkeypatch):
    monkeypatch.setattr(review,'items',fake_items)
    a,b=tmp_path/'a.json',tmp_path/'b.json';make_return(a,'A',True);make_return(b,'B')
    out=tmp_path/'merged';review.merge(a,b,out)
    for task in ['D','E']:
        p=out/f'{task}_adjudication.csv'
        with p.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
        rows[0]['adjudicated_is_error']='1';review.write_csv(p,rows)
    review.score_folder(out)
    result=json.loads((out/'human_results.json').read_text())
    assert result['D']['error_detection']['independent_agreement']['raw_agreement']==0
    assert result['D']['error_detection']['independent_agreement']['uncertain_a']==1
    p=out/'D_adjudication.csv'
    with p.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    rows[0]['annotator_a_is_error']='1';review.write_csv(p,rows)
    with pytest.raises(ValueError,match='changed after merge'):review.score_folder(out)


def test_missing_receipt_label_is_not_scored_as_a_negative_fact():
    gold={'head':'doc','relation':'company','tail':'Alpha Ltd'}
    ref={'annotated_relations':['company','date','total'],'triples':[gold]}
    output=[gold,{'head':'doc','relation':'address','tail':'Some street'}]
    assert score_case([],output,ref)['triple_f1']==1
    wrong=output+[{'head':'doc','relation':'unknown','tail':'bad'}]
    assert score_case([],wrong,ref)['triple_f1']<1
    variant=[{**gold,'tail':'ALPHA LTD'}]
    metrics=score_case([],variant,ref)
    assert metrics['triple_f1']==0 and metrics['normalized_f1']==1


def test_receipt_keywords_are_data_not_sparql_code():
    inp=PublicInput('test','receipt','SERVICE TAX TOTAL: 10.00','doc',('total',),())
    triple={'head':'doc','relation':'total','tail':'10.00'}
    assert receipt_shacl_context(inp,[triple])['conforms'] is True
    report=receipt_shacl_context(inp,[{**triple,'tail':'99.00'}])
    assert report['conforms'] is False
    assert any('SourceSupport' in str(x) or 'SPARQLConstraint' in str(x) for x in report['violation_context'])


def test_source_whitespace_check_matches_parser_without_merging_words():
    from exps.paper1_external_receipts.whitespace_check import whitespace_gate
    inp=PublicInput('test','receipt','Alpha  Beta','doc',('company',),())
    supported={'head':'doc','relation':'company','tail':'Alpha Beta'}
    accepted,rejected=whitespace_gate(inp,[supported])
    assert accepted==[supported] and not rejected
    accepted,rejected=whitespace_gate(inp,[{**supported,'tail':'AlphaBeta'}])
    assert not accepted and rejected[0]['reason']=='unsupported'
