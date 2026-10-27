"""Revalidate authentic organizer/reviewer events before accepting mappings."""
import json
import time

from .model_events import result
from .model_trace import verify_request
from .receipts import digest
from .wiki_contract import approved
from .wiki_prompts import request
from .wiki_final import output


def accepted_runs(db):
    return [row[0] for row in db.execute("SELECT id FROM wiki_runs WHERE state='accepted' ORDER BY started,id")]


def reviewed(row):
    inputs = json.loads(row['input'])
    if digest(inputs) != row['input_sha']:
        raise ValueError('wiki input receipt changed')
    author, _ = result(row['proposal'])
    packet = output(row['proposal'], inputs)
    reviewer, verdict = result(row['review'])
    if author == reviewer:
        raise ValueError('wiki review requires a separate session')
    verify_request(row["proposal"], request('organize', inputs))
    verify_request(row["review"], request('organize_review', inputs, packet))
    return inputs, packet, verdict


def verified(row):
    inputs, packet, verdict = reviewed(row)
    approved(inputs, packet, verdict)
    return inputs, packet


def accept(db, identity):
    with db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT * FROM wiki_runs WHERE id=?', (identity,)).fetchone()
        inputs, _ = verified(row)
        if row['state'] != 'running' or row['expires'] <= time.time():
            raise ValueError('wiki mapping attempt expired or superseded')
        db.execute("UPDATE wiki_runs SET state='accepted' WHERE id=?", (identity,))
        for source in inputs['sources']:
            db.execute("UPDATE wiki_sources SET run=?,action='verified organization' WHERE publication=?", (identity, source))
