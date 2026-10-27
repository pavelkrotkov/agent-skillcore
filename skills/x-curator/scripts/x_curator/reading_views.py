"""Explicit partial reading views retain original intervals and overlapping context."""
from .receipts import digest

from .reading_plan import POLICIES
from .reading_ranges import context as boundaries
from . import pdf_views


def view(evidence, reading, index):
    context = POLICIES[reading['version']]['context']
    fragments = [fragment(evidence, span, context) for span in reading['parts'][index]]
    result = {'account': evidence['account'], 'source': evidence['source'],
            'reading_view': {'plan_sha': digest(reading), 'index': index},
            'captures': {key: capture for key, capture, _ in fragments},
            'boundary_context': {key: context for key, _, context in fragments}}
    return pdf_views.number_images(result) if reading['version'] == 2 else result


def fragment(evidence, span, context):
    original = evidence['captures'][span['capture']]
    text = original.get('text', '')
    left, right = boundaries(text, span['start'], span['end'], context)
    context = {'before': text[left:span['start']], 'after': text[span['end']:right]}
    lines = text[span['start']:span['end']].splitlines(keepends=True)
    capture = {key: value for key, value in original.items() if key != 'text'}
    capture['text_lines'] = {f'L{index:06}': line for index, line in enumerate(lines)}
    if original['kind'] == 'pdf':
        capture = pdf_views.fragment(original, span, capture)
    return span['capture'], capture, context


def request(evidence, reading, index, role, proposal=None, feedback=None, correction=False):
    evidence_view = view(evidence, reading, index)
    result = {'role': role, 'bundle': evidence_view, 'bundle_sha': digest(evidence_view),
              'proposal': proposal, 'reading': {'stage': 'segment', 'plan_sha': digest(reading), 'index': index}}
    if feedback is not None:
        result['review_feedback'] = feedback
    if correction:
        result['reading']['correction'] = True
    return result


def slot(reading, index, role, correction=False):
    return f'read:{digest(reading)}:{index}:{role}' + (':correction' if correction else '')
