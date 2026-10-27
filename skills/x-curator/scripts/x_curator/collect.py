"""Bounded fresh acquisition; the caller holds the corpus lock."""
from .stage_timings import timed
import time

from .collection_store import current_run, save_page
from .storage import coverage

def request_page(db, client, run):
    """Reserve before HTTP so termination still consumes the request budget."""
    run = dict(run, requests=run["requests"] + 1)
    with db:
        db.execute("INSERT INTO responses VALUES (?,?,?,?,?,?,?)",
                   (run["id"], run["requests"], run["cursor"], -1, time.time(), "", b""))
        db.execute("UPDATE collections SET requests=?,state='collecting',reason='request pending' WHERE id=?",
                   (run["requests"], run["id"]))
    try:
        status, body = client.fetch(run["kind"], run["cursor"])
    except Exception:
        save_page(db, run, 0, b"")
        raise
    return save_page(db, run, status, body)


@timed("intake.collect", scope="selected")
def collect(db, client, kind, limit=500, new=False, delay=1):
    """Caller holds the corpus lock; the limit is cumulative across restarts."""
    if kind not in ("likes", "bookmarks") or limit < 1:
        raise ValueError("invalid collection or request budget")
    run = current_run(db, kind, client.account, new)
    while run["state"] != "timeline_end" and run["requests"] < limit:
        run = request_page(db, client, run)
        if run["state"] == "blocked":
            break
        time.sleep(delay)
    return coverage(db, run["id"])
