"""Bounded single-attempt segmented reading never resets a source's retry budget."""
import json

from . import reading_citations, reading_aggregate, reading_audit, reading_packets, reading_plan, reading_views, reading_receipts
from .codex_profile import MODEL
from .evidence import bundle
from .executions import recorded
from .packets import validate
from .publication import publish
from .worker_prompts import prompt
from .media_inputs import requires_partition as page_required


def required(evidence):
    from .receipts import digest
    if page_required(evidence):
        return True
    request = dict(role='research', bundle=evidence, bundle_sha=digest(evidence), proposal=None)
    try:
        prompt(request)
        return False
    except ValueError:
        return True


def run(db, state, token, call):
    evidence = bundle(db, token)
    reading = reading_plan.plan(evidence)
    pairs = [read(db, token, call, evidence, reading, index) for index in range(len(reading['parts']))]
    _, _, template = reading_audit.chain(db, token, evidence, {'plan': reading, 'receipts': pairs})
    request = reading_aggregate.request(evidence, reading, pairs, template, 'research')
    proposal, header = execute(db, token, 'research', call, request)
    packet = reading_aggregate.compose(template, header)
    validate(packet, evidence)
    request = reading_aggregate.request(evidence, reading, pairs, template, 'review', packet)
    review, _ = execute(db, token, 'review', call, request)
    return publish(db, state, token, proposal, review)


def read(db, token, call, evidence, reading, index):
    pair = attempt(db, token, call, evidence, reading, index)
    _, verdict = reading_receipts.reviewed(db, token, evidence, reading, index, pair)
    if verdict['verdict'] == 'reject':
        feedback = reading_receipts.rejection(db, token, evidence, reading, index, pair)
        corrected = attempt(db, token, call, evidence, reading, index, feedback)
        pair = dict(corrected, rejected=pair)
    reading_receipts.approved(db, token, evidence, reading, index, pair)
    return pair


def attempt(db, token, call, evidence, reading, index, feedback=None):
    correction = feedback is not None
    request = reading_views.request(evidence, reading, index, 'research', feedback=feedback, correction=correction)
    proposal, packet = execute(db, token, reading_views.slot(reading, index, 'research', correction), call, request)
    packet = reading_citations.materialize(packet, request['bundle'])
    reading_packets.validate(packet, request['bundle'])
    request = reading_views.request(evidence, reading, index, 'review', packet, correction=correction)
    review, _ = execute(db, token, reading_views.slot(reading, index, 'review', correction), call, request)
    return {'proposal': proposal, 'review': review}


def execute(db, token, slot, call, request):
    identity = recorded(db, token, slot, MODEL, call, request)
    output = db.execute('SELECT output FROM executions WHERE id=?', (identity,)).fetchone()[0]
    return identity, json.loads(output)
