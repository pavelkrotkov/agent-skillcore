"""Acquisition failures need operator triage before proposing more research."""
import json
from .quick_window import READ_CLOSED
from .quick_prefetch_failures import failures as prefetch_failures

MEDIA_REFUSAL = 'quick checks read HTML/plain text only; media needs explicit research approval'


def retrieval(db, token):
    rows = db.execute("SELECT name,output FROM quick_tools WHERE token=? AND name IN ('search','read') ORDER BY created,id", (token,))
    return list(dict.fromkeys(filter(None, [failure(row) for row in rows] + prefetch_failures(db, token))))


def failure(row):
    try:
        output = json.loads(row['output'])
        content, *_ = output['content']
        message = content['text']
        if type(output['isError']) is not bool or not isinstance(message, str):
            raise ValueError('invalid tool receipt shape')
    except (ValueError, TypeError, KeyError):
        return row['name'] + ': incomplete or malformed acquisition receipt'
    if not output['isError'] or message in (MEDIA_REFUSAL, READ_CLOSED):
        return None
    return row['name'] + ': ' + message


def for_source(db, account, source):
    row = db.execute('''SELECT token FROM quick_checks WHERE account=? AND source=?
        ORDER BY started DESC,id DESC LIMIT 1''', (account, source)).fetchone()
    return retrieval(db, row['token']) if row else []
