"""The controller derives original page and character locations from model selectors."""
from .claim_validation import nonempty


def pages_at(capture, start, end):
    return [p['number'] for p in capture['pages'] if p['start'] < end and p['end'] > start]


def text_location(capture, keys, first, last):
    lines = capture['text_lines']
    start = capture['primary_start'] + sum(len(lines[key]) for key in keys[:first])
    end = start + sum(len(lines[key]) for key in keys[first:last + 1])
    return {'pdf_offsets': [start, end], 'pdf_pages': pages_at(capture, start, end)}


def visual(cite, capture):
    if type(cite['page']) is not int:
        raise ValueError('PDF visual citation requires a physical page number')
    page = {p['number']: p for p in capture['pages']}[cite['page']]
    return {'capture': cite['capture'], 'quote': '', 'observation': nonempty(cite['observation']),
            'pdf_pages': [page['number']], 'pdf_image': page['image']}
