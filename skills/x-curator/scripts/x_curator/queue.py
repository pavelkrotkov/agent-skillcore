"""One unresolved job per account/source, with every selection retained separately."""
def initialize(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            account TEXT NOT NULL, id TEXT NOT NULL, created REAL NOT NULL,
            state TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
            max_attempts INTEGER NOT NULL DEFAULT 3, next_at REAL NOT NULL DEFAULT 0,
            token TEXT, lease_until REAL, action TEXT NOT NULL DEFAULT 'bounded quick fact-check',
            PRIMARY KEY(account,id)
        );
        CREATE TABLE IF NOT EXISTS attempts (
            token TEXT PRIMARY KEY, account TEXT NOT NULL, id TEXT NOT NULL,
            started REAL NOT NULL, expires REAL NOT NULL, finished REAL,
            state TEXT NOT NULL, action TEXT,
            FOREIGN KEY(account,id) REFERENCES jobs(account,id)
        );
        CREATE TABLE IF NOT EXISTS queue_checkpoint (
            singleton INTEGER PRIMARY KEY CHECK(singleton=1), selection_rowid INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS queue_turns (
            account TEXT PRIMARY KEY, turn INTEGER NOT NULL DEFAULT 0
        );
    """)


def enqueue(db):
    """Advance an atomic intake watermark; unchanged polls never reserve the writer."""
    initialize(db)
    tip = db.execute('SELECT coalesce(max(rowid),0) FROM selections').fetchone()[0]
    seen = checkpoint(db)
    if seen == tip:
        return counts(db)
    with db:
        db.execute('BEGIN IMMEDIATE')
        tip = db.execute('SELECT coalesce(max(rowid),0) FROM selections').fetchone()[0]
        seen = checkpoint(db)
        if seen == tip:
            return counts(db)
        # Canonical selections are append-only; reconcile safely if maintenance rewinds rowids.
        start = seen if seen < tip else 0
        db.execute("""INSERT OR IGNORE INTO jobs(account,id,created,action)
            SELECT c.account,s.id,min(r.fetched),'bounded quick fact-check' FROM selections s
            JOIN collections c ON c.id=s.run
            JOIN responses r ON r.run=s.run AND r.number=s.response
            WHERE s.rowid>? AND s.rowid<=? GROUP BY c.account,s.id""", (start, tip))
        db.execute('INSERT INTO queue_checkpoint VALUES (1,?) ON CONFLICT(singleton) DO UPDATE SET selection_rowid=excluded.selection_rowid', (tip,))
    return counts(db)


def checkpoint(db):
    row = db.execute('SELECT selection_rowid FROM queue_checkpoint WHERE singleton=1').fetchone()
    return row[0] if row else 0


def counts(db):
    rows = db.execute("SELECT account,state,count(*) AS count FROM jobs GROUP BY account,state")
    return [dict(row) for row in rows]


def recover(db, account, now, technical_retries=False):
    from .deep_store import recover as recover_deep
    recover_deep(db, account, now)
    if technical_retries:
        from .quick_retry_interrupted import recover as interrupted
        interrupted(db, account, now)
    # Recovery consumes the original attempt; a restart never grants a fresh budget.
    db.execute("""UPDATE attempts SET state='expired',finished=?,action='worker lease expired'
        WHERE account=? AND state='leased' AND expires<=?""", (now, account, now))
    db.execute("""UPDATE jobs SET state=CASE WHEN attempts<max_attempts THEN 'retry' ELSE 'needs_action' END,
        action=CASE WHEN attempts<max_attempts THEN 'retry interrupted research' ELSE 'attempt budget exhausted; diagnose worker failure' END,
        token=NULL,lease_until=NULL WHERE account=? AND state='leased' AND lease_until<=?""", (account, now))


def outstanding(db):
    return [dict(row) for row in db.execute(
        "SELECT account,id,state,attempts,max_attempts,next_at,action FROM jobs WHERE state!='published' ORDER BY created,id")]
