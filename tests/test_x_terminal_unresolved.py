from copy import deepcopy

from x_publication_fixtures import PublicationCase, events
from x_trace_fixtures import SESSION, rollout, trace_fixture
from x_curator.executions import execute, verified_execution
from x_curator.model_trace import pack
from x_curator.packets import validate
from x_curator.evidence import bundle
from x_curator.receipts import encoded
from x_curator.worker_prompts import prompt


class TerminalUnresolvedTests(PublicationCase):
    def test_terminal_unresolved_is_recorded_but_cannot_publish(self):
        terminal = {'unresolved': 'Original evidence is insufficient'}
        def call(request):
            _, _, rows = trace_fixture()
            rows[1]['payload']['content'] = [{'type': 'input_text', 'text': prompt(request)}]
            rows[-1]['payload']['content'][0]['text'] = encoded(self.packet).decode()
            last = deepcopy(rows[-1])
            last['payload']['content'][0]['text'] = encoded(terminal).decode()
            return pack(request, prompt(request), [], events(terminal, SESSION), rollout(rows + [last]))
        identity = execute(self.db, self.token, 'research', 'synthetic', call)
        _, _, packet = verified_execution(self.db, identity, 'research', self.token)
        self.assertEqual(packet, terminal)
        with self.assertRaises((KeyError, ValueError)):
            validate(packet, bundle(self.db, self.token))
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM publications').fetchone()[0], 0)
