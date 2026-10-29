"""Finished superseded receipts cannot approve work or recover a different publication."""
import time
import json

from . import compact_seal
from .receipts import digest
from .storage import sha256


def candidates(db):
    return db.execute('''SELECT a.* FROM attempts a JOIN jobs j
        ON j.account=a.account AND j.id=a.id
        WHERE j.state='published' AND a.state IN ('failed','expired','interrupted','excluded','published')
        AND a.expires<?
        AND EXISTS (SELECT 1 FROM publications p WHERE p.account=a.account
            AND p.source=a.id AND p.state='published')
        AND NOT EXISTS (SELECT 1 FROM publications p JOIN executions e
            ON e.id=p.proposal OR e.id=p.review WHERE e.token=a.token)
        AND EXISTS (SELECT 1 FROM executions e WHERE e.token=a.token
            AND e.finished IS NOT NULL AND e.log IS NOT NULL)
        ORDER BY a.token''', (time.time(),)).fetchall()


def require_approval(db, root, row):
    identities = db.execute('''SELECT id FROM publications WHERE account=? AND source=?
        AND state='published' ''', (row['account'], row['id']))
    if not any(compact_seal.read(db, root, ('publication', p[0])) for p in identities):
        raise ValueError('Superseded history requires a retained publication approval')


def rows(db, token):
    return db.execute('''SELECT * FROM executions WHERE token=? AND finished IS NOT NULL
        ORDER BY started,id''', (token,)).fetchall()


def intact(row):
    try:
        return (sha256(row['log']) == row['log_sha'] and
                digest(json.loads(row['input'])) == row['input_sha'] and
                digest(json.loads(row['output'])) == row['output_sha'])
    except (ValueError, TypeError):
        return False


def eligible(db):
    for attempt in candidates(db):
        receipts = rows(db, attempt['token'])
        if all(intact(row) for row in receipts):
            yield attempt, receipts
