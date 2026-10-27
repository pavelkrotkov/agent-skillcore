"""Publication revalidates the entire original-slice to final-packet proof chain."""
from . import reading_aggregate, reading_plan, reading_receipts
from .packets import validate
from .receipts import digest


def chain(db, token, evidence, manifest):
    reading = reading_plan.plan(evidence, manifest['plan']['version'])
    pairs = manifest['receipts']
    if manifest['plan'] != reading or len(pairs) != len(reading['parts']):
        raise ValueError('incomplete or foreign reading plan')
    packets = [reading_receipts.approved(db, token, evidence, reading, index, pair)
               for index, pair in enumerate(pairs)]
    return reading, pairs, reading_aggregate.template(evidence, packets)


def approved(db, token, proposal_id, review_id, evidence):
    author, request, header = reading_receipts.verify(db, token, proposal_id, 'research', 'research')
    reviewer, review_request, verdict = reading_receipts.verify(db, token, review_id, 'review', 'review')
    reading, pairs, template = chain(db, token, evidence, request['reading'])
    packet = reading_aggregate.compose(template, header)
    expected = reading_aggregate.request(evidence, reading, pairs, template, 'research')
    if request != expected or review_request != reading_aggregate.request(evidence, reading, pairs, template, 'review', packet):
        raise ValueError('composition input differs from approved reading chain')
    if author['session'] == reviewer['session']:
        raise ValueError('composition review must use a separate model session')
    if verdict != dict(verdict='approve', proposal_sha=digest(header), bundle_sha=expected['bundle_sha'], findings=[]):
        raise ValueError('independent composition review has not approved the exact proposal')
    validate(packet, evidence)
    return packet, evidence
