"""Per-source transition inventory and preservation rules."""
import json

from .receipts import digest
from .publication_audit import inventory

POLICY = 'bounded-default/v1'


def item(db, root, captured, proof_db):
    account, source = captured['account'], captured['id']
    row = db.execute('SELECT * FROM jobs WHERE account=? AND id=?', (account, source)).fetchone()
    job = dict(row) if row else dict(state='missing', attempts=0, max_attempts=3)
    pages = inventory(db, root, account, source, proof_db)
    checks = [dict(r) for r in db.execute('SELECT * FROM quick_checks WHERE account=? AND source=? ORDER BY id', (account, source))]
    migrated = db.execute('SELECT 1 FROM policy_transitions WHERE policy=? AND account=? AND source=?', (POLICY, account, source)).fetchone()
    requests = db.execute('SELECT count(*) FROM retrievals WHERE account=? AND source=?', (account, source)).fetchone()[0]
    extra = db.execute('SELECT coalesce(sum(request_extra),0) FROM recovery_grants WHERE account=? AND source=?', (account, source)).fetchone()[0]
    value = dict(account=account, source=source, created=captured['created'],
                 revision=digest(sorted(json.loads(captured['revisions']))), job=job, publications=pages,
                 quick_checks=checks, requests=requests, request_limit=40+extra, transitioned=bool(migrated))
    target = disposition(value)
    grant = None
    if target == 'quick_check':
        extra = 20 if value['request_limit'] - requests < 20 else 0
        grant = dict(id=digest([POLICY, account, source]), request_extra=extra,
                     remaining_requests=value['request_limit'] + extra - requests,
                     attempt_limit=max(job['max_attempts'], job['attempts'] + 1))
    return dict(value, disposition=target, grant=grant)


def disposition(value):
    if blocked(value):
        return 'blocked'
    if value['job']['state'] == 'published':
        return 'valid_publication'
    governed = [value['job']['state'] in ('excluded', 'awaiting_review'), value['quick_checks'], value['transitioned']]
    return 'preserve_new_policy' if any(governed) else 'quick_check'


def blocked(value):
    return any([value['job']['state'] == 'leased', value['requests'] > value['request_limit'],
                any(p['error'] for p in value['publications']),
                (value['job']['state'] == 'published') != bool(value['publications'])])
