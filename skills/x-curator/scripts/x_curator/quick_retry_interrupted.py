"""Expired quick leases retain their spent receipt before bounded redispatch."""
from .quick_retry import delay


def recover(db, account, now):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='quick_retry_failures'").fetchone():
        return
    rows = db.execute('''SELECT j.*,q.id check_id FROM jobs j LEFT JOIN quick_checks q ON q.token=j.token
        WHERE j.account=? AND j.state='leased' AND j.lease_until<=? AND q.outcome IS NULL''', (account, now)).fetchall()
    for row in rows:
        reason = 'Technical quick check interrupted; original attempt and deadline remain spent.'
        db.execute('INSERT OR IGNORE INTO quick_retry_failures VALUES (?,?,?,?)', (row['token'], row['check_id'], now, reason))
        db.execute("UPDATE quick_checks SET outcome='inconclusive',reason=? WHERE id=? AND outcome IS NULL", (reason, row['check_id']))
        db.execute('UPDATE jobs SET next_at=? WHERE token=?', (now + delay(row['attempts']), row['token']))
