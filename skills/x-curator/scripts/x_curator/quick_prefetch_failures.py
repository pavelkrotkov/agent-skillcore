"""Controller prefetch errors remain operator work even without a model read call."""
import json
from .quick_window import READ_CLOSED

CUTOFF = ['Linked source unavailable during bounded prefetch: ' + READ_CLOSED]


def failures(db, token):
    result = []
    for row in db.execute('SELECT payload FROM captures WHERE token=? ORDER BY id', (token,)):
        try:
            result.append(classify(json.loads(row['payload'])))
        except (ValueError, TypeError):
            result.append('prefetch: incomplete or malformed acquisition receipt')
    return list(filter(None, result))


def classify(value):
    if not isinstance(value, dict):
        raise ValueError('invalid capture shape')
    if value.get('kind') != 'unavailable' or value.get('quick_scope') is not True:
        return None
    if value.get('limitations') == CUTOFF:
        return None
    message = ' '.join(map(str, value.get('limitations') or ['Linked source unavailable']))
    return 'prefetch: ' + message
