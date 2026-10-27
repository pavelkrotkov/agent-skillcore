import json
import io
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock, patch
import uuid

from x_publication_fixtures import PublicationCase, events
from x_fixtures import Client
from x_trace_fixtures import image_content
from x_curator import quick_mcp, quick_store, public_http
from x_curator.model_trace import pack
from x_curator.receipts import encoded
from x_curator.worker_prompts import prompt


class QuickCase(PublicationCase):
    search_mode = 'controller'

    def setUp(self):
        super().setUp()
        mode = patch('x_curator.quick_process.SEARCH_MODE', self.search_mode)
        mode.start()
        self.addCleanup(mode.stop)
        self.calls = []
        self.client = Client([])
        self.decision = None
        self.modify = lambda value: value

    @contextmanager
    def transport(self, body):
        response = SimpleNamespace(status=200, read=Mock(wraps=io.BytesIO(body).read),
                                   getheaders=lambda: [('content-type', 'text/html')])
        connection = Mock()
        connection.getresponse.return_value = response
        parts = public_http.public_url('https://example.test/large')
        with patch('x_curator.public_http.destination', return_value=(parts, 443, '93.184.216.34')), \
                patch('x_curator.public_http.http.client.HTTPSConnection', return_value=connection):
            yield response
        connection.close.assert_called_once()

    def fetch(self, url):
        self.calls.append(url)
        if 'format=rss' in url:
            body = b'<rss><channel><item><title>Official release</title><link>https://example.test/release</link></item></channel></rss>'
            return 200, 'text/xml', body, None
        return 200, 'text/plain', b'The tool was released in 2025. This is the original release announcement.', None

    def checker(self, request):
        token = self.token
        found = quick_mcp.call(self.db, token, 'search', {'query': 'synthetic official release'})
        source = json.loads(found['content'][0]['text'])[0]['source']
        read = quick_mcp.call(self.db, token, 'read', {'source': source})
        cite = json.loads(read['content'][0]['text'])['capture']
        decision = self.modify(self.packet_for(cite))
        self.decision = decision
        return native(request, decision, [found, read])

    def packet_for(self, cite):
        quotation = {'capture': cite, 'quote': 'The tool was released in 2025.'}
        claim = dict(self.packet['claims'][0], kind='fact', text=quotation['quote'], citations=[quotation],
                     checks=['f1'], independently_useful=True)
        check = dict(id='f1', text=claim['text'], status='supported', sources=[dict(quotation, primary=True,
                     credible=True, origin='Original project', reason='Original release announcement supports the year.')])
        packet = dict(self.packet, claims=[claim])
        return dict(outcome='supported', reason='Original release confirms the claim.', central=['f1'], checks=[check], packet=packet)


def native(request, decision, responses, searches=b'', images=None):
    session = str(uuid.uuid4())
    messages = [{'type': 'session_meta', 'payload': {'id': session}},
                {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user',
                 'content': [{'type': 'input_text', 'text': prompt(request)}]}}]
    messages[1]['payload']['content'].extend(image_content(images))
    messages.extend({'type': 'response_item', 'payload': {'type': 'function_call_output',
                     'output': json.dumps(value)}} for value in responses)
    messages.append({'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant',
                     'phase': 'final_answer', 'content': [{'type': 'output_text', 'text': json.dumps(decision)}]}})
    return pack(request, prompt(request), ['synthetic'], searches + events(decision, session), b'\n'.join(encoded(m) for m in messages))
