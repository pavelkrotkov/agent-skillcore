"""Reconcile every selected identity against audited publications and an active wiki."""
import json
from . import provider_health, wiki_store, cycle_store
from .process_liveness import state as liveness
from .queue import enqueue
from .receipts import initialize as receipts
from .publication_audit import audit
from .wiki_current import current
from .command_lock import lockfile


def report(db, root):
    enqueue(db)
    receipts(db)
    wiki_store.initialize(db)
    cycle_store.initialize(db)
    invalidated = audit(db, root)
    with lockfile(root, '.wiki.lock'):
        wiki = wiki_status(db, root)
    sources = [dict(row) for row in db.execute('''SELECT j.account,j.id,j.state,j.attempts,j.max_attempts,
        j.next_at,j.lease_until,j.action,count(DISTINCT p.id) AS publications FROM jobs j
        LEFT JOIN publications p ON p.account=j.account AND p.source=j.id AND p.state='published'
        GROUP BY j.account,j.id ORDER BY j.created,j.id''')]
    counts = {}
    for source in sources:
        counts[source['state']] = counts.get(source['state'], 0) + 1
    return {'state': 'checkpoint', 'historical_complete': False,
            'coverage_action': 'Recover older likes through a fresh official X archive; timeline coverage is unproven.',
            'selected_sources': len(sources), 'counts': counts, 'sources': sources, 'invalidated': invalidated,
            'wiki': wiki, 'operations': operations(db), 'provider': provider_health.blocked(db)}


def wiki_status(db, root):
    try:
        manifest = current(db, root)
        return {'state': 'verified', 'manifest': manifest} if manifest else {'state': 'absent', 'action': 'build verified source mappings'}
    except (ValueError, OSError, KeyError, TypeError) as exc:
        return {'state': 'withdrawn', 'action': str(exc)}


def operations(db):
    cycles = [dict(row) for row in db.execute("SELECT id,started,deadline,finished,pid,process_start,stage,state,json_extract(result,'$.work.dependency') AS dependency FROM cycles ORDER BY started DESC LIMIT 3")]
    for cycle in cycles:
        cycle['liveness'] = liveness(cycle)
        cycle['dependency'] = json.loads(cycle['dependency'] or 'null')
    collections = [dict(row) for row in db.execute('SELECT id,kind,state,requests,reason FROM collections ORDER BY started')]
    mappings = [dict(row) for row in db.execute('SELECT publication,attempts,run,action FROM wiki_sources')]
    return {'collections': collections, 'cycles': cycles, 'mapping_attempts': mappings}
