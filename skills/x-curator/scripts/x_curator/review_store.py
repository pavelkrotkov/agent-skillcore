"""Private outbox and item permissions; never exposed to the fact-checking model."""
from . import batch_store


def initialize(db):
    batch_store.initialize(db)
    db.executescript('''CREATE TABLE IF NOT EXISTS review_routes (
        account TEXT PRIMARY KEY, chat TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS review_deliveries (
        id TEXT PRIMARY KEY, batch TEXT UNIQUE NOT NULL REFERENCES curation_batches(id),
        chat TEXT NOT NULL, payload TEXT NOT NULL, message TEXT NOT NULL,
        created REAL NOT NULL, observed TEXT, failure TEXT);
        CREATE TABLE IF NOT EXISTS review_replies (
        chat TEXT NOT NULL, message TEXT NOT NULL, delivery TEXT NOT NULL REFERENCES review_deliveries(id),
        receipt TEXT NOT NULL, readback TEXT NOT NULL, PRIMARY KEY(chat,message));
        CREATE TABLE IF NOT EXISTS review_decisions (
        delivery TEXT NOT NULL REFERENCES review_deliveries(id), reference TEXT NOT NULL,
        action TEXT NOT NULL CHECK(action IN ('research','defer','exclude')),
        reply TEXT NOT NULL, created REAL NOT NULL, PRIMARY KEY(delivery,reference));
        CREATE TABLE IF NOT EXISTS research_permissions (
        id TEXT PRIMARY KEY, delivery TEXT NOT NULL, reference TEXT NOT NULL,
        account TEXT NOT NULL, source TEXT NOT NULL, revision TEXT NOT NULL,
        question TEXT NOT NULL, scope TEXT NOT NULL, seconds INTEGER NOT NULL CHECK(seconds>0),
        consumed REAL, UNIQUE(delivery,reference),
        FOREIGN KEY(delivery,reference) REFERENCES review_decisions(delivery,reference));
        CREATE TABLE IF NOT EXISTS research_supersessions (
        previous TEXT PRIMARY KEY REFERENCES research_permissions(id),
        replacement TEXT NOT NULL REFERENCES research_permissions(id));
        DROP INDEX IF EXISTS research_unspent_source;''')


def route(db, account, chat):
    if not isinstance(chat, str) or not chat.strip():
        raise ValueError('originating chat is required')
    db.execute('INSERT OR IGNORE INTO review_routes VALUES (?,?)', (account, chat))
    if db.execute('SELECT chat FROM review_routes WHERE account=?', (account,)).fetchone()[0] != chat:
        raise ValueError('review delivery cannot move to another chat')


def delivery(db, identity):
    row = db.execute('SELECT * FROM review_deliveries WHERE id=?', (identity,)).fetchone()
    if row is None:
        raise ValueError('unknown approval digest')
    return dict(row)
