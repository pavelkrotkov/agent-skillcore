"""Keep useful cycle diagnostics without repeating full corpus snapshots."""
import json
import time
from .retention_files import DAY, table
from .receipts import encoded


def summary(result):
    value = {key: result[key] for key in ('state', 'cycle', 'action') if key in result}
    if dependency := result.get('work', {}).get('dependency'):
        value['work'] = dict(dependency=dependency)
    report = result.get('report', {})
    if report:
        value['report'] = {key: report[key] for key in ('selected_sources', 'counts') if key in report}
        manifest = report.get('wiki', {}).get('manifest', {})
        value['report']['generation'] = manifest.get('generation')
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
