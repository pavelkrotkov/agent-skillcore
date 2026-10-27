"""Acquire new selections without confusing a known frontier with complete history."""
from .stage_timings import timed
import json
import time

from . import intake_store
from .collect import request_page
from .deadlines import until
from .storage import coverage


@timed("intake.poll", scope="selected")
def poll(db, client, kind):
    run, active = intake_store.begin(db, client, kind)
    if not active:
        return coverage(db, run['id'])
    receipt = db.execute('SELECT * FROM intake_runs WHERE run=?', (run['id'],)).fetchone()
    try:
        with until(receipt['deadline']):
            advance(db, client, run, receipt)
    except Exception as exc:
        intake_store.finish(db, run['id'], type(exc).__name__ + ': ' + str(exc)[:300])
    return coverage(db, run['id'])


def advance(db, client, run, receipt):
    known = set(json.loads(receipt['known']))
    while run['state'] == 'collecting' and run['requests'] < receipt['request_limit']:
        with until(time.time() + 60):
            run = request_page(db, client, run)
        if intake_store.frontier(db, run, known):
            return intake_store.finish(db, run['id'])
        time.sleep(1)
    action = 'head-poll request budget exhausted; inspect retained responses' if run['state'] == 'collecting' else None
    intake_store.finish(db, run['id'], action)
