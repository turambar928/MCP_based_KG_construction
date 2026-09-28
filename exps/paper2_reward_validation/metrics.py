"""Scorer-only controlled-reference metrics. Never imported by training/policies."""
from collections import Counter

def facts(graph):
    return {(r['start_id'],r['relation_type'],r['end_id']) for r in graph.rels}

def fact_changes(reference,before,after):
    good=facts(reference);left=facts(before);right=facts(after)
    return {'added_correct_facts':len((right-left)&good),'added_wrong_facts':len((right-left)-good),
        'removed_correct_facts':len((left-right)&good),'removed_wrong_facts':len((left-right)-good),
        'duplicate_excess_change':(len(after.rels)-len(right))-(len(before.rels)-len(left))}

def score(reference,initial,final,restoration_targets):
    good=facts(reference);original=facts(initial);actual=facts(final);tp=len(actual&good)
    initial_correct=original&good
    final_by_id={r['_edge_id']:r for r in final.rels}
    restored=sum(identity in final_by_id and final_by_id[identity]['relation_type']==target for identity,target in restoration_targets.items())
    return {'fact_f1':2*tp/max(1,len(actual)+len(good)), 'fact_precision':tp/max(1,len(actual)),
        'fact_recall':tp/max(1,len(good)),'correct_fact_preservation':len(actual&initial_correct)/len(initial_correct) if initial_correct else 1.,
        'lost_initial_correct_facts':len(initial_correct-actual),'remaining_wrong_facts':len(actual-good),
        'missing_reference_facts':len(good-actual),'new_wrong_facts_final':len((actual-original)-good),
        'invalid_relation_repair_rate':restored/len(restoration_targets) if restoration_targets else 1.,
        'initial_invalid_relations':len(restoration_targets),'restored_invalid_relations':restored,
        'reference_fact_count':len(good),'final_fact_count':len(actual),'final_edge_occurrences':len(final.rels),
        'final_duplicate_excess':len(final.rels)-len(actual)}

def restoration_labels(env):
    """Trusted corruption records supply evaluation labels only."""
    return {r['_edge_id']:env._relation_gold[r['defect_id']] for r in env.graph.rels if r.get('defect_id') in env._relation_gold}

def graph_delta(before,after):
    b={r['_edge_id']:r for r in before.rels};a={r['_edge_id']:r for r in after.rels}
    return {'removed_edge_ids':sorted(b.keys()-a.keys()),'added_edges':[a[k] for k in sorted(a.keys()-b.keys())],
        'updated_edges':[a[k] for k in sorted(a.keys()&b.keys()) if a[k]!=b[k]],
        'removed_node_ids':sorted(before.nodes.keys()-after.nodes.keys()),
        'added_nodes':{k:after.nodes[k] for k in sorted(after.nodes.keys()-before.nodes.keys())}}
