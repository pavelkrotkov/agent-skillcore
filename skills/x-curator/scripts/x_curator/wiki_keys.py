"""Stable semantic page keys and composite evidence identities."""
import re
import unicodedata

from .claim_validation import nonempty
from .receipts import digest


def page_key(page):
    if page['kind'] not in ('concept', 'entity'):
        raise ValueError('wiki pages must be concepts or entities')
    title = ' '.join(unicodedata.normalize('NFKC', nonempty(page['title'])).casefold().split())
    slug = re.sub('[^a-z0-9]+', '-', title).strip('-')[:60] or 'topic'
    return {'concept': 'concepts', 'entity': 'entities'}[page['kind']] + '/' + slug + '-' + digest(title)[:10]


def reference(value):
    return value['publication'], value['claim']


def claim_index(sources):
    return {(identity, claim['id']): claim for identity, source in sources.items()
            for claim in source['packet']['claims']}


def distinct_pages(pages):
    keys = {page_key(p) for p in pages}
    if not pages or len(keys) != len(pages) or len(pages) > 30:
        raise ValueError('distinct meaningful wiki pages required')
    return keys


def identities(pages, keys, inputs):
    replaced = [page_key(old) for page in pages for old in page.get('replaces', [])]
    if keys & set(inputs.get('retired_keys', [])) or len(replaced) != len(set(replaced)):
        raise ValueError('retired note identities or conflicting consolidations')
