"""Extract successful curator drafts from the same authenticated native execution."""
import json

from .model_trace import native
from .receipts import digest
from .wiki_references import canonical


def validations(log):
    items = [event['item'] for event in native(log) if event['type'] == 'item.completed']
    return [item for item in items if (item.get('type'), item.get('server'), item.get('tool'), item.get('status'))
            == ('mcp_tool_call', 'curator', 'validate', 'completed') and not item.get('error')]


def selected(item, sha, inputs):
    try:
        if item['result'].get('isError') or set(item['arguments']) != {'proposal'}:
            return None
        proposal = canonical(item['arguments']['proposal'], inputs)
        response = json.loads(item['result']['content'][0]['text'])
        if (digest(proposal), response.get('valid'), response.get('decision_sha')) == (sha, True, sha):
            return proposal
    except (KeyError, TypeError, ValueError, IndexError, AttributeError):
        pass
    return None
