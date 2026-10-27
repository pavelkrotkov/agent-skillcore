"""Correlate private worker attempts with queue age and stable cohorts."""
from contextlib import contextmanager
import time

from .storage import sha256
from .stage_timings import span


@contextmanager
def item(db, job):
    with span(db, 'worker.item', scope='selected', cohort=job['batch'],
              item=sha256(job['id'].encode()), attempt=job['token'],
              attempt_number=job['attempts'],
              queue_wait_seconds=max(0, time.time()-max(job['created'], job['next_at'])),
              concurrency=db.execute("SELECT count(*) FROM attempts WHERE state='leased'").fetchone()[0]) as timing:
        yield timing
