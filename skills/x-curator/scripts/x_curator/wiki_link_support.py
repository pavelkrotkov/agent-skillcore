"""New link receipts bind explanations to the exact target's evidence."""
from .wiki_keys import page_key, reference


def connected(pages, catalog, enabled):
    if enabled:
        targets = catalog | {page_key(page): page for page in pages}
        for page in pages:
            connections(page, targets)


def connections(page, targets):
    for edge in page['related']:
        target = targets[page_key(edge)]
        refs = target.get('claims') or [item['reference'] for item in target['evidence']]
        if not set(map(reference, edge['claims'])) & set(map(reference, refs)):
            raise ValueError('related links require target evidence as well as page evidence')
