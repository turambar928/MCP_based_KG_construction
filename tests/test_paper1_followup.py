import copy
import pytest
from content_enhancement.source_validation import validate_document_candidates
from exps.paper1_receipt_followup.protocol import make_prompt,evidence_index


def test_symmetric_whitespace_support_preserves_word_boundaries_and_constraints():
    def run(value,source='Alpha  Beta',relation='company',head='doc'):
        return validate_document_candidates([{'head':head,'relation':relation,'tail':value}],source=source,document_node='doc',allowed_relations=['company'])
    assert len(run('Alpha Beta')[0])==1
    assert len(run('Alpha  Beta','Alpha Beta')[0])==1
    assert run('AlphaBeta')[1][0]['reason']=='unsupported'
    assert run('Alpha Beta',relation='wrong')[1][0]['reason']=='invalid_relation'
    assert run('Alpha Beta',head='wrong')[1][0]['reason']=='wrong_head'
    assert run('')[1][0]['reason']=='unsupported'


def test_filter_cannot_add_missing_facts_or_keep_two_values_for_same_relation():
    a={'head':'doc','relation':'company','tail':'Alpha'};b={**a,'tail':'Beta'}
    result,rejected=validate_document_candidates([a,a,b],source='Alpha Beta',document_node='doc',allowed_relations=['company'])
    assert result==[a]
    assert [r['reason'] for r in rejected]==['duplicate','cardinality']


def test_evidence_prompt_never_reads_reference_fields_and_base_gets_same_schema():
    row={'case_id':'test','domain':'receipt','source_evidence':'ABC SDN BHD TOTAL 10.00',
         'required_document_node':'doc','allowed_relations':['company','total'],
         'source_lines':['ABC SDN BHD','TOTAL','10.00']}
    changed=copy.deepcopy(row);changed['references']={'company':'SECRET'}
    for arm in ['simple','evidence']:
        assert make_prompt(row,[],arm)==make_prompt(changed,[],arm)
    import json
    _,system_base,base=make_prompt(row,[],'simple');_,system_index,indexed=make_prompt(row,[],'evidence')
    assert system_base==system_index
    p=json.loads(indexed);assert p.pop('field_evidence_index')
    assert p==json.loads(base)


def test_evidence_index_uses_source_positions_instead_of_inventing_values():
    lines=['ABC SDN BHD','SUB TOTAL','7.00','TOTAL','10.00']
    index=evidence_index(lines)
    assert 2 not in index['total']['anchor_lines']
    assert index['total']['anchor_lines']==[4]
    assert index['company']['anchors']==[{'line':1,'text':lines[0]}]
    for data in index.values():
        assert all(1<=i<=len(lines) for i in data['anchor_lines']+data['nearby_lines'])


def test_amount_value_metric_separates_representation_from_different_values():
    from exps.paper1_receipt_followup.analyze import amount_value
    assert amount_value('$8.20')==amount_value('RM 8.2')
    assert amount_value('1,008.20')==amount_value('1008.2')
    assert amount_value('8.20')!=amount_value('82.00')
    assert amount_value('NaN') is None
    assert amount_value('item 8.20') is None
