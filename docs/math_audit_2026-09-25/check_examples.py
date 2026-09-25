"""Read-only mathematical counterexamples. No model requests or training."""
import hashlib,itertools,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import numpy as np
from content_enhancement.constraint_optimizer import MultiScaleConstraintOptimizer
from content_enhancement.source_validation import validate_document_candidates
from exps.paper1_mechanism_audit.protocol import PublicInput,diagnosis
from exps.paper2_cooptimization.run_experiment import KG,Paper2CoOptimizationEnv,VALID_DETECTORS,VALIDATION_PREDICTIONS,VALIDATION_GOLD
from exps.paper2_offline_revision.policy_study import graph

def main():
    result={'scope':'Constructed counterexamples and exhaustive registry enumeration; not new benchmark estimates. No API, training, or modification of original artifacts.'}
    t={'head':'receipt','relation':'total','tail':'100'}
    kept,_=validate_document_candidates([t],source='Subtotal 100; total 120',document_node='receipt',allowed_relations=['total'])
    assert kept==[t];result['literal_support_not_field_correctness']={'source':'Subtotal 100; total 120','accepted':kept}
    # Check the stated cardinality result on every order of a small candidate universe.
    candidates=[{'head':'receipt','relation':r,'tail':v} for r,v in [('company','ABC'),('total','100'),('total','120'),('date','2026')]]
    for order in itertools.permutations(candidates):
        selected,_=validate_document_candidates(order,source='ABC 100 120 2026',document_node='receipt',allowed_relations=['company','total','date'])
        assert len(selected)==3
    result['cardinality_property']={'orders_checked':24,'maximum_count':3,'semantic_accuracy_not_guaranteed':True}
    opt=MultiScaleConstraintOptimizer()
    empty=opt.assess([{'name':'receipt'}],[],'Issuer ABC total 120')
    partial=opt.assess([{'name':'receipt'}],[{'head':'receipt','relation':'company','tail':'ABC'}],'Issuer ABC total 120')
    assert partial.q_score==100 and not partial.violations
    result['partial_graph_max_quality']={'empty_scores':[empty.S_iso,empty.S_red,empty.S_log,empty.S_sem],
        'partial_scores':[partial.S_iso,partial.S_red,partial.S_log,partial.S_sem],'partial_q':partial.q_score,'detected_violations':partial.violations}
    assert opt._hierarchy_reversal('甲县','隶属于','乙省')
    result['hierarchy_direction_bug']={'triple':['甲县','隶属于','乙省'],'flagged_reversal':True,'meaning':'A county belonging to its province follows the normal direction.'}
    dangling=opt.assess([{'name':'a'}],[{'head':'a','relation':'r','tail':'unregistered'}],'unregistered')
    assert not any(v['type']=='dangling_endpoint' for v in dangling.violations)
    result['endpoint_universe']={'unregistered_tail_added_to_nodes':True,'dangling_violations':0}
    inp=PublicInput('toy','toy','abc','doc',('field',),({'head':'doc','relation':'field','tail':''},))
    report=diagnosis(inp,list(inp.triples));assert report['unsupported_indices']==[]
    result['empty_tail_diagnostic_mismatch']={'diagnostic_unsupported_indices':report['unsupported_indices'],'paper_predicate_S':0,'scope':'Diagnostic builder on an empty-tail input; the candidate parser usually removes empty tails.'}
    prior=.05*math.log(1/3+1e-6)
    result['utility_thresholds_no_hard_gain']={'prior_term':prior,'confidence_bonus':.014,'add_required_normalized_gain':.35*.06-prior-.014,'replacement_required_normalized_gain':.35*.36-prior-.014}
    clean=graph();nodes={n:{'id':n,'name':n,'node_type':'Document'} for n in 'abcd'};envs=[]
    for pairs in [[('a','b'),('b','c'),('d','missing')],[('a','b'),('c','d'),('a','missing')]]:
        e=Paper2CoOptimizationEnv(clean,123)
        e.graph=KG(dict(nodes),[{'start_id':h,'end_id':t,'relation_type':'MENTIONS'} for h,t in pairs])
        e.active_rules=set(VALID_DETECTORS);e.initial_defects=e.defect_counts();envs.append(e)
    assert np.array_equal(envs[0].state(),envs[1].state())
    assert np.array_equal(envs[0].available_action_mask(),envs[1].available_action_mask())
    transitions=[]
    for e in envs:
        _,reward,done,info=e.step(3)
        transitions.append({'before':info['before_defects'],'after':info['defects'],'reward':reward,'done':done,'reported_new_violations':info['new_violations']})
    assert transitions[0]['after']['isolated']==1 and transitions[1]['after']['isolated']==0
    result['observation_alias_and_inactive_safety_penalty']={'equal_observations':True,'equal_masks':True,'action':'dangling_edge_cleanup','transitions':transitions}
    best=(-1,None);entries=[]
    for mask in range(1<<len(VALIDATION_PREDICTIONS)):
        rules=[r for i,r in enumerate(VALIDATION_PREDICTIONS) if mask>>i&1]
        pred=set().union(*(VALIDATION_PREDICTIONS[r] for r in rules));tp=len(pred&VALIDATION_GOLD)
        p=tp/len(pred) if pred else 0;rec=tp/len(VALIDATION_GOLD);cov=sum(v in rules for v in VALID_DETECTORS)/4
        q=.35*p+.35*rec+.3*cov
        if q>best[0]:best=(q,rules)
        if rules==list(VALID_DETECTORS)[:len(rules)]:entries.append({'valid_modules':len(rules),'precision':p,'recall':rec,'coverage':cov,'q_rule':q})
    result['fixed_registry_ceiling']={'subsets_checked':128,'max_rule_quality':best[0],'maximizing_subset':best[1],
        'joint_upper_bound_at_perfect_graph':(1+.4*best[0])/1.4,'valid_prefix_scores':entries,
        'note':'Score ceiling for this fixed registry; does not prove reachability within the 18-step repair budget.'}
    paths=['paper1/sections/overview.tex','paper1/sections/implementation.tex','paper2/sections/methodology.tex',
      'content_enhancement/constraint_optimizer.py','content_enhancement/source_validation.py','exps/decision_network/build_from_repair_benchmark.py',
      'exps/decision_network/train_fphi.py','exps/paper1_mechanism_audit/protocol.py','exps/paper2_cooptimization/run_experiment.py']
    result['inspected_source_sha256']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    dest=Path(__file__).with_name('checked_examples.json');dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='inspected_source_sha256'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
