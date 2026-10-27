"""Materialize model-selected line ranges without altering original source characters."""
from .receipts import digest
from . import pdf_citation_locations

def captures(evidence):
    return {key: dict(capture, text=''.join(capture['text_lines'][line] for line in sorted(capture['text_lines'])))
            for key, capture in evidence['captures'].items()}


def materialize(packet, evidence):
    if packet.get('unresolved'):
        return packet
    claims = [dict(claim, citations=[citation(cite, evidence) for cite in claim['citations']])
              for claim in packet['claims']]
    return dict(packet, source=evidence['source'], bundle_sha=digest(evidence), claims=claims)


def citation(cite, evidence):
    capture = evidence['captures'][cite['capture']]
    if 'quote' in cite:
        return visual(cite, capture)
    lines = capture['text_lines']
    keys = sorted(lines)
    first, last = keys.index(cite['line_start']), keys.index(cite['line_end'])
    if last < first:
        raise ValueError('reversed original line range')
    quote = ''.join(lines[key] for key in keys[first:last+1])
    location = pdf_citation_locations.text_location(capture, keys, first, last) if capture['kind'] == 'pdf' else {}
    return dict(capture=cite['capture'], quote=quote, observation=cite.get('observation', ''), **location)


def visual(cite, capture):
    if cite['quote'] != '' or 'line_start' in cite or 'line_end' in cite:
        raise ValueError('text citations require unambiguous original line references')
    return pdf_citation_locations.visual(cite, capture) if capture['kind'] == 'pdf' else dict(cite)
