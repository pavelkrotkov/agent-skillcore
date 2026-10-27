from unittest.mock import patch

from x_native_search_fixtures import NativeCase
from x_fixtures import Client
from x_curator import execution_failure, provider_health, quick_process
from x_curator.deadlines import DeadlineExceeded
from x_curator.receipts import encoded
from x_curator.worker import work


class ProviderTransportDeadlineTests(NativeCase):
    def test_exhausted_native_reconnects_pause_following_attempts(self):
        reconnects = b''.join(encoded({'type': 'error', 'message':
            'Reconnecting... %d/5 (stream disconnected before completion: '
            'websocket closed by server before response.completed)' % number}) + b'\n'
            for number in range(2, 6))
        retained = reconnects + self.search_log + b'{"partial":'
        error = DeadlineExceeded('execution deadline exhausted')
        error.log = retained
        with patch('x_curator.quick_process.runner', return_value=lambda _: self.fail_execution(error)):
            self.assertIsNone(quick_process.research(self.db, self.root, self.client, self.token))
        execution = self.db.execute('SELECT log,finished FROM executions').fetchone()
        self.assertEqual(tuple(execution), (retained, None))
        self.assertEqual(self.db.execute('SELECT searches FROM quick_checks').fetchone()[0], 4)
        self.assertIsNotNone(provider_health.blocked(self.db))
        before = self.db.execute('SELECT count(*) FROM attempts').fetchone()[0]
        result = work(self.db, self.root, Client([]), 2)
        self.assertEqual((result['state'], result['attempted']), ('blocked', 0))
        self.assertEqual(self.db.execute('SELECT count(*) FROM attempts').fetchone()[0], before)
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)

    def fail_execution(self, error):
        raise error

    def test_only_unfinished_native_exhausted_transport_errors_classify_deadline(self):
        message = ('Reconnecting... 5/5 (stream disconnected before completion: '
                   'websocket closed by server before response.completed)')
        event = encoded({'type': 'error', 'message': message}) + b'\n'
        ordinary = DeadlineExceeded('ordinary execution limit')
        variants = [b'', b'incomplete', b'[]\n', encoded({'type': 'error', 'message': None}),
                    event.replace(b'5/5', b'2/5'), event + encoded({'type': 'turn.completed'}),
                    encoded({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': message}})]
        for log in variants:
            with self.subTest(log=log):
                self.assertIsNone(execution_failure.provider_failure(ordinary, log))
        self.assertIsNone(execution_failure.provider_failure(ValueError('local defect'), event))
        self.assertIsNotNone(execution_failure.provider_failure(ordinary, event))
        ordinary.log = event
        execution_failure.record(self.db, self.root, self.token, ordinary)
        self.assertIsNone(provider_health.blocked(self.db))
