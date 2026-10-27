"""Explicit, bounded organization of retained publications; no fact-check retries."""
from .wiki_refresh_store import fingerprint


def command(db, args):
    from . import wiki, wiki_catalog, wiki_index_result, wiki_mapping
    from .wiki_input_load import Snapshot
    selected = args.publication
    if not 1 <= len(selected) <= 10 or len(set(selected)) != len(selected):
        raise ValueError('select one to ten distinct retained publications')
    snapshot, _ = wiki.initial(db, args.state)
    current, _, pages = snapshot.values
    if not set(selected) <= set(current):
        raise ValueError('refresh requires current accepted publications')
    inputs = wiki_catalog.prepare(current, pages, selected, args.page)
    inputs.update(refresh=fingerprint(inputs), refresh_reason=args.reason)
    identity = wiki_mapping.map_sources(db, inputs)
    result = wiki_index_result.publish(db, args.state, Snapshot(db, args.state, 'zk_refresh'))
    return dict(result, organization_run=identity)
