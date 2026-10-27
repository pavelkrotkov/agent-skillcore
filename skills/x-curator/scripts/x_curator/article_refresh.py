"""Renew only opted-in held articles inside the original intake budgets."""
import sqlite3
import time
from . import article_refresh_store as store, blobs
from .deadlines import until
from .publication_qualification import qualify
from .publication_recovery import complete
from .source_evidence import selected_source


def run(db, root, client):
    store.initialize(db)
    rows = db.execute('''SELECT p.*,j.id AS source_id FROM article_refresh_permissions a
        JOIN publications p ON p.id=a.publication JOIN jobs j ON j.account=p.account AND j.id=p.source
        WHERE p.state='invalid' AND j.token IS NULL AND j.lease_until IS NULL''').fetchall()
    return [renew(db, root, client, row) for row in rows]


def renew(db, root, client, row):
    current = selected_source(db, dict(account=row['account'], id=row['source_id']))
    try:
        deadline = store.reserve(db, row['id'], current, client.account)
    except (ValueError, sqlite3.IntegrityError) as exc:
        return dict(state='held', publication=row['id'], action=str(exc)[:300])
    try:
        with until(deadline):
            qualify(db, row['id'], 'Approved recurring article currentness',
                    acquire_detail=lambda db, row: acquire(db, row, client))
        result = complete(db, root, row['id'], 'Original article currentness verified in new intake collection')
    except Exception as exc:
        result = dict(state='held', publication=row['id'], action=type(exc).__name__ + ': ' + str(exc)[:300])
    store.finish(db, row['id'], current['run'], result)
    return result


def acquire(db, row, client):
    if row['account'] != client.account:
        raise ValueError('article currentness account mismatch')
    status, body = client.detail(row['source'])
    return dict(source=row['source'], account=client.account, status=status,
                fetched=time.time(), body_sha=blobs.put(db, body))
