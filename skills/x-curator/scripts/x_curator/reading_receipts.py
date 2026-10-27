"""Reconstruct each reading request and validate its independent exact approval."""
from . import reading_citations, reading_views, reading_packets, reading_verdicts
from .executions import verified_execution
from .receipts import digest
from .model_trace import envelope


def approved(db, token, evidence, reading, index, pair):
    packet, verdict = reviewed(db, token, evidence, reading, index, pair)
    if verdict['verdict'] != 'approve':
        raise ValueError('segment lacks independent approval')
    return packet


def reviewed(db, token, evidence, reading, index, pair):
    correction = reading_verdicts.correction(pair)
    feedback = rejection(db, token, evidence, reading, index, pair['rejected']) if correction else None
    author, request, packet = verify(db, token, pair['proposal'], reading_views.slot(reading, index, 'research', correction), 'research')
    reviewer, review_request, verdict = verify(db, token, pair['review'], reading_views.slot(reading, index, 'review', correction), 'review')
    expected = reading_views.request(evidence, reading, index, 'research', feedback=feedback, correction=correction)
    packet = reading_citations.materialize(packet, expected['bundle'])
    if request != expected or review_request != reading_views.request(evidence, reading, index, 'review', packet, correction=correction):
        raise ValueError('reading request differs from original evidence interval')
    if author['session'] == reviewer['session']:
        raise ValueError('segment review must use a separate model session')
    reading_packets.validate(packet, expected['bundle'])
    reading_verdicts.validate_verdict(verdict, packet, expected['bundle_sha'])
    return packet, verdict


def rejection(db, token, evidence, reading, index, pair):
    packet, verdict = reviewed(db, token, evidence, reading, index, pair)
    if verdict['verdict'] != 'reject':
        raise ValueError('correction requires an authenticated rejected proposal')
    return {'review': pair['review'], 'proposal': packet, 'findings': verdict['findings']}


def verify(db, token, identity, slot, role):
    row, request, output = verified_execution(db, identity, slot, token, role)
    if envelope(row['log']) is None:
        raise ValueError('segmented reading requires complete model-input proof')
    return row, request, output
