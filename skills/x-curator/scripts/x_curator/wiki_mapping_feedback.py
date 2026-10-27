"""Only authentic, unchanged-input rejections inform the next ordinary mapping."""
from .claim_validation import nonempty
from .receipts import digest
from .wiki_contract import validate
from .wiki_mapping_receipts import reviewed


def previous_rejection(db, inputs):
    identity = digest(inputs)
    row = db.execute('''SELECT * FROM wiki_runs WHERE state='failed' AND proposal IS NOT NULL
        AND review IS NOT NULL AND (input_sha=? OR
        CASE WHEN json_valid(input) THEN json_extract(input,'$.feedback.input_sha') END=?)
        ORDER BY started DESC,id DESC LIMIT 1''', (identity, identity)).fetchone()
    if row is None:
        return None
    try:
        return verified_feedback(row, inputs)
    except (ValueError, KeyError, TypeError):
        return None


def verified_feedback(row, inputs):
    original, packet, verdict = reviewed(row)
    base = dict(original)
    base.pop('feedback', None)
    if digest(base) != digest(inputs):
        raise ValueError('mapping feedback uses changed inputs')
    if not isinstance(verdict, dict):
        raise ValueError('review must be an object')
    findings = verdict.get('findings')
    if not isinstance(findings, list) or not findings:
        raise ValueError('rejection requires concrete findings')
    for finding in findings:
        nonempty(finding)
    if verdict != dict(verdict='reject', input_sha=digest(original), proposal_sha=digest(packet), findings=findings):
        raise ValueError('rejection does not bind the exact mapping and inputs')
    validate(packet, original)
    return dict(input_sha=digest(inputs), review=row['id'], proposal=packet, findings=findings)
