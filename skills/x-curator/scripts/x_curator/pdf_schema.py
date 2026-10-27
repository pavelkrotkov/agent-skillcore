"""Validate immutable PDF rendering metadata without silently regenerating old pixels."""
from .pdf_pages import intervals, dimensions
from .pdf_reader import FLAGS
from .storage import sha256


def validate(capture):
    policy, pages = capture['pdf'], capture['pages']
    expected = list(intervals(capture['text'], policy['page_count']))
    if (policy['version'], policy['pdf_sha'], policy['text_sha'], policy['extract_flags'], policy['render_flags']) != (
            1, capture['body_sha'], sha256(capture['text'].encode()), ['-layout'], FLAGS):
        raise ValueError('PDF extraction/rendering provenance changed')
    if not policy['extractor'].startswith('pdftotext version ') or not policy['renderer'].startswith('pdftoppm version '):
        raise ValueError('PDF tool versions are missing')
    validate_pages(capture, pages, expected)


def validate_pages(capture, pages, expected):
    if len(pages) != len(expected) or capture['images'] != sorted({p['image'] for p in pages}):
        raise ValueError('PDF pages or image inventory changed')
    for page, span in zip(pages, expected):
        if {key: page[key] for key in span} != span:
            raise ValueError('PDF physical page identities or text offsets changed')


def verify_pixels(db, capture):
    from .blobs import read
    validate(capture)
    for page in capture['pages']:
        if dimensions(read(db, page['image'])) != (page['width'], page['height']):
            raise ValueError('PDF retained page dimensions changed')
