"""Freeze complete original attempts and executor bytes, including interrupted work."""
from x_curator.receipts import digest
from x_curator.storage import sha256


def rows(db, query, parameters):
    return [dict(sha=digest({key: {'bytes_sha256': sha256(value)} if isinstance(value, bytes) else value
                            for key, value in dict(row).items()}))
            for row in db.execute(query, parameters)]


def snapshot(db, item):
    check = db.execute('SELECT * FROM quick_checks WHERE id=?', (item['original'],)).fetchone()
    if check is None:
        raise ValueError('missing original quick check')
    tools = [dict(id=row['id'], sha=digest(dict(row))) for row in db.execute(
        'SELECT * FROM quick_tools WHERE token=? ORDER BY created,id', (check['token'],))]
    executions = rows(db, 'SELECT * FROM executions WHERE token=? ORDER BY started,id', (check['token'],))
    attempts = rows(db, 'SELECT * FROM attempts WHERE account=? AND id=? ORDER BY started,token',
                    (check['account'], check['source']))
    return dict(original_sha=digest(dict(check)), tools=tools, executions=executions, prior_attempts=attempts)
