"""Deterministic evidence checks precede the independent semantic review."""
from .receipts import digest
from .coverage import validate_coverage
from .claim_validation import nonempty, validate_claims


def validate(packet, bundle):
    if packet.get('unresolved'):
        raise ValueError('research unresolved: ' + str(packet['unresolved'])[:500])
    if packet["source"] != bundle["source"] or packet["bundle_sha"] != digest(bundle):
        raise ValueError("proposal uses stale or foreign evidence")
    identities = validate_claims(packet["claims"], bundle["captures"])
    for part in (packet["title"], packet["summary"]):
        nonempty(part["text"])
        if not part["claims"] or not set(part["claims"]) <= identities:
            raise ValueError("title and summary require supporting claims")
    validate_coverage(packet, bundle["captures"])
