"""Intake and research are independent; reserve time to publish accumulated knowledge."""
from . import cycle_store, intake, wiki_store
from .command_lock import lockfile
from .deadlines import until, DeadlineExceeded
from .publication_audit import audit
from .queue import enqueue
from .receipts import initialize as receipts
from .wiki import run as wiki
from .worker import work
from .review_reconcile import flush
from .stage_timings import span, skip




def phases(db, root, client, identity, max_items, max_sources, deadline, result):
    cycle_store.stage(db, identity, 'intake')
    with span(db, 'cycle.intake', scope='selected'):
        with lockfile(root, '.collector.lock'):
            result['intake'] = [intake.poll(db, client, kind) for kind in ('likes', 'bookmarks')]
        enqueue(db)
        receipts(db)
        wiki_store.initialize(db)
        result['invalidated'] = audit(db, root)
        from .article_refresh import run as refresh_articles
        with lockfile(root, '.collector.lock'), lockfile(root, '.publication-recovery.lock'):
            result['article_currentness'] = refresh_articles(db, root, client)
    cycle_store.stage(db, identity, 'research')
    if max_items:
        with span(db, 'cycle.research', scope='selected', concurrency=max_items):
            result['work'] = research_stage(db, root, client, max_items, deadline)
    else:
        skip(db, 'cycle.research', 'bounded cycle requested no items')
    result['review_outbox'] = flush(db, client.account)
    cycle_store.stage(db, identity, 'wiki')
    with span(db, 'cycle.wiki', scope='corpus', selected_sources=max_sources):
        with until(deadline), lockfile(root, '.wiki.lock', blocking=True):
            result['wiki'] = organize(db, root, max_sources)
    cycle_store.stage(db, identity, 'reconciled')


def organize(db, root, max_sources):
    try:
        return wiki(db, root, max_sources)
    except (ValueError, RuntimeError) as exc:
        return {'state': 'blocked', 'action': str(exc)[:300]}


def research_stage(db, root, client, max_items, deadline):
    import time
    remaining = deadline - time.time()
    try:
        with until(deadline - min(900, remaining / 3)):
            return work(db, root, client, max_items)
    except DeadlineExceeded:
        return {'state': 'checkpoint', 'action': 'research phase deadline; remaining work retained'}
