"""Explicit operator recovery appends a bounded grant without erasing prior attempts."""
import time
import uuid


def command(db, args):
    if args.command == 'recover-wiki':
        from .wiki_recovery import grant as mapping_grant
        return mapping_grant(db, args.publication, args.reason)
    from .publication_recovery import complete
    return complete(db, args.state, args.publication, args.reason)


def initialize(db):
    db.execute('''CREATE TABLE IF NOT EXISTS recovery_grants (
        id TEXT PRIMARY KEY,account TEXT NOT NULL,source TEXT NOT NULL,created REAL NOT NULL,
        reason TEXT NOT NULL,attempt_limit_before INTEGER NOT NULL,attempt_limit_after INTEGER NOT NULL,
        request_extra INTEGER NOT NULL,FOREIGN KEY(account,source) REFERENCES jobs(account,id))''')


def request_limit(db, account, source):
    initialize(db)
    extra = db.execute('SELECT coalesce(sum(request_extra),0) FROM recovery_grants WHERE account=? AND source=?',
                       (account, source)).fetchone()[0]
    return 40 + extra


def grant(db, account, source, reason, request_extra=0):
    if not reason.strip() or len(reason) > 500 or request_extra not in (0, 20):
        raise ValueError('concrete recovery reason and zero or twenty extra requests required')
    initialize(db)
    with db:
        db.execute('BEGIN IMMEDIATE')
        job = db.execute('SELECT * FROM jobs WHERE account=? AND id=?', (account, source)).fetchone()
        if job is None or job['state'] != 'needs_action' or job['max_attempts'] >= 5:
            raise ValueError('only exhausted unresolved jobs qualify; at most two lifetime recovery grants')
        identity = uuid.uuid4().hex
        db.execute('INSERT INTO recovery_grants VALUES (?,?,?,?,?,?,?,?)',
                   (identity, account, source, time.time(), reason, job['max_attempts'], job['max_attempts'] + 1, request_extra))
        db.execute("UPDATE jobs SET state='retry',max_attempts=max_attempts+1,next_at=0,action=? WHERE account=? AND id=?",
                   ('operator recovery: ' + reason, account, source))
    return {'state': 'checkpoint', 'grant': identity, 'source': source}
