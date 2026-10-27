"""Authenticated omitted targets inform context, never approval or extra attempts."""
import json

from .wiki_catalog import prepare as catalog
from .wiki_keys import distinct_pages, page_key
from .wiki_final import output
from .model_trace import envelope, verify_request
from .receipts import digest
from .wiki_prompts import request
from .wiki_review_catalog import review_keys


def prepare(db, current, pages, selected):
    inputs = catalog(current, pages, selected)
    keys = required_keys(db, inputs) | review_keys(db, inputs, pages)
    return catalog(current, pages, selected, keys) if keys else inputs


def required_keys(db, inputs):
    identity = digest(inputs)
    row = db.execute('''SELECT * FROM wiki_runs WHERE state='failed' AND proposal IS NOT NULL
        AND review IS NULL AND (input_sha=? OR
        CASE WHEN json_valid(input) THEN json_extract(input,'$.feedback.input_sha') END=?)
        ORDER BY started DESC,id DESC LIMIT 1''', (identity, identity)).fetchone()
    if row is None:
        return set()
    try:
        return verified_keys(row, inputs)
    except (ValueError, KeyError, TypeError, AttributeError):
        return set()


def verified_keys(row, inputs):
    original = json.loads(row['input'])
    base = dict(original)
    base.pop('feedback', None)
    if digest(original) != row['input_sha'] or digest(base) != digest(inputs) or envelope(row['proposal']) is None:
        raise ValueError('catalog recovery requires authenticated unchanged inputs')
    verify_request(row['proposal'], request('organize', original))
    packet = output(row['proposal'], original)
    if packet['input_sha'] != digest(original):
        raise ValueError('catalog recovery proposal uses stale inputs')
    return distinct_pages(packet['pages']) & set(inputs['known_keys']) - {page_key(p) for p in inputs['catalog']}
