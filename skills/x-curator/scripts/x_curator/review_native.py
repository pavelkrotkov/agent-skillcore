"""Check native readback and immutable proposal binding without inferring human origin."""
import json

from .receipts import digest
from .review_outbox import render, status_render


def message(receipt, chat, identity, kind):
    require_chat(receipt, chat)
    matches = [item for turn in receipt['turns'] for item in turn['items']
               if item['id'] == identity and item['type'] == kind]
    item, = matches
    return item


def require_chat(receipt, chat):
    if receipt['schemaVersion'] != 1 or receipt['thread']['kind'] != 'codex' or receipt['thread']['id'] != chat:
        raise ValueError('receipt is not from the originating Codex chat')


def validate(value, receipt, message_id):
    payload = json.loads(value['payload'])
    if frozen_message(value, payload) != value['message']:
        raise ValueError('frozen approval proposal changed')
    item = message(receipt, value['chat'], message_id, 'agentMessage')
    if item['text'] not in (value['message'], value['message'] + '\n'):
        raise ValueError('the complete approval digest was not observed')


def frozen_message(value, payload):
    for version, renderer in (('chat-review/v2', status_render), ('chat-review/v1', render)):
        identity = digest([version, value['batch'], value['chat'], payload])
        if identity == value['id']:
            return renderer(identity, payload)
    raise ValueError('frozen approval proposal changed')


def require_observed(value):
    if value['observed'] is None:
        raise ValueError('approval request has not been observed in its destination')
    observed = json.loads(value['observed'])
    validate(value, observed['receipt'], observed['message'])
