"""Exclusive, expiring claims with persistent fairness and bounded retries."""
import time
import uuid

from .queue import recover


def claim(db, account, lease_seconds=900):
    if not 1 <= lease_seconds <= 14400:
        raise ValueError("lease must be between 1 and 14400 seconds")
    with db:
        db.execute("BEGIN IMMEDIATE")
        now = time.time()
        recover(db, account, now)
        db.execute("INSERT OR IGNORE INTO queue_turns(account) VALUES (?)", (account,))
        turn = db.execute("SELECT turn FROM queue_turns WHERE account=?", (account,)).fetchone()[0]
        # Alternate extremes persistently so new arrivals cannot starve the backlog.
        order = "DESC" if turn % 2 else "ASC"
        row = db.execute(f"""SELECT * FROM jobs WHERE account=? AND state IN ('pending','retry')
            AND next_at<=? AND attempts<max_attempts ORDER BY created {order},id {order} LIMIT 1""", (account, now)).fetchone()
        if row is None:
            return None
        return reserve(db, dict(row), now, lease_seconds)


def reserve(db, job, now, seconds):
    token = uuid.uuid4().hex
    identity = (job["account"], job["id"])
    db.execute("""UPDATE jobs SET state='leased',attempts=attempts+1,token=?,lease_until=?
        WHERE account=? AND id=?""", (token, now + seconds, *identity))
    db.execute("INSERT INTO attempts VALUES (?,?,?,?,?,NULL,'leased',NULL)",
               (token, *identity, now, now + seconds))
    db.execute("UPDATE queue_turns SET turn=turn+1 WHERE account=?", (job["account"],))
    return dict(db.execute("SELECT * FROM jobs WHERE account=? AND id=?", identity).fetchone())


def require_lease(db, token, now):
    row = db.execute("SELECT * FROM jobs WHERE token=? AND state='leased' AND lease_until>?", (token, now)).fetchone()
    if row is None:
        raise ValueError("expired or superseded worker lease")
    return dict(row)


def fail(db, token, action, retry_after=60):
    if not action.strip() or not 0 <= retry_after <= 86400:
        raise ValueError("concrete recovery action and bounded retry delay required")
    with db:
        db.execute("BEGIN IMMEDIATE")
        now = time.time()
        job = require_lease(db, token, now)
        record_failure(db, job, token, action, retry_after, now)


def fail_owned(db, token, action, retry_after):
    """Classify even an expired attempt without touching a replacement owner."""
    with db:
        db.execute("BEGIN IMMEDIATE")
        now = time.time()
        row = db.execute("SELECT * FROM jobs WHERE token=? AND state='leased'", (token,)).fetchone()
        if row is not None:
            return record_failure(db, dict(row), token, action, retry_after, now)
        else:
            db.execute("UPDATE attempts SET action=? WHERE token=? AND state='expired'", (action, token))
            return 'superseded'


def record_failure(db, job, token, action, retry_after, now):
    state = "retry" if job["attempts"] < job["max_attempts"] else "needs_action"
    db.execute("UPDATE jobs SET state=?,next_at=?,action=?,token=NULL,lease_until=NULL WHERE token=?",
               (state, now + retry_after, action, token))
    db.execute("UPDATE attempts SET state='failed',finished=?,action=? WHERE token=?", (now, action, token))
    return state
