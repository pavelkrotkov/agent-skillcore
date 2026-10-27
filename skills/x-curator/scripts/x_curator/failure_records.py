"""Keep private exception traces and SQLite extended codes beyond a terse queue action."""
import traceback
import uuid

from .blobs import state_root
from .publication_files import write_verified
from .receipts import encoded


def record(db, token, exc):
    detail = dict(token=token, error=type(exc).__name__, message=str(exc), traceback=traceback.format_exc(),
                  sqlite_errorcode=getattr(exc, 'sqlite_errorcode', None), sqlite_errorname=getattr(exc, 'sqlite_errorname', None))
    action = type(exc).__name__ + ': ' + str(exc)[:300]
    if detail['sqlite_errorname']:
        action += ' [' + detail['sqlite_errorname'] + ']'
    try:
        write_verified(state_root(db), 'failures/' + uuid.uuid4().hex + '.json', encoded(detail))
    except (OSError, ValueError) as failure:
        action += ' (diagnostic retention failed: ' + type(failure).__name__ + ')'
    return action
