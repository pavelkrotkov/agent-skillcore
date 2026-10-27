import io
import json
import time
from unittest.mock import patch

from x_quick_fixtures import QuickCase
from x_curator import quick_mcp, quick_store
from x_curator.leases import claim
from x_curator.worker import process
from x_fixtures import Client


class QuickRuntimeTests(QuickCase):
    def test_default_worker_publishes_once_without_legacy_research(self):
        job = dict(self.db.execute('SELECT * FROM jobs').fetchone())
        with patch('x_curator.quick_web.fetch', self.fetch), patch('x_curator.quick_search.fetch', self.fetch), patch('x_curator.quick_process.runner', return_value=self.checker), patch('x_curator.research.research', side_effect=AssertionError('deep work forbidden')):
            self.assertEqual(process(self.db, self.root, self.client, job)['state'], 'published')
            self.assertIsNone(claim(self.db, Client.account))
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 1)
        self.assertEqual(self.db.execute('SELECT outcome FROM quick_checks').fetchone()[0], 'supported')

    def test_stdio_initialization_tools_and_unknown_tool_response(self):
        quick_store.start(self.db, self.token, time.time())
        messages = [dict(jsonrpc='2.0', id=1, method='initialize'), dict(jsonrpc='2.0', method='notifications/initialized'),
                    dict(jsonrpc='2.0', id=2, method='tools/list'),
                    dict(jsonrpc='2.0', id=3, method='tools/call', params={'name': 'shell', 'arguments': {}})]
        output = io.StringIO()
        quick_mcp.serve(self.db, self.token, io.StringIO('malformed\n42\n' + '\n'.join(json.dumps(m) for m in messages)), output)
        replies = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(replies.pop(0)['error']['code'], -32700)
        self.assertEqual(replies.pop(0)['error']['code'], -32600)
        self.assertEqual([r['id'] for r in replies], [1, 2, 3])
        self.assertEqual({t['name'] for t in replies[1]['result']['tools']}, {'search', 'read', 'validate'})
        self.assertTrue(replies[2]['result']['isError'])

    def test_prepared_quick_recovery_completes_the_same_outcome_atomically(self):
        from x_curator.publication_files import write_verified
        from x_curator.publication_recovery import complete
        import test_x_quick_flow
        def interrupted(*args):
            write_verified(*args)
            raise OSError('synthetic interruption after file readback')
        with patch('x_curator.publication.write_verified', side_effect=interrupted):
            self.assertIsNone(test_x_quick_flow.QuickFlowTests.run_check(self))
        identity = self.db.execute('SELECT id FROM publications').fetchone()[0]
        complete(self.db, self.root, identity, 'Resume the verified prepared quick publication')
        self.assertEqual(self.db.execute('SELECT outcome FROM quick_checks').fetchone()[0], 'supported')
        self.assertTrue(complete(self.db, self.root, identity, 'Repeated recovery')['already_completed'])
