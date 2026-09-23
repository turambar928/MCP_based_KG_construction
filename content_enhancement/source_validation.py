"""Document-field candidate validation with consistent whitespace handling."""
from collections.abc import Iterable


def normalize_source_whitespace(text: str) -> str:
    """Collapse whitespace while preserving word boundaries, case and punctuation."""
    return ' '.join(text.split())


def validate_document_candidates(candidates: Iterable[dict[str,str]], *, source: str,
                                 document_node: str, allowed_relations: Iterable[str]):
    evidence=normalize_source_whitespace(source)
    allowed=set(allowed_relations);seen=set();used_relations=set();accepted=[];rejected=[]
    for candidate in candidates:
        triple=dict(candidate)
        key=tuple(triple[k] for k in ['head','relation','tail'])
        value=normalize_source_whitespace(triple['tail'])
        reason=None
        if key in seen:reason='duplicate'
        elif triple['head']!=document_node:reason='wrong_head'
        elif triple['relation'] not in allowed:reason='invalid_relation'
        elif not value or value not in evidence:reason='unsupported'
        elif triple['relation'] in used_relations:reason='cardinality'
        if reason:rejected.append({'triple':triple,'reason':reason})
        else:accepted.append(triple);used_relations.add(triple['relation'])
        seen.add(key)
    return accepted,rejected
