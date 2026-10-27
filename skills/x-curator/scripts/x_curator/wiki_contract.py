"""Organizers may classify approved claims but cannot rewrite their evidence."""
from .receipts import digest
from .wiki_keys import claim_index, page_key, distinct_pages, identities
from .wiki_refs import validate_page
from .wiki_link_support import connected
from .wiki_prompts import proposal_capacity
from . import wiki_notes, wiki_note_contract


def validate(packet, inputs):
    proposal_capacity(packet, inputs)
    if packet['input_sha'] != digest(inputs):
        raise ValueError('wiki mapping uses stale inputs')
    claims = claim_index(inputs['sources'])
    required = set(claims)
    if inputs.get('organization') == wiki_notes.MODE:
        claims.update(wiki_notes.evidence(inputs))
    catalog = {page_key(p): p for p in inputs['catalog']}
    pages = packet['pages']
    keys = distinct_pages(pages)
    identities(pages, keys, inputs)
    if keys & set(inputs['known_keys']) - set(catalog):
        raise ValueError('existing page meaning was absent from reviewed catalog')
    assigned = set()
    for page in pages:
        assigned.update(validate_page(page, claims, keys | set(catalog)))
        wiki_note_contract.validate(page, catalog, keys, inputs.get('organization') == wiki_notes.MODE)
    connected(pages, catalog, inputs.get('link_support') == 'target-evidence/v1')
    if not required <= assigned:
        raise ValueError('every verified source claim needs an explicit wiki assignment')


def approved(inputs, proposal, verdict):
    expected = {'verdict': 'approve', 'input_sha': digest(inputs),
                'proposal_sha': digest(proposal), 'findings': []}
    if verdict != expected:
        raise ValueError('wiki mapping lacks independent approval')
    validate(proposal, inputs)
