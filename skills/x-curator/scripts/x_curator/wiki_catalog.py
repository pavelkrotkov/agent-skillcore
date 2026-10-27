"""Bounded semantic context prevents unrelated meanings from being merged."""

from .receipts import digest, encoded
from .wiki_keys import claim_index, page_key, reference
from .wiki_prompts import preflight
from .wiki_notes import MODE, retired
from .quick_final import FORMAT
from .wiki_catalog_topics import ranked_pages, selected_text


def prepare(current, pages, selected, required_keys=()):
    required = set(required_keys)
    if not required <= pages.keys():
        raise ValueError('required existing catalog page is unknown')
    required = required_context(pages, required)
    text = selected_text(current, selected)
    ranked = ranked_pages(pages, text, required)
    claims = claim_index(current)
    inputs = {'publication_references': 'short/v1', 'final_format': FORMAT, 'projection': 1, 'catalog_projection': 2, 'organization': MODE, 'link_support': 'target-evidence/v1',
              'sources': {key: projected(current[key], key) for key in selected}, 'catalog': [],
              'known_keys': sorted(pages), 'retired_keys': retired(pages),
              'catalog_sha': digest(pages), 'publications_sha': digest(current)}
    budget = min(preflight(inputs), 100000)
    # ponytail: bound full evidence at 100k; required keys recover omitted meanings.
    for page in ranked:
        entry = catalog_page(page, claims, selected)
        size = len(encoded(entry).decode()) + bool(inputs['catalog'])
        if size > budget:
            if page_key(page) in required:
                raise ValueError('required existing page meaning exceeds catalog budget')
            break
        inputs['catalog'].append(entry)
        budget -= size
    return inputs


def required_context(pages, required):
    return required | {page_key(link) for key in required for link in pages[key]['related']}


def catalog_page(page, claims, selected=()):
    return {key: page[key] for key in ('kind', 'title', 'description', 'aliases')} | {
        'complete': True, 'entry': page.get('entry', False), 'redirects': page.get('redirects', []),
        'synthesis': page.get('synthesis', []), 'questions': page.get('questions', []), 'related': page['related'],
        'evidence': [dict(reference=r) if r['publication'] in selected else
                     dict(claim_prose(claims[reference(r)]), reference=r) for r in page['claims']]}


def claim_prose(claim):
    return {key: value for key, value in claim.items() if key != 'citations'}


def projected(source, identity):
    packet = dict(source['packet'], claims=[claim_prose(claim) for claim in source['packet']['claims']])
    return dict(source, packet=packet, publication=identity)
