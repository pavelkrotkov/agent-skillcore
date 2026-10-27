"""Commit acquisition evidence and its pagination checkpoint together."""
import json
import time
import uuid

from .storage import sha256
from .timeline import parse

def current_run(db, kind, account, new=False):
    row = db.execute(
        "SELECT * FROM collections WHERE kind=? AND account=? ORDER BY started DESC LIMIT 1",
        (kind, account),
    ).fetchone()
    if row is not None and not new:
        return dict(row)
    run = uuid.uuid4().hex
    with db:
        db.execute("INSERT INTO collections(id,kind,account,started,state) VALUES (?,?,?,?,?)",
                   (run, kind, account, time.time(), "collecting"))
    return dict(db.execute("SELECT * FROM collections WHERE id=?", (run,)).fetchone())


def outcome(db, run, status, body):
    if status != 200:
        return [], run["cursor"], "blocked", "http_" + str(status)
    try:
        items, cursor, problem = parse(body, run["kind"])
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        return [], run["cursor"], "blocked", "malformed timeline: " + type(exc).__name__
    if problem:
        return items, run["cursor"], "blocked", problem
    # Repeated cursors can occur on truncated timelines, so they cannot prove exhaustion.
    prior = db.execute("SELECT 1 FROM responses WHERE run=? AND cursor=?", (run["id"], cursor)).fetchone()
    if prior:
        return items, run["cursor"], "blocked", "pagination cursor loop"
    return items, cursor, "timeline_end" if cursor is None else "collecting", None


def save_page(db, run, status, body):
    items, cursor, state, reason = outcome(db, run, status, body)
    number = run["requests"]
    with db:
        db.execute("UPDATE responses SET status=?,fetched=?,sha256=?,body=? WHERE run=? AND number=? AND status=-1",
                   (status, time.time(), sha256(body), body, run["id"], number))
        for source_id, availability, entry in items:
            db.execute("""INSERT INTO selections VALUES (?,?,?,?,?)
                       ON CONFLICT(run,id) DO UPDATE SET response=excluded.response,
                       entry=excluded.entry, availability=excluded.availability
                       WHERE selections.availability='malformed' AND excluded.availability!='malformed'""",
                       (run["id"], source_id, number, json.dumps(entry, sort_keys=True), availability))
        db.execute("UPDATE collections SET cursor=?,state=?,requests=?,reason=? WHERE id=?",
                   (cursor, state, number, reason, run["id"]))
    return dict(db.execute("SELECT * FROM collections WHERE id=?", (run["id"],)).fetchone())
