"""Consolidation and prose must retain complete, reviewed support."""
from .claim_validation import nonempty
from .wiki_keys import page_key, reference


def validate(page, catalog, keys, zk=False):
    if not isinstance(page.get('entry', False), bool):
        raise ValueError('entry must be a boolean')
    refs = {reference(ref) for ref in page['claims']}
    prose(page, refs, zk)
    if page.get('synthesis'):
        retain(catalog.get(page_key(page)), refs)
    for previous in page.get('replaces', []):
        key = page_key(previous)
        if key not in catalog or key in keys:
            raise ValueError('consolidation needs a distinct reviewed catalog page')
        retain(catalog[key], refs)


def retain(previous, refs):
    if previous is not None:
        if not previous.get('complete') or not {reference(item['reference']) for item in previous['evidence']} <= refs:
            raise ValueError('revising a note requires its complete reviewed evidence')


def prose(page, refs, zk):
    if zk and not page.get('synthesis'):
        raise ValueError('ZK notes require a supported synthesis')
    for block in page.get('synthesis', []) + page.get('questions', []):
        nonempty(block['text'])
        support = {reference(ref) for ref in block['claims']}
        if not support or not support <= refs:
            raise ValueError('ZK prose requires supporting page claims')
