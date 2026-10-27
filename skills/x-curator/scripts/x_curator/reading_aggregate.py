"""Composition preserves every approved claim verbatim under globally distinct IDs."""
from .receipts import digest
from .pdf_coverage import combined


def template(evidence, packets):
    claims = []
    limits = []
    notes = {}
    for index, packet in enumerate(packets):
        claims.extend(dict(claim, id=f'{index}:{claim["id"]}') for claim in packet['claims'])
        limits.extend(packet['limitations'])
        for item in packet['coverage']:
            notes.setdefault(item['capture'], []).append(item['notes'])
    coverage = [dict(capture=key, status=status(capture), notes='\n'.join(notes[key]), **combined(key, capture, packets))
                for key, capture in sorted(evidence['captures'].items())]
    return dict(source=evidence['source'], bundle_sha=digest(evidence), claims=claims,
                limitations=list(dict.fromkeys(limits)), coverage=coverage)


def status(capture):
    return {'metadata': 'metadata_only', 'unavailable': 'unavailable'}.get(capture['kind'], 'covered')


def request(evidence, reading, pairs, packet, role, proposal=None):
    if proposal is not None:
        proposal = {key: proposal[key] for key in ('title', 'summary')}
    claims = [{key: value for key, value in claim.items() if key != 'citations'} for claim in packet['claims']]
    approved_view = {'account': evidence['account'], 'source': evidence['source'], 'captures': {},
                     'approved_segment_claims': dict(packet, claims=claims), 'original_bundle_sha': digest(evidence)}
    return {'role': role, 'bundle': approved_view, 'bundle_sha': digest(approved_view), 'proposal': proposal,
            'reading': {'stage': 'composition', 'plan': reading, 'receipts': pairs}}


def compose(template_packet, header):
    if set(header) != {'title', 'summary'}:
        raise ValueError('composition must contain only a title and summary')
    return dict(template_packet, **header)
