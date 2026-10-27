"""Owned attempts preserve concrete failures and pause an unavailable provider route."""
from .queue import counts
from .leases import fail_owned
from .deadlines import until
from .quick_process import research
from .worker_errors import WorkerFailure
from . import provider_health
from .failure_records import record


def process(db, state, client, job):
    token = job["token"]
    try:
        with until(job["lease_until"] - 2):
            publication = research(db, state, client, token)
        state = db.execute('SELECT state FROM jobs WHERE account=? AND id=?', (job['account'], job['id'])).fetchone()[0]
        return {"source": job["id"], "state": state, "publication": publication}
    except WorkerFailure as exc:
        fail_owned(db, token, str(exc), 3600)
        provider_health.suspend(db, str(exc))
        return {"source": job["id"], "state": "provider_blocked", "action": str(exc)}
    except Exception as exc:
        action = record(db, token, exc)
        outcome = fail_owned(db, token, action, 300)
        return {"source": job["id"], "state": outcome, "action": action}


def summary(db, results, dependency):
    return {"state": "blocked" if dependency else "checkpoint", "completed": sum(r["state"] == "published" for r in results), "attempted": len(results), "results": results, "queue": counts(db), "dependency": dependency}
