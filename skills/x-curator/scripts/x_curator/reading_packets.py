"""Segment claims can cite only the original slice actually shown to both sessions."""
from .claim_validation import nonempty, validate_claims
from .coverage import validate_item
from .receipts import digest
from .reading_citations import captures


def validate(packet, evidence):
    if packet.get('unresolved'):
        raise ValueError('segment unresolved: ' + str(packet['unresolved'])[:300])
    if (packet['source'], packet['bundle_sha']) != (evidence['source'], digest(evidence)):
        raise ValueError('segment proposal uses foreign evidence')
    if packet['claims']:
        validate_claims(packet['claims'], captures(evidence))
    elif packet['claims'] == []:
        nonempty(packet['empty_reason'])
    else:
        raise ValueError('segment claims must be a list')
    coverage(packet, evidence['captures'])


def coverage(packet, captures):
    items = packet['coverage']
    if not isinstance(packet['limitations'], list):
        raise ValueError('segment limitations required')
    if len(items) != len(captures) or {c['capture'] for c in items} != set(captures):
        raise ValueError('every segment capture needs coverage')
    for item in items:
        validate_item(item, captures[item['capture']], packet['limitations'])
