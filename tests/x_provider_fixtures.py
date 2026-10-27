from datetime import datetime, timezone
import json

from x_trace_fixtures import proof
from x_curator.codex_profile import command
from x_curator.receipts import encoded


def recovery_proof(request, started):
    receipt = json.loads(proof(request, {'unresolved': 'Missing primary evidence'}))
    receipt['profile'] = command('codex', request['role'] == 'discover') + ['-']
    rows = [json.loads(line) for line in receipt['rollout'].splitlines()]
    rows[0]['payload']['timestamp'] = datetime.fromtimestamp(started, timezone.utc).isoformat()
    receipt['rollout'] = '\n'.join(encoded(row).decode() for row in rows)
    return encoded(receipt)
