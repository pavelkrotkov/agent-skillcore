import json
from unittest.mock import patch
from x_read_window_fixtures import WindowCase
from x_curator import quick_mcp,quick_sources
from x_curator.deadlines import DeadlineExceeded


class ReadWindowTests(WindowCase):
    def test_late_read_and_controller_search_never_reach_transport_or_reserve_query(self):
        self.at = self.start + 80
        with patch('x_curator.quick_web.fetch') as read, patch('x_curator.quick_search.fetch') as search:
            self.assertTrue(quick_mcp.call(self.db, self.token, 'read', {'source': self.source})['isError'])
            self.assertTrue(quick_mcp.call(self.db, self.token, 'search', {'query': 'late'})['isError'])
            read.assert_not_called()
            search.assert_not_called()
        self.assertEqual(self.db.execute('SELECT searches FROM quick_checks').fetchone()[0], 0)
        self.assertEqual(self.db.execute("SELECT count(*) FROM sqlite_master WHERE name='retrievals'").fetchone()[0], 0)

    def test_read_started_before_cutoff_returns_error_and_keeps_validation_available(self):
        with patch('x_curator.quick_web.fetch', self.fetch):
            read = quick_mcp.call(self.db, self.token, 'read', {'source': self.source})
        cite = json.loads(read['content'][0]['text'])['capture']
        slow = quick_sources.source(self.db, self.token, 'https://example.test/slow')
        self.at = self.start + 79
        def crosses_cutoff(_url):
            self.at = self.start + 80
            raise DeadlineExceeded('synthetic read crosses phase boundary')
        with patch('x_curator.quick_web.fetch', side_effect=crosses_cutoff):
            response = quick_mcp.call(self.db, self.token, 'read', {'source': slow})
        self.assertTrue(response['isError'])
        self.assertIn('read window', response['content'][0]['text'])
        self.at = self.start + 90
        self.assertFalse(quick_mcp.call(self.db, self.token, 'validate', {'decision': self.packet_for(cite)})['isError'])

    def test_original_hard_deadline_still_rejects_validation(self):
        self.at = self.start + 120
        response = quick_mcp.call(self.db, self.token, 'validate', {'decision': {}})
        self.assertTrue(response['isError'])
        self.assertEqual(json.loads(response['content'][-1]['text'])['timing']['remaining_seconds'], 0)
        self.assertEqual(self.db.execute('SELECT deadline-started FROM quick_checks').fetchone()[0], 120)
