"""Persist and execute one bounded, independently observable supervision cycle."""
from . import accounting, cycle_store
from .deadlines import until
from .cycle_stages import phases
from .stage_timings import span


def run(db, root, client, max_items=2, max_sources=0, seconds=1800):
    if not 1 <= seconds <= 3600 or not 0 <= max_items <= 20 or not 0 <= max_sources <= 10:
        raise ValueError('invalid bounded supervisor limits')
    identity, deadline = cycle_store.begin(db, seconds)
    result = {'state': 'checkpoint', 'cycle': identity}
    with span(db, 'cycle.run', cohort=identity, scope='selected',
              concurrency=max_items, selected_sources=max_sources) as timing:
        try:
            with until(deadline):
                phases(db, root, client, identity, max_items, max_sources, deadline, result)
                result['report'] = accounting.report(db, root, wait_for_wiki=True)
            cycle_store.finish(db, identity, 'finished', result)
        except Exception as exc:
            result.update(state='blocked', action=type(exc).__name__ + ': ' + str(exc)[:300])
            cycle_store.finish(db, identity, 'failed', result)
        timing['result_state'] = result['state']
    return result
