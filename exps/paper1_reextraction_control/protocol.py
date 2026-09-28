"""Four matched prompts. No credentials, network client or reference labels."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_mechanism_audit.protocol import PublicInput,preprocess
from exps.paper1_receipt_followup.protocol import FIELD_DEFINITIONS,evidence_index
from content_enhancement.source_validation import normalize_source_whitespace
MODEL='google/gemma-4-26B-A4B-it'
ARMS=('repair_simple','repair_index','extract_simple','extract_index')
COMMON=('Use only the supplied source and field definitions. '
        'Return the COMPLETE final graph as strict JSON: {"triples":[{"head":"...","relation":"...","tail":"..."}]}. '
        'Use the required document node and allowed relations, at most one value per relation. '
        'Copy source wording, keep word boundaries and punctuation, and do not silently correct OCR spelling. '
        'Omit unsupported fields. Optional context contains automatically computed evidence cues.')


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def make_prompt(row,old_graph,arm):
    assert arm in ARMS
    payload={'source_evidence':normalize_source_whitespace(row['source_evidence']),
             'required_document_node':row['required_document_node'],
             'allowed_relations':list(row['allowed_relations']),
             'field_definitions':dict(FIELD_DEFINITIONS),
             'source_lines':[{'line':i+1,'text':normalize_source_whitespace(t)} for i,t in enumerate(row['source_lines'])]}
    if arm.startswith('repair_'):
        inp=PublicInput(row['case_id'],row['domain'],payload['source_evidence'],row['required_document_node'],tuple(row['allowed_relations']),tuple(old_graph))
        payload['input_triples']=preprocess(inp)
        prefix='Repair the supplied receipt-field graph; retain correct values and revise unsupported or incorrect values. '
    else:
        prefix='Extract a receipt-field graph from the supplied source. '
    if arm.endswith('_index'):
        payload['field_evidence_index']=evidence_index(row['source_lines'])
    return prefix+COMMON,json.dumps(payload,ensure_ascii=False,sort_keys=True)


def task(row,old_graph,arm):
    system,user=make_prompt(row,old_graph,arm)
    request={'model':MODEL,'temperature':0,'max_tokens':4000,
             'messages':[{'role':'system','content':system},{'role':'user','content':user}]}
    return {'case_id':row['case_id'],'arm':arm,'request':request,'prompt_sha256':digest(request)}
