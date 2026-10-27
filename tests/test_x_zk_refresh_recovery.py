from unittest.mock import patch
import json
import time

from x_zk_refresh_fixtures import RefreshRecoveryCase
from x_curator import wiki_refresh, wiki_store
from x_curator.cli import arguments
from x_curator.wiki_mapping import map_sources
from x_curator.wiki_refresh_recovery import grant


class ZKRefreshRecoveryTests(RefreshRecoveryCase):
    def test_cli_grant_allows_only_fourth_and_preserves_history(self):
        self.exhaust()
        history = list(self.db.execute('SELECT * FROM wiki_runs ORDER BY id'))
        counters = list(self.db.execute('SELECT publication,attempts FROM wiki_sources ORDER BY publication'))
        sources = list(self.db.execute('SELECT * FROM executions ORDER BY id'))
        argv = ['x', '--state', str(self.root), 'zk-refresh', '--reason', 'Synthetic explicit approval', '--grant-extra-attempt']
        for source in reversed(self.sources):
            argv.extend(['--publication', source])
        with patch('sys.argv', argv):
            args = arguments()
        with patch('x_curator.wiki.initial', side_effect=AssertionError('grant loaded history')), \
                patch('x_curator.wiki_mapping.runner', side_effect=AssertionError('grant invoked model')):
            result = wiki_refresh.command(self.db, args)
        self.assertEqual((result['refresh'], result['attempt_limit']), (self.inputs['refresh'], 4))
        row = self.db.execute('SELECT * FROM wiki_refresh_grants').fetchone()
        self.assertEqual(json.loads(row['publications']), sorted(self.sources))
        self.assertEqual((row['limit_before'], row['limit_after'], row['reason']), (3, 4, args.reason))
        with self.assertRaises(ValueError):
            grant(self.db, list(self.sources), 'Repeated approval text')
        with patch('x_curator.wiki_mapping.runner', return_value=self.feedback_response):
            identity = map_sources(self.db, self.inputs)
        self.assertEqual(self.db.execute('SELECT state FROM wiki_runs WHERE id=?', (identity,)).fetchone()[0], 'accepted')
        with self.assertRaisesRegex(ValueError, 'budget exhausted'):
            wiki_store.reserve(self.db, dict(self.inputs, catalog_sha='changed', refresh_reason='new wording'))
        self.assertEqual([self.db.execute('SELECT * FROM wiki_runs WHERE id=?', (r['id'],)).fetchone() for r in history], history)
        self.assertEqual(list(self.db.execute('SELECT publication,attempts FROM wiki_sources ORDER BY publication')), counters)
        self.assertEqual(list(self.db.execute('SELECT * FROM executions ORDER BY id')), sources)

    def test_invalid_and_unspent_selections_do_not_create_grants(self):
        for selected, reason in [(list(self.sources), ''), ([], 'Approval'),
                                 ([self.publication] * 2, 'Approval'),
                                 ([str(n) for n in range(11)], 'Approval'),
                                 (list(self.sources), 'Premature approval')]:
            with self.subTest(selected=selected), self.assertRaises(ValueError):
                grant(self.db, selected, reason)
        self.assertEqual(self.db.execute('SELECT count(*) FROM wiki_refresh_grants').fetchone()[0], 0)

    def test_active_and_withdrawn_selections_do_not_create_grants(self):
        self.exhaust()
        identity = self.db.execute("SELECT id FROM wiki_runs WHERE state='failed' LIMIT 1").fetchone()[0]
        with self.db:
            self.db.execute("UPDATE wiki_runs SET state='running',expires=? WHERE id=?", (time.time() + 600, identity))
        with self.assertRaisesRegex(ValueError, 'active'):
            grant(self.db, list(self.sources), 'Synthetic approval')
        wiki_store.fail(self.db, identity, 'Synthetic finished interruption')
        with self.db:
            self.db.execute("UPDATE publications SET state='withdrawn-fixture' WHERE id=?", (self.publication,))
        with self.assertRaisesRegex(ValueError, 'exhausted retained'):
            grant(self.db, list(self.sources), 'Synthetic approval')
        self.assertEqual(self.db.execute('SELECT count(*) FROM wiki_refresh_grants').fetchone()[0], 0)
