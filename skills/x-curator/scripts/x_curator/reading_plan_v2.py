"""Page-aware reading accounts for PDF pixels and ordinary media together."""
from . import pdf_ranges
from .reading_ranges import split
from .receipts import digest


def intervals(evidence, policy):
    for key, capture in sorted(evidence['captures'].items()):
        spans = pdf_ranges.split(capture, policy['width'], policy['images']) if capture['kind'] == 'pdf' else (
            {'start': start, 'end': end} for start, end in split(capture.get('text', ''), policy['width']))
        for span in spans:
            yield dict(span, capture=key, capture_sha=digest(capture))


def groups(evidence, policy):
    parts, current, size, images = [], [], 0, set()
    for span in intervals(evidence, policy):
        length = span['end'] - span['start']
        pixels = pdf_ranges.images(evidence['captures'][span['capture']], span)
        if len(pixels) > policy['images']:
            raise ValueError('one capture exceeds the qualified image allowance')
        if current and full(current, size + length, images | pixels, span, policy):
            parts.append(current)
            current, size, images = [], 0, set()
        current.append(span)
        size += length
        images.update(pixels)
    return parts + [current]


def full(current, size, images, span, policy):
    return size > policy['width'] or len(images) > policy['images'] or span['capture'] in {p['capture'] for p in current}
