"""Separate historical unobserved digests from newer delivery work."""
from .retention_files import table


def recent(db, cutoff):
    if not table(db, 'review_deliveries'):
        return dict(pending_since_last_observed=0, failures_since_last_observed=0)
    row = db.execute("""SELECT count(*),coalesce(sum(failure IS NOT NULL),0)
        FROM review_deliveries WHERE observed IS NULL AND (? IS NULL OR created>?)""", (cutoff, cutoff)).fetchone()
    return dict(pending_since_last_observed=row[0], failures_since_last_observed=row[1])


def state(counts):
    if counts['pending_since_last_observed']:
        return 'external_consumer_required'
    return 'historical_unobserved' if counts['unobserved'] else 'idle'
