"""Whole physical pages remain indivisible primary reading assignments."""
from .pdf_schema import validate


def split(capture, width, count):
    validate(capture)
    pages = capture['pages']
    first = 0
    for index, page in enumerate(pages):
        if page['end'] - page['start'] > width:
            raise ValueError('one PDF page exceeds the qualified text allowance')
        if index > first and (index - first >= count or page['end'] - pages[first]['start'] > width):
            yield span(pages[first], pages[index - 1])
            first = index
    yield span(pages[first], pages[-1])


def span(first, last):
    return {'start': first['start'], 'end': last['end'], 'page_start': first['number'], 'page_end': last['number']}


def assigned(capture, interval):
    return capture['pages'][interval['page_start'] - 1:interval['page_end']]


def images(capture, interval):
    if capture['kind'] == 'pdf':
        return {p['image'] for p in assigned(capture, interval)}
    return set(capture.get('images', []))
