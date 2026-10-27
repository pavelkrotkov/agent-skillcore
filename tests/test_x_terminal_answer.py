from copy import deepcopy
import unittest

from x_trace_fixtures import SESSION, rollout, trace_fixture
from x_curator.model_events import result
from x_curator.model_trace import pack
from x_curator.worker_prompts import prompt


class TerminalAnswerTests(unittest.TestCase):
    def test_only_terminal_answer_must_match_native_completion(self):
        request, log, rows = trace_fixture()
        for earlier in ('Earlier prose', '{"different":true}'):
            first = deepcopy(rows[-1])
            first['payload']['content'][0]['text'] = earlier
            proof = pack(request, prompt(request), [], log, rollout(rows[:-1] + [first, rows[-1]]))
            self.assertEqual(result(proof), (SESSION, {'synthetic': True}))
        for terminal in ('different prose', '{"different":true}'):
            last = deepcopy(rows[-1])
            last['payload']['content'][0]['text'] = terminal
            with self.assertRaises(ValueError):
                pack(request, prompt(request), [], log, rollout(rows + [last]))
        with self.assertRaisesRegex(ValueError, 'final answer'):
            pack(request, prompt(request), [], log, rollout(rows[:-1]))
