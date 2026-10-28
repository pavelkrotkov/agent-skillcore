"""Explicit, bounded organization of retained publications; no fact-check retries."""
from .wiki_refresh_store import fingerprint, selection
from .wiki_retained_assignments import VERSION
from .wiki_retained_catalog import omitted


def command(db, args):
    from . import wiki, wiki_catalog, wiki_index_result, wiki_mapping
    from .wiki_input_load import Snapshot
    selected = args.publication
    selection(selected)
    fifth = getattr(args, 'grant_fifth_attempt', False)
    sixth = getattr(args, 'grant_sixth_attempt', False)
    if getattr(args, 'grant_extra_attempt', False) or fifth or sixth:
        from .wiki_refresh_recovery import grant
        return grant(db, selected, args.reason, fifth=fifth, sixth=sixth)
    snapshot, _ = wiki.initial(db, args.state)
    current, _, pages = snapshot.values
    if not set(selected) <= set(current):
        raise ValueError('refresh requires current accepted publications')
    inputs = wiki_catalog.prepare(current, pages, selected, args.page)
    inputs.update(refresh=fingerprint(inputs), refresh_reason=args.reason, retained_assignments=VERSION,
                  retained_catalog_assignments=omitted(pages,inputs['catalog'],set(selected)))
    identity = wiki_mapping.map_sources(db, inputs)
    result = wiki_index_result.publish(db, args.state, Snapshot(db, args.state, 'zk_refresh'))
    return dict(result, organization_run=identity)
