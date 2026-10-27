"""Detailed public exchanges retain both sides under the ordinary lifetime budget."""
import json

from . import blobs, public_http
from .receipts import encoded
from .retrieval_store import finish, reserved


def request(db, token, url, method='GET', body=None, headers=None, max_bytes=8388608):
    db.execute('''CREATE TABLE IF NOT EXISTS http_details (
        id TEXT PRIMARY KEY REFERENCES retrievals(id), request_sha TEXT NOT NULL, response_sha TEXT)''')
    sent = dict(url=url, method=method, body_sha=blobs.put(db, body or b''), headers=headers or {},
                effective_headers=public_http.request_headers(headers))
    with reserved(db, token, url) as identity:
        with db:
            db.execute('INSERT INTO http_details VALUES (?,?,NULL)', (identity, blobs.put(db, encoded(sent))))
        status, received, data = public_http.exchange(url, method, body, headers, max_bytes)
        response = dict(status=status, headers=received, body_sha=finish(db, identity, status, data))
        with db:
            db.execute('UPDATE http_details SET response_sha=? WHERE id=?', (blobs.put(db, encoded(response)), identity))
    return identity, response


def read(db, identity, job):
    row = db.execute('''SELECT r.*,d.request_sha,d.response_sha FROM retrievals r
        JOIN http_details d ON d.id=r.id WHERE r.id=?''', (identity,)).fetchone()
    if row is None or (row['account'], row['source']) != (job['account'], job['id']):
        raise ValueError('HTTP receipt does not belong to source')
    if row['error'] or not row['finished'] or not row['response_sha']:
        raise ValueError('incomplete HTTP receipt')
    sent = json.loads(blobs.read(db, row['request_sha']))
    response = json.loads(blobs.read(db, row['response_sha']))
    if (sent['url'], response['status'], response['body_sha']) != (row['url'], row['status'], row['body_sha']):
        raise ValueError('HTTP receipt differs from reserved request')
    blobs.read(db, sent['body_sha'])
    blobs.read(db, response['body_sha'])
    return sent, response
