"""Every physical page needs independently reviewed visual coverage, even without text."""
from .claim_validation import nonempty


def validate(item, capture):
    if capture['kind'] != 'pdf':
        return
    pages = item['pages']
    expected = [p['number'] for p in capture['pages']]
    if sorted(p['number'] for p in pages) != expected:
        raise ValueError('every physical PDF page needs distinct reviewed coverage')
    for page in pages:
        if page['status'] != 'reviewed':
            raise ValueError('unread PDF page pixels require recovery')
        nonempty(page['notes'])


def combined(key, capture, packets):
    if capture['kind'] != 'pdf':
        return {}
    pages = [p for packet in packets for item in packet['coverage'] if item['capture'] == key for p in item['pages']]
    return {'pages': pages}
