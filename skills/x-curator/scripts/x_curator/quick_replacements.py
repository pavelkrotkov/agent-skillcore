"""Replacement checks append history; source attempts bound chain resolution."""
import json
import time

from .receipts import digest


def migrate(db):
    sql = db.execute("SELECT sql FROM sqlite_master WHERE name='quick_recoveries'").fetchone()[0]
    legacy = ', UNIQUE(account,source)'
    if legacy not in sql:
        return
    with db:
        db.execute('BEGIN IMMEDIATE')
        db.execute(sql.replace('quick_recoveries', 'quick_recoveries_next', 1).replace(legacy, ''))
        db.execute('INSERT INTO quick_recoveries_next SELECT * FROM quick_recoveries')
        db.execute('DROP TABLE quick_recoveries')
        db.execute('ALTER TABLE quick_recoveries_next RENAME TO quick_recoveries')


def latest(db, account, source, identity):
    job = db.execute('SELECT max_attempts FROM jobs WHERE account=? AND id=?', (account, source)).fetchone()
    if job is None:
        raise ValueError('replacement source job is missing')
    for _ in range(job[0]):
        row = db.execute('SELECT * FROM quick_recoveries WHERE original=?', (identity,)).fetchone()
        if row is None:
            return identity
        if (row['account'], row['source']) != (account, source):
            raise ValueError('replacement belongs to another source')
        identity = row['replacement']
    raise ValueError('replacement chain exceeds the source attempt bound')


def replacement(db, job, identity, revision):
    # quick_store.start owns the writer transaction: the link and child row commit together.
    previous = db.execute('''SELECT q.revision FROM quick_retry_failures f JOIN quick_checks q ON q.id=f.check_id
        WHERE q.account=? AND q.source=? ORDER BY f.created DESC LIMIT 1''', (job['account'], job['id'])).fetchone()
    if previous and previous['revision'] != revision:
        raise ValueError('technical retry source revision changed; explicit review required')
    row = db.execute('''SELECT q.id,q.token FROM quick_checks q JOIN quick_retry_failures f ON f.token=q.token
        WHERE q.id=?''', (identity,)).fetchone()
    if row is None:
        return identity
    if row['token'] == job['token']:
        raise ValueError('this technical attempt is already spent')
    child = digest(['technical-retry/v1', identity, job['attempts']])
    db.execute('INSERT INTO quick_recoveries VALUES (?,?,?,?,?,?,NULL)',
               (identity, child, job['account'], job['id'], time.time(), json.dumps({'technical_failure': row['token']})))
    return child
