"""One fixed field-evidence index; all arms share schema definitions and source lines."""
import json,re
from exps.paper1_mechanism_audit.protocol import preprocess
from exps.paper1_external_receipts.shacl import receipt_shacl_context
from exps.paper1_external_receipts.run import input_object
from content_enhancement.source_validation import normalize_source_whitespace, validate_document_candidates

FIELD_DEFINITIONS={
 'company': 'Name of the receipt issuer. If both a trading brand and a registered company are printed, use the registered company name. Exclude registration/tax numbers, customer names, and extra brand headings.',
 'address': 'Full printed postal address of the issuer, including unit, street, city, postcode and state where printed. Preserve source punctuation and spelling. Exclude telephone/tax numbers and unrelated headings.',
 'date': 'Transaction date printed on the receipt, without the time.',
 'total': 'Final amount payable, including tax and any printed rounding. Return the numeric amount without the currency label. Exclude subtotal, tendered cash, change, unit prices and quantities.'}
SYSTEM=('Repair the supplied receipt-field graph using the source and field definitions. '
 'Check every field against its definition; the input graph is a proposal, not an authority. '
 'Return the COMPLETE final graph as strict JSON: {"triples":[{"head":"...","relation":"...","tail":"..."}]}. '
 'Use the required document node and allowed relations, at most one value per relation. '
 'Copy source wording, keep word boundaries and punctuation, and do not silently correct OCR spelling. '
 'Retain correct fields and revise an input value when the source and definition support a better value. '
 'Omit unsupported fields. Optional context contains automatically computed evidence or validation cues.')

PATTERNS={
 'company':re.compile(r'\b(?:SDN\.?\s*BHD\.?|BERHAD|S/B|ENTERPRISE|TRADING|PLT)\b',re.I),
 'address':re.compile(r'\b(?:JALAN|JLN|LOT|TAMAN|TMN|LORONG|LOR|PERSIARAN|KUALA|SELANGOR|JOHOR|PENANG|PERAK|MALAYSIA|NO\.?\s*\d)|\b\d{5}\b',re.I),
 'date':re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{1,2}\s+(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\s+\d{2,4}\b',re.I),
 'total':re.compile(r'\b(?:TOTAL|JUMLAH|PAYABLE|AMOUNT\s+DUE|NETT?\s+AMOUNT)\b',re.I)}


def evidence_index(lines):
    result={}
    for field,pattern in PATTERNS.items():
        hits=[i for i,line in enumerate(lines) if pattern.search(line)]
        if field=='total':hits=[i for i in hits if not re.search(r'\bSUB\s*TOTAL\b',lines[i],re.I)]
        # No target strings are supplied or inferred; retain source line identities.
        neighbours=sorted({j for i in hits for j in range(max(0,i-1),min(len(lines),i+3))})
        result[field]={'anchor_lines':[i+1 for i in hits], 'nearby_lines':[j+1 for j in neighbours],
                       'anchors':[{'line':i+1,'text':lines[i]} for i in hits]}
    return result


def make_prompt(row,triples,arm):
    public=input_object(row,triples)
    normalized=normalize_source_whitespace(public.source_evidence)
    from dataclasses import replace
    public=replace(public,source_evidence=normalized)
    structural=preprocess(public)
    payload={**public.payload(),'input_triples':structural,'field_definitions':FIELD_DEFINITIONS,
             'source_lines':[{'line':i+1,'text':normalize_source_whitespace(t)} for i,t in enumerate(row['source_lines'])]}
    if arm=='evidence':payload['field_evidence_index']=evidence_index(row['source_lines'])
    elif arm=='shacl':payload['shacl_context']=receipt_shacl_context(public,structural)
    elif arm!='simple':raise ValueError(arm)
    return public,SYSTEM,json.dumps(payload,ensure_ascii=False,sort_keys=True)


def filter_response(row,triples):
    return validate_document_candidates(triples,source=row['source_evidence'],
        document_node=row['required_document_node'],allowed_relations=row['allowed_relations'])
