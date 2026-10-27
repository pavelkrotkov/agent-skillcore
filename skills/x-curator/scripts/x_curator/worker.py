"""Bounded queue passes retain every failure as owned unresolved work."""
from subprocess import SubprocessError

from .batch_queue import claim
from .command_lock import lockfile
from .queue import enqueue
from .worker_process import process, summary
from .provider_health import blocked
from .review_reconcile import flush
from .stage_timings import timed
from .worker_timing import item
from .wiki import run as wiki


@timed('worker.pass', scope='selected')
def work(db, state, client, max_items=1, lease_seconds=240, defer_index=False, unspent_only=False):
    if not 1 <= max_items <= 1000:
        raise ValueError("work pass must be bounded between 1 and 1000 items")
    enqueue(db)
    results = []
    for _ in range(max_items):
        dependency = blocked(db)
        if dependency or (job := claim(db, client.account, lease_seconds, unspent_only)) is None:
            break
        with item(db, job) as timing:
            result = dict(process(db, state, client, job), batch=job['batch'])
            timing['result_state'] = result['state']
        results.append(result)
        if result["state"] == "provider_blocked":
            dependency = {"route": "chatgpt", "action": result["action"]}
            break
    report = dict(summary(db, results, dependency), review_outbox=flush(db, client.account))
    if report['completed']:
        report['index'] = rebuild_index(db, state, defer_index)
    return report


@timed('wiki.lock_and_index', scope='corpus', lock_wait_seconds=0)
def rebuild_index(db, state, defer=False):
    if defer:
        return {'state': 'pending'}
    try:
        with lockfile(state, '.wiki.lock'):
            return wiki(db, state, 0)
    except (OSError, ValueError, RuntimeError, SubprocessError) as exc:
        return {'state': 'blocked', 'action': str(exc)[:300]}
