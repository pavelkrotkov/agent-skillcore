"""Assigned physical pages map to the exact ordered native image attachments."""
from .pdf_ranges import assigned
from .media_inputs import identities


def fragment(original, span, capture):
    pages = [dict(page) for page in assigned(original, span)]
    return dict(capture, pages=pages, images=sorted({p['image'] for p in pages}),
                primary_start=span['start'], primary_end=span['end'])


def number_images(evidence):
    positions = {sha: index for index, sha in enumerate(sorted(identities(evidence)), 1)}
    for capture in evidence['captures'].values():
        if capture['kind'] == 'pdf':
            capture['pages'] = [dict(page, attachment=positions[page['image']]) for page in capture['pages']]
    return evidence
