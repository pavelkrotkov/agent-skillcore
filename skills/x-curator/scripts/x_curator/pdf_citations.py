"""PDF citations bind exact original offsets or an explicitly observed physical page."""
from .claim_validation import nonempty


from .pdf_citation_locations import pages_at


def validate(cite, capture):
    if cite['quote'] == '':
        validate_visual(cite, capture)
        return
    nonempty(cite['quote'])
    start, end = cite['pdf_offsets']
    base = capture.get('primary_start', 0)
    if not base <= start < end <= base + len(capture['text']):
        raise ValueError('PDF citation escapes its assigned text')
    if cite['quote'] != capture['text'][start - base:end - base] or cite['pdf_pages'] != pages_at(capture, start, end):
        raise ValueError('PDF quotation or physical page reference changed')


def validate_visual(cite, capture):
    pages = {p['number']: p for p in capture['pages']}
    if len(cite['pdf_pages']) != 1 or 'pdf_offsets' in cite:
        raise ValueError('PDF visual citation requires one unambiguous physical page')
    page = pages[cite['pdf_pages'][0]]
    if cite['pdf_image'] != page['image'] or page['image'] not in capture['images']:
        raise ValueError('PDF visual citation lacks its assigned page pixels')
    nonempty(cite['observation'])
