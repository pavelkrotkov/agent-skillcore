"""Read the immutable organizer input without file access or new retrieval."""
import json

from .wiki_draft import active
from .wiki_notes import request
from .wiki_prompt_payload import payload


def tool():
    return dict(name='context', description='Read the exact bound organizer request as structured data. Use its supplied publication references and catalog directly when drafting; no file tools are needed. For corrections, edit bundle.wiki_inputs.feedback.proposal and set its input_sha to this response input_sha, then validate. Prior feedback is unapproved; no new facts or allowance.',
                annotations={'readOnlyHint': True, 'destructiveHint': False, 'openWorldHint': False},
                inputSchema={'type': 'object', 'properties': {}, 'additionalProperties': False})


def call(db, identity, arguments):
    try:
        if arguments != {}:
            raise ValueError('context takes no arguments')
        value = payload(request('organize', json.loads(active(db, identity)['input'])))
        return {'content': [{'type': 'text', 'text': json.dumps(value)}],
                'structuredContent': value, 'isError': False}
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        return {'content': [{'type': 'text', 'text': str(exc)[:500]}], 'isError': True}
