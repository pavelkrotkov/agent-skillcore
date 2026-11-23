"""Keep useful cycle diagnostics without repeating full corpus snapshots."""
import json
import time
from .retention_files import DAY, table
from .receipts import encoded
from . import cycle_diagnostics


def summary(result):
    value = {key: result[key] for key in ('state', 'cycle', 'action') if key in result}
    if dependency := result.get('work', {}).get('dependency'):
        value['work'] = dict(dependency=dependency)
    if result.get('wiki'):
        value['wiki'] = cycle_diagnostics.wiki(result['wiki'])
    if result.get('report'):
        value['report'] = cycle_diagnostics.report(result['report'])
    return value


def run(db, apply=False):
    if not table(db, 'cycles'):
        return dict(records=0, bytes=0)
    changed, saved = [], 0
    for row in db.execute('SELECT id,result FROM cycles WHERE finished<? AND result IS NOT NULL', (time.time() - 7 * DAY,)):
        body = encoded(summary(json.loads(row[1]))).decode()
        if len(body) < len(row[1]):
            changed.append((body, row[0]))
            saved += len(row[1].encode()) - len(body.encode())
    if apply:
        with db:
            db.executemany('UPDATE cycles SET result=? WHERE id=?', changed)
    return dict(records=len(changed), bytes=saved, note='SQLite reuses freed pages; this does not shrink the database file')
