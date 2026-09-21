"""Receipt SHACL adapter: source text is RDF data, never interpolated into SPARQL."""
import hashlib,json
from exps.paper1_mechanism_audit.protocol import PublicInput

def receipt_shacl_context(inp: PublicInput, triples):
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
    # Bind source as RDF data: words such as SERVICE in receipt text are not SPARQL code.
    data.add((ns.SourceEvidence, ns.text, Literal(inp.source_evidence)))
    query='SELECT $this ?path ?value WHERE { $this ?path ?value . <urn:paper1:SourceEvidence> <urn:paper1:text> ?source . FILTER (!CONTAINS(STR(?source), STR(?value))) }'
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
            'source_metadata':'SourceEvidence/text supplies validation text; exclude this metadata from the repaired graph.',
            'instructions':'Make contextually appropriate repairs with minimal change; return the complete JSON graph using the labels, not RDF identifiers.',
            'conforms':bool(conforms)}

