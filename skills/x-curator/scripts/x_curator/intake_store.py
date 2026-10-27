"""Fresh head polls have persistent request and elapsed-time budgets."""
import json
import time

from .collection_store import current_run


def initialize(db):
    db.execute('''CREATE TABLE IF NOT EXISTS intake_runs (
        run TEXT PRIMARY KEY REFERENCES collections(id),known TEXT NOT NULL,
        request_limit INTEGER NOT NULL,deadline REAL NOT NULL,finished REAL)''')


def begin(db, client, kind):
    initialize(db)
    row = db.execute('''SELECT c.*,i.finished FROM collections c JOIN intake_runs i ON i.run=c.id
        WHERE c.account=? AND c.kind=? ORDER BY c.started DESC LIMIT 1''', (client.account, kind)).fetchone()
    if row and (row['finished'] is None or time.time() - row['started'] < 1800):
        return dict(row), row['finished'] is None
    known = [row[0] for row in db.execute('''SELECT DISTINCT s.id FROM selections s JOIN collections c ON c.id=s.run
        WHERE c.account=? AND c.kind=?''', (client.account, kind))]
    run = current_run(db, kind, client.account, True)
    with db:
        db.execute('INSERT INTO intake_runs VALUES (?,?,?,?,NULL)',
                   (run['id'], json.dumps(known), 100, run['started'] + 300))
    return run, True


def finish(db, identity, action=None):
    with db:
        if action:
            db.execute("UPDATE collections SET state='blocked',reason=? WHERE id=?", (action, identity))
        db.execute('UPDATE intake_runs SET finished=? WHERE run=?', (time.time(), identity))

def frontier(db, run, known):
    ids = {row[0] for row in db.execute('SELECT id FROM selections WHERE run=? AND response=?', (run['id'], run['requests']))}
    if ids and ids <= known and run['state'] != 'blocked':
        with db:
            db.execute("UPDATE collections SET state='caught_up',reason='previously observed frontier' WHERE id=?", (run['id'],))
        return True
    return False
