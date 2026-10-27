"""Alternate ordinary categories while allowing immediate fallback to ready work."""
from . import batch_store, daily_plan, daily_store


def ready(db, account, now, kind, unspent_only=False):
    row = db.execute('''SELECT b.id FROM curation_batches b WHERE b.account=? AND b.kind=? AND EXISTS (
        SELECT 1 FROM curation_members m JOIN jobs j ON j.account=m.account AND j.id=m.source
        WHERE m.batch=b.id AND j.state IN ('pending','retry') AND j.next_at<=? AND j.attempts<j.max_attempts AND (?=0 OR j.attempts=0))
        ORDER BY b.created,b.id LIMIT 1''', (account, kind, now, unspent_only)).fetchone()
    return row['id'] if row else None


def current(db, account, now, unspent_only=False):
    batch_store.close_finished(db, account)
    daily_plan.freeze(db, account, now)
    backlog = ready(db, account, now, 'backlog', unspent_only)
    if backlog is None:
        batch_store.form(db, account, now)
        backlog = ready(db, account, now, 'backlog', unspent_only)
    daily = ready(db, account, now, 'daily', unspent_only)
    return (daily or backlog) if daily_store.preferred(db, account) == 'daily' else (backlog or daily)
