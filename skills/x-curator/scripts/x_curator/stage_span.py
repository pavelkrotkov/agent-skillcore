"""Durable monotonic nested timing spans."""
from contextlib import contextmanager
from contextvars import ContextVar
import json
import os
import time
import uuid
from .process_liveness import start_mark
from .stage_store import revision, utc, write
from .stage_outcomes import exception_outcome, final_outcome

_ACTIVE = ContextVar('x_curator_stage', default=None)

@contextmanager
def span(db, stage, **fields):
    parent = _ACTIVE.get()
    identity = uuid.uuid4().hex
    run = parent['run'] if parent else identity
    context = dict(parent['context'] if parent else {}, **fields)
    context.setdefault('revision', revision())
    stamp, cpu = time.monotonic(), time.process_time()
    write(db, '''INSERT INTO stage_spans
        (id,run,parent,stage,started,monotonic_start,outcome,context,pid,process_start)
        VALUES (?,?,?,?,?,?,'open',?,?,?)''',
          (identity, run, parent['id'] if parent else None, stage, utc(), stamp,
           json.dumps(context, sort_keys=True), os.getpid(), start_mark(os.getpid())))
    marker = _ACTIVE.set({'id': identity, 'run': run, 'context': context})
    outcome, failure = 'completed', None
    try:
        yield context
    except BaseException as exc:
        failure = type(exc).__name__
        outcome = exception_outcome(exc)
        raise
    finally:
        outcome = final_outcome(context, outcome)
        try:
            write(db, '''UPDATE stage_spans SET finished=?,elapsed=?,process_cpu_seconds=?,outcome=?,failure=?,context=? WHERE id=?''',
                  (utc(), time.monotonic()-stamp, time.process_time()-cpu, outcome, failure,
                   json.dumps(context, sort_keys=True), identity))
        finally:
            _ACTIVE.reset(marker)
