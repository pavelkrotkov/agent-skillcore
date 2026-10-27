"""Assignment and relationship references must resolve to approved claims."""
from .claim_validation import nonempty
from .wiki_keys import page_key, reference


def validate_page(page, claims, keys):
    nonempty(page['description'])
    refs = [reference(r) for r in page['claims']]
    if not refs or len(refs) != len(set(refs)) or not set(refs) <= set(claims):
        raise ValueError('wiki claim references are missing, duplicated or unknown')
    for link in page['related']:
        validate_link(link, page, refs, keys)
    return set(refs)


def validate_link(link, page, refs, keys):
    nonempty(link['reason'])
    support = {reference(r) for r in link['claims']}
    if page_key(link) not in keys or page_key(link) == page_key(page):
        raise ValueError('related page target is missing or self-referential: ' + page_key(page) + ' -> ' + page_key(link))
    if not support or not support <= set(refs):
        raise ValueError('related links require evidence from the page')
