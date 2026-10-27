"""One private stage-timing mechanism for existing pipeline entry points."""
from functools import wraps
from contextlib import nullcontext
from .stage_span import span
from .stage_store import initialize
from .stage_report import report

def skip(db, stage, reason):
    with span(db, stage) as receipt:
        receipt.update(skipped=True, skip_reason=reason)


def timed(name, *, token_arg=False, **context):
    def decorate(fn):
        @wraps(fn)
        def invoke(db, *args, **kwargs):
            with span(db, name, **(dict(context, attempt=args[0]) if token_arg else context)) as receipt:
                result = fn(db, *args, **kwargs)
                receipt['skipped'] = ((isinstance(result, dict) and result.get('state') in ('empty', 'idle', 'pending'))
                                      or (result is None and name in ('queue.select', 'source.linked_read')))
                if isinstance(result, dict):
                    receipt['result_state'] = result.get('state')
                return result
        return invoke
    return decorate


def command(db, name):
    if name in ('policy-report', 'report', 'batches', 'status', 'queue'):
        return nullcontext()
    return span(db, 'command.' + name, scope='selected')
