import copy
import pytest
from exps.paper1_mechanism_audit.protocol import public_input,make_prompt,gate,preprocess,shacl_context
from exps.paper1_mechanism_audit.replay_optimizer import recommendations
from exps.paper1_submission_extensions.score_human_annotations import agreement,score


def fixture_case():
    return {'case_id':'x','domain':'test','evidence_text':'Alice works at A.','allowed_relations':['works_at'],
            'clean_triples':[{'head':'doc','relation':'works_at','tail':'A'}],'defects':[{'gold':'SECRET'}]}


def test_prompts_do_not_depend_on_reference_tails_or_relation_presence():
    c=fixture_case();t=[{'head':'doc','relation':'works_at','tail':'B'}]
    changed=copy.deepcopy(c);changed['clean_triples']=[{'head':'doc','relation':'SECRET_REL','tail':'SECRET_TAIL'}]
    changed['defects']=[]
    for arm in ['base','diagnosis']:
        assert make_prompt(public_input(c,t),arm)==make_prompt(public_input(changed,t),arm)
    # SHACL serialization contains blank-node IDs, so compare semantic reports.
    a=shacl_context(public_input(c,t),t);b=shacl_context(public_input(changed,t),t)
    assert a['conforms']==b['conforms']==False
    assert a['violation_context']==b['violation_context']


def test_gate_has_same_response_and_conservative_first_valid_relation():
    c=fixture_case();p=public_input(c,[])
    good={'head':'doc','relation':'works_at','tail':'A'}
    bad={'head':'doc','relation':'works_at','tail':'invented'}
    out,rejected=gate(p,[bad,good,good])
    assert out==[good]
    assert [r['reason'] for r in rejected]==['unsupported','duplicate']


def test_replacement_is_one_atomic_bundle_and_unchanged_relations_not_edited():
    old={'head':'doc','relation':'works_at','tail':'B'}
    new={**old,'tail':'A'}
    rec=recommendations([old],[new])
    assert len(rec)==1
    assert [a['action'] for a in rec[0]['implementation']['actions']]==['delete','add']
    assert recommendations([new],[new])==[]


def test_uncertain_human_labels_remain_independent():
    rows=[]
    for a,b,z in [('U','1','1'),('0','0','0'),('1','0','U')]:
        rows.append({prefix+'_'+task:value for task in ['is_error','repair_acceptable']
                     for prefix,value in [('annotator_a',a),('annotator_b',b),('adjudicated',z)]})
    result=score(rows)['error_detection']
    assert result['independent_agreement']['raw_agreement']==pytest.approx(1/3)
    assert result['independent_agreement']['uncertain_a']==1
    assert result['adjudicated_n_uncertain']==1
    assert rows[0]['annotator_a_is_error']=='U'
    assert agreement(['1','1'],['1','1'])['cohen_kappa'] is None


def test_blank_labels_cannot_be_reported_as_completed_human_review():
    with pytest.raises(ValueError):score([{'annotator_a_is_error':''}])


def test_source_field_baseline_uses_only_declared_serialized_input():
    from exps.paper1_mechanism_audit.source_field_baseline import source_field_copy
    c=fixture_case()
    c['allowed_relations']=['works_at','role']
    c['evidence_text']='works_at：A。branch。role：Researcher。'
    p=public_input(c,[])
    assert source_field_copy(p)==[
        {'head':'doc','relation':'works_at','tail':'A。branch'},
        {'head':'doc','relation':'role','tail':'Researcher。'}]
    # It is deliberately not claimed as a general unstructured-text extractor.
    c['evidence_text']='Alice works at A.'
    assert source_field_copy(public_input(c,[]))==[]
