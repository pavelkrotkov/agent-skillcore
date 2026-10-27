"""Exact review verdicts and single-correction manifests fail closed."""
from .claim_validation import nonempty
from .receipts import digest


def validate_verdict(verdict, packet, bundle_sha):
    findings = verdict['findings']
    if not isinstance(findings, list):
        raise ValueError('segment findings must be a list')
    for finding in findings:
        nonempty(finding)
    expected = dict(verdict='reject' if findings else 'approve', proposal_sha=digest(packet), bundle_sha=bundle_sha, findings=findings)
    if verdict != expected:
        raise ValueError('segment verdict does not bind the exact proposal and evidence')


def correction(pair):
    if set(pair) == {'proposal', 'review'}:
        return False
    if set(pair) != {'proposal', 'review', 'rejected'} or set(pair['rejected']) != {'proposal', 'review'}:
        raise ValueError('only one correction per segment is permitted')
    return True
