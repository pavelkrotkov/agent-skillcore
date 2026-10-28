"""Versioned refresh coverage from unchanged controller-supplied notes."""
from .wiki_keys import page_key, reference
from .wiki_notes import MODE
from .wiki_refresh_store import fingerprint

VERSION = 'catalog/v2'


def retained(inputs, pages):
    if 'retained_assignments' not in inputs:
        return set()
    if (inputs['retained_assignments'] not in ('catalog/v1',VERSION) or inputs.get('organization') != MODE
            or inputs.get('refresh') != fingerprint(inputs)):
        raise ValueError('invalid retained assignment contract')
    catalog = inputs['catalog']
    if inputs['retained_assignments'] == VERSION:
        catalog = catalog + inputs.get('retained_catalog_assignments',[])
    return coverage(catalog, changed_keys(pages))


def changed_keys(pages):
    changed = {page_key(page) for page in pages}
    changed.update(page_key(old) for page in pages for old in page.get('replaces', []))
    return changed


def coverage(catalog, changed):
    return {reference(item['reference']) for page in catalog
            if page.get('complete') is True and page_key(page) not in changed
            for item in page['evidence']}
