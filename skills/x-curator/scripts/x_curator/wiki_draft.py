"""Draft feedback reuses the final contract within the original mapping deadline."""
import json
import time

from .deadlines import until
from .receipts import digest
from .wiki_contract import validate
from .wiki_final import feedback
from .wiki_references import canonical


def tools():
    return [dict(name='validate', description='Validate a draft wiki mapping against this run\'s exact catalog and claims. Correct errors before final submission; no new allowance or approval.',
                 annotations={'readOnlyHint': True, 'destructiveHint': False, 'openWorldHint': False},
                 inputSchema={'type': 'object', 'properties': {'proposal': {'type': 'object'}},
                              'required': ['proposal'], 'additionalProperties': False})]


def active(db, identity):
    row = db.execute('SELECT * FROM wiki_runs WHERE id=?', (identity,)).fetchone()
    if row is None or row['state'] != 'running' or row['expires'] <= time.time():
        raise ValueError('wiki mapping attempt expired or superseded')
    if digest(json.loads(row['input'])) != row['input_sha']:
        raise ValueError('wiki input receipt changed')
    return row


def call(db, identity, name, arguments):
    try:
        if name != 'validate' or set(arguments) != {'proposal'}:
            raise ValueError('only validate(proposal) is available')
        row = active(db, identity)
        inputs = json.loads(row['input'])
        proposal = canonical(arguments['proposal'], inputs)
        with until(row['expires']):
            validate(proposal, inputs)
        text, error = feedback(inputs, proposal), False
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        text, error = str(exc)[:500], True
    return {'content': [{'type': 'text', 'text': text}], 'isError': error}
