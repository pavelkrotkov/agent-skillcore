"""Controller time feedback supplements, never replaces, exact evidence text."""
import time
from .receipts import encoded


def budget(check):
    now = time.time()
    return dict(remaining_seconds=max(0, int(check['deadline'] - now)),
                validation_target_seconds_remaining=max(0, int(min(check['deadline'], check['started'] + 70) - now)),
                read_window_seconds_remaining=max(0, int(min(check['deadline'], check['started'] + 80) - now)))


def append(db, token, output):
    row = db.execute('SELECT started,deadline FROM quick_checks WHERE token=? AND outcome IS NULL', (token,)).fetchone()
    if row is not None:
        output['content'].append({'type': 'text', 'text': encoded({'timing': budget(row)}).decode()})
