import unittest

from x_curator.execution_failure import provider_failure
from x_curator.deadlines import DeadlineExceeded
from x_curator.receipts import encoded


class ProviderRateLimitTests(unittest.TestCase):
    def test_only_unfinished_native_exhausted_rate_limit_classifies_deadline(self):
        message = ('Reconnecting... 1/5 (exceeded retry limit, last status: '
                   '429 Too Many Requests, request id: synthetic)')
        event = encoded({'type': 'error', 'message': message}) + b'\n'
        deadline = DeadlineExceeded('execution deadline exhausted')
        self.assertIsNotNone(provider_failure(deadline, event))
        variants = [b'', b'incomplete', encoded({'type': 'error', 'message': None}),
                    event.replace(b'exceeded retry limit', b'temporary interruption'),
                    event.replace(b'429 Too Many Requests', b'400 Bad Request'),
                    event + encoded({'type': 'turn.completed'}),
                    encoded({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': message}})]
        for log in variants:
            with self.subTest(log=log):
                self.assertIsNone(provider_failure(deadline, log))
        self.assertIsNone(provider_failure(ValueError('local defect'), event))
