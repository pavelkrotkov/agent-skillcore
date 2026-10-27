import json
from unittest import TestCase

from x_trace_fixtures import proof
from x_curator.receipts import digest, encoded
from x_curator import wiki_catalog
from x_curator.wiki_prompts import request
from x_curator.wiki_final import feedback


def compact(request, proposal, response=None):
    response = response or dict(content=[dict(type='text', text=feedback(request['bundle']['wiki_inputs'], proposal))])
    final = json.loads(response['content'][0]['text'])['final_answer']
    value = json.loads(proof(request, final))
    events = [json.loads(line) for line in value['events'].splitlines()]
    item = dict(type='mcp_tool_call', server='curator', tool='validate', status='completed',
                arguments=dict(proposal=proposal), result=response, error=None)
    events.insert(1, dict(type='item.completed', item=item))
    value['events'] = '\n'.join(encoded(event).decode() for event in events)
    return encoded(value)


class WikiFinalCase(TestCase):
    def setUp(self):
        self.inputs = wiki_catalog.prepare({'p': dict(packet=dict(claims=[dict(id='c1', text='Synthetic opinion.')]))}, {}, ['p'])
        refs = [dict(publication='p', claim='c1')]
        self.proposal = dict(input_sha=digest(self.inputs), pages=[dict(kind='concept', title='Synthetic opinion',
            description='Attributed synthetic opinion. ' * 500, claims=refs, related=[],
            synthesis=[dict(text='A synthetic opinion illustrates retained attribution.', claims=refs)])])
        self.request = request('organize', self.inputs)
