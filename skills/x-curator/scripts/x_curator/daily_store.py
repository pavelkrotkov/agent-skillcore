"""One explicit daily policy per account; restarts cannot move its baseline or zone."""
import time
from zoneinfo import ZoneInfo


def initialize(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS daily_settings (
        account TEXT PRIMARY KEY, timezone TEXT NOT NULL, baseline REAL NOT NULL,
        turn INTEGER NOT NULL DEFAULT 0);
        CREATE UNIQUE INDEX IF NOT EXISTS daily_cutoff
        ON curation_batches(account,cutoff) WHERE kind='daily';''')


def configure(db, account, chat, timezone):
    from . import review_store
    ZoneInfo(timezone)
    review_store.initialize(db)
    with db:
        db.execute('BEGIN IMMEDIATE')
        review_store.route(db, account, chat)
        db.execute('INSERT OR IGNORE INTO daily_settings(account,timezone,baseline) VALUES(?,?,?)', (account, timezone, time.time()))
        value = settings(db, account)
        if value['timezone'] != timezone:
            raise ValueError('daily timezone changes require an explicit migration')
        return dict(state='configured', **value)


def settings(db, account):
    row = db.execute('SELECT * FROM daily_settings WHERE account=?', (account,)).fetchone()
    return dict(row) if row else None


def preferred(db, account):
    value = settings(db, account)
    return 'daily' if value and value['turn'] % 2 == 0 else 'backlog'
