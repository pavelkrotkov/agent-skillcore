"""Only independently useful supported knowledge enters the existing wiki shape."""
from .claim_validation import nonempty, validate_claims
from .receipts import digest
from .quick_claims import retained
from .deep_scope import resource_limits


def packet(value, evidence, checked):
    identities = validate_claims(value['claims'], evidence['captures'])
    for claim in value['claims']:
        retained(claim, checked)
    for part in (value['title'], value['summary']):
        nonempty(part['text'])
        if not part['claims'] or not set(part['claims']) <= identities:
            raise ValueError('title and summary must reference retained claims')
    if not isinstance(value['limitations'], list):
        raise ValueError('explicit bounded scope required')
    limitations = value['limitations'] + ['Bounded fact-check; linked resources were not exhaustively reviewed.']
    limitations.extend(resource_limits(evidence))
    limitations.extend(quick_limits(evidence))
    return dict(value, source=evidence['source'], bundle_sha=digest(evidence), limitations=limitations)


def quick_limits(evidence):
    return sorted({limit for capture in evidence['captures'].values() if capture.get('quick_scope')
                   for limit in capture.get('limitations', [])})
