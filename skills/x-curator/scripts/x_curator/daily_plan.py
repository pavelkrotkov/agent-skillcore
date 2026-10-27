"""Freeze capture-time eligibility at local midnight, including empty cutoffs."""
from datetime import datetime, time
from zoneinfo import ZoneInfo

from . import daily_store
from .receipts import digest


def cutoff(now, timezone):
    zone = ZoneInfo(timezone)
    day = datetime.fromtimestamp(now, zone).date()
    return datetime.combine(day, time(), zone).timestamp()


def freeze(db, account, now):
    settings = daily_store.settings(db, account)
    if settings is None:
        return None
    boundary = cutoff(now, settings['timezone'])
    if boundary <= settings['baseline']:
        return None
    identity = digest(['daily/v1', account, settings['timezone'], boundary])
    created = db.execute("INSERT OR IGNORE INTO curation_batches VALUES (?,?,'daily',?,?,'open')",
                         (identity, account, now, boundary)).rowcount
    if created:
        db.execute('''INSERT INTO curation_members(batch,account,source)
            SELECT ?,j.account,j.id FROM jobs j WHERE j.account=? AND j.created>=? AND j.created<?
            AND j.state!='published' AND NOT EXISTS (
                SELECT 1 FROM curation_members m WHERE m.account=j.account AND m.source=j.id)''',
                   (identity, account, settings['baseline'], boundary))
    return identity


def metadata(db, batch):
    if batch['kind'] != 'daily':
        return {}
    settings = daily_store.settings(db, batch['account'])
    return {'timezone': settings['timezone'],
            'cutoff_local': datetime.fromtimestamp(batch['cutoff'], ZoneInfo(settings['timezone'])).isoformat()}
