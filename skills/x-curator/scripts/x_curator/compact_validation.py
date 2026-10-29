"""Replay current source bytes and contracts; model approval is a signed historical fact."""
import json

from .evidence import current_bundle
from .publication_currentness import validate as validate_revision
from .source_evidence import selected_source
from .source_render import render
from .read_set import read_file
from .storage import sha256


def publication(db, root, identity, value):
    packet, retained = value
    row = db.execute('SELECT * FROM publications WHERE id=?', (identity,)).fetchone()
    token = db.execute('SELECT token FROM executions WHERE id=?', (row['proposal'],)).fetchone()[0]
    job = db.execute('SELECT * FROM jobs WHERE account=? AND id=?', (row['account'], row['source'])).fetchone()
    evidence = current_bundle(db, job, token)
    if evidence != retained:
        raise ValueError('source evidence differs from compact approval')
    validate_revision(db, token, evidence['captures'], selected_source(db, job), packet)
    expected = render(packet, evidence).encode()
    if row['body'] != expected or row['sha'] != sha256(expected) or read_file(db, root, row['path']) != expected:
        raise ValueError('publication differs from compact approval')


def mapping(db, root, identity, value):
    from .wiki_contract import validate
    row = db.execute('SELECT input,input_sha FROM wiki_runs WHERE id=?', (identity,)).fetchone()
    from .receipts import digest
    inputs = json.loads(row['input'])
    if digest(inputs) != row['input_sha']:
        raise ValueError('wiki input receipt changed')
    validate(value, inputs)
