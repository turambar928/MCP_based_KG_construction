"""Gold-free inputs and a fixed prompt protocol for the submission audit."""
from __future__ import annotations
import hashlib
import json
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BENCH = ROOT / 'exps/paper1_repair_benchmark'
EXT = ROOT / 'exps/paper1_submission_extensions'
MODEL = 'google/gemma-4-26B-A4B-it'
SYSTEM = ('Repair this document-level knowledge graph using only the supplied source evidence. '
          'Return the COMPLETE final graph as strict JSON: '
          '{"triples":[{"head":"...","relation":"...","tail":"..."}]}. '
          'Use the required document node and allowed relations, copy exact source spans, '
          'emit at most one triple per relation with a nonempty value supported by the source, '
          'retain correct fields and restore missing or corrupted fields. Do not invent facts. '
          'Any optional diagnostic or validation context is computed from the input only.')


def read_jsonl(path):
    if not Path(path).exists(): return []
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()


def key(t): return (t['head'],t['relation'],t['tail'])


@dataclass(frozen=True)
class PublicInput:
    case_id: str
    domain: str
    source_evidence: str
    required_document_node: str
    allowed_relations: tuple[str,...]
    triples: tuple[dict[str,str],...]

    def payload(self):
        return {'source_evidence':self.source_evidence,
                'required_document_node':self.required_document_node,
                'allowed_relations':list(self.allowed_relations),'input_triples':list(self.triples)}


def public_input(case, triples):
    # Required head is declared task metadata supplied identically to every arm.
    # It was formerly stored only inside clean_triples in the benchmark format.
    # No reference relation set, reference tail, or defect label enters this object.
    return PublicInput(case['case_id'],case['domain'],case['evidence_text'],
                       case['clean_triples'][0]['head'],tuple(case['allowed_relations']),
                       tuple(dict(t) for t in triples))


def preprocess(inp: PublicInput):
    result=[];seen=set()
    for raw in inp.triples:
        t=dict(raw)
        if t['head']!=inp.required_document_node and t['tail']==inp.required_document_node:
            t={'head':t['tail'],'relation':t['relation'],'tail':t['head']}
        if t['head']!=inp.required_document_node or t['relation'] not in inp.allowed_relations: continue
        if key(t) not in seen: result.append(t);seen.add(key(t))
    return result


def diagnosis(inp: PublicInput, triples):
    counts=Counter(key(t) for t in triples)
    return {'duplicate_rows':sum(n-1 for n in counts.values() if n>1),
            'invalid_relation_indices':[i for i,t in enumerate(triples) if t['relation'] not in inp.allowed_relations],
            'wrong_head_indices':[i for i,t in enumerate(triples) if t['head']!=inp.required_document_node],
            'unsupported_indices':[i for i,t in enumerate(triples) if t['tail'] not in inp.source_evidence],
            'present_relations':sorted({t['relation'] for t in triples if t['relation'] in inp.allowed_relations})}


def gate(inp: PublicInput, triples):
    accepted=[];rejected=[];seen=set();seen_r=set()
    for t in triples:
        reason=None
        if key(t) in seen: reason='duplicate'
        elif t['head']!=inp.required_document_node: reason='wrong_head'
        elif t['relation'] not in inp.allowed_relations: reason='invalid_relation'
        elif not t['tail'] or t['tail'] not in inp.source_evidence: reason='unsupported'
        elif t['relation'] in seen_r: reason='cardinality'
        if reason: rejected.append({'triple':t,'reason':reason})
        else: accepted.append(t);seen_r.add(t['relation'])
        seen.add(key(t))
    return accepted,rejected


def shacl_context(inp: PublicInput, triples):
    """Actual pySHACL validation; Lin et al. Sec.5 M+G context adaptation.

    RDF collapses duplicate occurrences; the unchanged JSON input preserves them.
    We use task-provided closed/maxCount/canonical-head constraints, plus an
    explicit source-support SPARQL constraint. Optional fields have no minCount.
    """
    from rdflib import Graph, Namespace, URIRef, Literal, BNode
    from rdflib.namespace import RDF, SH
    from rdflib.collection import Collection
    from pyshacl import validate
    ns=Namespace('urn:paper1:')
    data=Graph();shapes=Graph()
    data.bind('p',ns);shapes.bind('sh',SH);shapes.bind('p',ns)
    def node(s): return URIRef('urn:head:'+hashlib.sha256(s.encode()).hexdigest()[:24])
    def pred(s): return URIRef('urn:relation:'+hashlib.sha256(s.encode()).hexdigest()[:24])
    allowed={s:pred(s) for s in inp.allowed_relations}
    labels={str(node(inp.required_document_node)):inp.required_document_node}
    for t in triples:
        h=node(t['head']);p=pred(t['relation'])
        data.add((h,p,Literal(t['tail'])));labels[str(h)]=t['head'];labels[str(p)]=t['relation']
    labels.update({str(v):k for k,v in allowed.items()})
    shape=ns.DocumentShape
    shapes.add((shape,RDF.type,SH.NodeShape))
    shapes.add((shape,SH.targetNode,node(inp.required_document_node)))
    for h in set(data.subjects()): shapes.add((shape,SH.targetNode,h))
    headlist=BNode();Collection(shapes,headlist,[node(inp.required_document_node)])
    shapes.add((shape,SH['in'],headlist));shapes.add((shape,SH.closed,Literal(True)))
    for r,p in allowed.items():
        prop=URIRef(str(ns)+'property/'+hashlib.sha256(r.encode()).hexdigest()[:16])
        shapes.add((shape,SH.property,prop));shapes.add((prop,SH.path,p))
        shapes.add((prop,SH.maxCount,Literal(1)));shapes.add((prop,SH.minLength,Literal(1)))
    constraint=ns.SourceSupport
    shapes.add((shape,SH.sparql,constraint))
    shapes.add((constraint,SH.message,Literal('Value is absent from the supplied source text.')))
    query='SELECT $this ?path ?value WHERE { $this ?path ?value . FILTER (!CONTAINS('+Literal(inp.source_evidence).n3()+', STR(?value))) }'
    shapes.add((constraint,SH.select,Literal(query)))
    conforms,report,_=validate(data,shacl_graph=shapes,advanced=True,inference='none')
    records=[]
    for res in report.subjects(RDF.type,SH.ValidationResult):
        records.append({str(k).split('#')[-1]:str(report.value(res,k) or '') for k in
                        [SH.focusNode,SH.resultPath,SH.value,SH.sourceShape,SH.sourceConstraintComponent,SH.resultMessage]})
    records.sort(key=lambda x:json.dumps(x,sort_keys=True))
    return {'primer':'Repair the RDF graph using the violated SHACL constraints and graph context.',
            'violation_context':records,'shacl_manifest_context':shapes.serialize(format='turtle'),
            'knowledge_graph_context':data.serialize(format='turtle'),'identifier_labels':labels,
            'instructions':'Make contextually appropriate repairs with minimal change; return the complete JSON graph using the labels, not RDF identifiers.',
            'conforms':bool(conforms)}


def make_prompt(inp, arm):
    structural=preprocess(inp)
    payload={**inp.payload(),'input_triples':structural}
    if arm=='diagnosis': payload['diagnostic_context']=diagnosis(inp,structural)
    elif arm=='shacl_context': payload['shacl_context']=shacl_context(inp,structural)
    elif arm!='base': raise ValueError(arm)
    return SYSTEM,json.dumps(payload,ensure_ascii=False,sort_keys=True)
