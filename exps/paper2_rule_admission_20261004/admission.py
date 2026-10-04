"""Offline, context-bound admission of previously compiled rule proposals.

This verifies provenance and independently supplied attestations, NOT semantic
entailment. Model outputs cannot create trust roots. No reference labels, API,
filesystem reads or rule-family exceptions occur in the admission function.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

VERSION = 'context-bound-rule-admission-v1'
RECORD_FIELDS = {'record_id', 'source_document_id', 'head_entity_id', 'tail_entity_id',
                 'subject_type', 'relation', 'object_type', 'missing_endpoint'}
PACKET_FIELDS = {'packet_id', 'source_document_id', 'strategy', 'parse_success',
                 'rules', 'provenance', 'rejections'}
TYPES = {'PER', 'ORG', 'LOC', 'TIME', 'NUM', 'MISC'}
BINDING_FIELDS = {'version', 'packet_id', 'response_sha256', 'source_document_id',
                  'document_sha256', 'records_sha256', 'vocabulary_sha256', 'rule_sha256', 'episode_documents_sha256'}


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def binding(packet, rule, document, records, relations, documents):
    """Bind the decision to the exact public context, never a record-ID allowlist."""
    return dict(version=VERSION, packet_id=packet['packet_id'],
        response_sha256=packet.get('provenance', {}).get('response_sha256', ''),
        source_document_id=document['case_id'], document_sha256=digest(document),
        records_sha256=digest(sorted(records, key=lambda x: x['record_id'])),
        vocabulary_sha256=digest(relations), rule_sha256=digest(rule),
        episode_documents_sha256=digest(documents))


def provenance_error(packet, rule, document, records, relations):
    """Mechanical grounding only. Exact quotes are not contradiction proofs."""
    if packet['source_document_id'] != document['case_id']:
        return 'source_document_mismatch'
    if not packet['parse_success']:
        return 'failed_response'
    if rule.get('family') == 'type':
        if set(rule) != {'family', 'kind', 'pattern'} or rule['kind'] not in ('allowed', 'forbidden'):
            return 'invalid_type_rule'
        p = rule['pattern']
        if not isinstance(p, list) or len(p) != 3 or not all(isinstance(x, str) for x in p):
            return 'invalid_type_pattern'
        if p[0] not in TYPES or p[2] not in TYPES or p[1] not in relations:
            return 'unknown_vocabulary'
        return None
    if rule.get('family') != 'source' or set(rule) != {'family', 'verdict', 'record_id', 'evidence'}:
        return 'invalid_source_rule'
    if rule['verdict'] not in ('supported', 'contradicted'):
        return 'unsupported_source_verdict'
    targets = {r['record_id']: r for r in records}
    target = targets.get(rule['record_id'])
    if target is None or target['source_document_id'] != document['case_id']:
        return 'target_outside_document'
    entities = {e['entity_id']: e for e in document['entities']}
    if (target['head_entity_id'] not in entities or target['tail_entity_id'] not in entities
            or target['relation'] not in relations or target.get('missing_endpoint', False)):
        return 'unresolved_target'
    if not isinstance(rule['evidence'], list) or not rule['evidence']:
        return 'missing_evidence'
    for evidence in rule['evidence']:
        if not isinstance(evidence, dict) or set(evidence) != {'sentence_id', 'start', 'end', 'quote_sha256'}:
            return 'invalid_evidence'
        sid, start, end = (evidence[k] for k in ('sentence_id', 'start', 'end'))
        if (any(type(x) is not int for x in (sid, start, end)) or
                not 0 <= sid < len(document['sents'])):
            return 'invalid_evidence_offsets'
        sentence = ' '.join(document['sents'][sid])
        if not 0 <= start < end <= len(sentence):
            return 'invalid_evidence_offsets'
        if sha256(sentence[start:end].encode()).hexdigest() != evidence['quote_sha256']:
            return 'quote_hash_mismatch'
    return None


class Registry:
    """Pinned, externally supplied decisions. Empty by default, never auto-filled.

    The operator selecting trust roots is responsible for their independence and
    semantic quality. Hash verification establishes integrity, not reviewer truth.
    """
    def __init__(self):
        self._decisions = {}
        self.sources = []

    @classmethod
    def load(cls, manifest_path):
        manifest_path = Path(manifest_path)
        obj = json.loads(manifest_path.read_text())
        if set(obj) != {'version', 'trusted_sources'} or obj['version'] != VERSION:
            raise ValueError('Invalid registry manifest')
        if not isinstance(obj['trusted_sources'], list):
            raise ValueError('trusted_sources must be a list')
        registry = cls()
        seen = set()
        for root in obj['trusted_sources']:
            if set(root) != {'source_id', 'kind', 'path', 'sha256'} or root['kind'] not in ('independent_review', 'trusted_schema_review'):
                raise ValueError('Invalid trusted source')
            if not isinstance(root['source_id'], str) or not root['source_id'] or root['source_id'] in seen:
                raise ValueError('Duplicate or empty authority ID')
            seen.add(root['source_id'])
            relative = Path(root['path'])
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('Trusted evidence must stay within manifest directory')
            path = (manifest_path.parent / relative).resolve()
            if not path.is_relative_to(manifest_path.parent.resolve()):
                raise ValueError('Trusted evidence escapes registry directory')
            data = path.read_bytes()
            if sha256(data).hexdigest() != root['sha256']:
                raise ValueError('Trusted evidence hash mismatch')
            artifact = json.loads(data)
            if (set(artifact) != {'version', 'source_id', 'kind', 'authority', 'decisions'} or
                    artifact['version'] != VERSION or artifact['source_id'] != root['source_id'] or
                    artifact['kind'] != root['kind'] or not isinstance(artifact['authority'], str)
                    or not artifact['authority'].strip() or not isinstance(artifact['decisions'], list)):
                raise ValueError('Invalid independent validation artifact')
            for row in artifact['decisions']:
                if (set(row) != {'binding', 'verdict', 'basis', 'rationale'} or
                        not isinstance(row['binding'], dict) or set(row['binding']) != BINDING_FIELDS or
                        row['binding']['version'] != VERSION or
                        any(not isinstance(v, str) for v in row['binding'].values()) or
                        row['verdict'] not in ('approve', 'reject', 'uncertain') or
                        not all(isinstance(row[k], str) and row[k].strip() for k in ('basis', 'rationale'))):
                    raise ValueError('Invalid validation decision')
                registry._decisions.setdefault(digest(row['binding']), []).append(
                    dict(verdict=row['verdict'], source_id=root['source_id'], kind=root['kind']))
            registry.sources.append({k: root[k] for k in ('source_id', 'kind', 'sha256')})
        return registry

    def decide(self, bound, family):
        decisions = self._decisions.get(digest(bound), [])
        # A reviewed type schema cannot certify source-level entailment.
        decisions = [r for r in decisions if family == 'type' or r['kind'] == 'independent_review']
        if not decisions:
            return False, 'no_independent_validation', []
        if any(d['verdict'] != 'approve' for d in decisions):
            return False, 'validation_rejected_or_unresolved', decisions
        return True, 'independently_approved', decisions


def admit_packets(packets, documents, records, relations, registry, mode='validated'):
    """Project rules into the old executor contract; keep the old executor frozen.

    All families require validation, including allowed/supported: unvalidated
    claims must not earn coverage reward or silently veto approved constraints.
    `grounded` is a diagnostic comparator, not a certified execution mode.
    """
    if mode not in ('validated', 'grounded'):
        raise ValueError('Unknown admission mode')
    if set(packets) != {'deletion', 'augmentation'}:
        raise ValueError('Expected two strategy queues')
    if any(set(r) - RECORD_FIELDS for r in records):
        raise ValueError('Unexpected record fields; scorer data are not public inputs')
    ids = [r['record_id'] for r in records]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate public record ID')
    result = deepcopy(packets)
    audit = []
    for arm, queue in result.items():
        for packet in queue:
            if (set(packet) != PACKET_FIELDS or packet['strategy'] != arm or
                    type(packet['parse_success']) is not bool or
                    not isinstance(packet['rules'], list)):
                raise ValueError('Invalid packet or untrusted extra metadata')
            doc = documents[packet['source_document_id']]
            local_records = [r for r in records if r['source_document_id'] == doc['case_id']]
            kept = []
            for ordinal, rule in enumerate(packet['rules']):
                bound = binding(packet, rule, doc, records, relations, documents)
                error = provenance_error(packet, rule, doc, local_records, relations)
                valid, reason, witnesses = registry.decide(bound, rule.get('family')) if error is None else (False, error, [])
                admitted = error is None and (mode == 'grounded' or valid)
                if admitted:
                    kept.append(rule)
                audit.append(dict(packet_id=packet['packet_id'], ordinal=ordinal, family=rule.get('family'),
                    kind=rule.get('kind', rule.get('verdict')), binding=bound,
                    proposed=True, grounded=error is None, validated=valid,
                    admitted=admitted, state='validated' if valid else 'grounded' if error is None else 'proposed',
                    reason='grounding_only_diagnostic' if mode == 'grounded' and admitted else reason,
                    validation_sources=witnesses))
            packet['rules'] = kept
    return result, audit
