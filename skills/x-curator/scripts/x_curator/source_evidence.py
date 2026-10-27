"""Reconstruct selected source content from its original HTTP receipt."""
from .source_authentication import authentic_entry


def selected_source(db, job):
    row = db.execute("""SELECT s.*,c.kind FROM selections s
        JOIN collections c ON c.id=s.run JOIN responses r ON r.run=s.run AND r.number=s.response
        WHERE c.account=? AND s.id=? ORDER BY r.fetched DESC LIMIT 1""", (job["account"], job["id"])).fetchone()
    if row is None:
        raise ValueError('missing or tampered acquisition receipt')
    response = db.execute('SELECT body,sha256 FROM responses WHERE run=? AND number=?',
                          (row['run'],row['response'])).fetchone()
    entry = authentic_entry(dict(row,**dict(response)), job["id"])
    return {"run": row["run"], "response": row["response"], "entry": entry}



def strings(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        value = value.values()
    if isinstance(value, (list, type({}.values()))):
        return [text for item in value for text in strings(item)]
    return []


def nodes(value):
    pending = [value]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            yield value
            pending.extend(reversed(list(value.values())))
        elif isinstance(value, list):
            pending.extend(reversed(value))


def branch(value, *keys):
    for key in keys:
        value = value.get(key) if isinstance(value, dict) else None
    return value if isinstance(value, dict) else {}

def card_bindings(value):
    items = value.items() if isinstance(value, dict) else (
        (item.get('key'), item.get('value')) for item in value if isinstance(item, dict) and item.keys() == {'key', 'value'})
    return ((key, item) for key, item in items if isinstance(item, dict))
