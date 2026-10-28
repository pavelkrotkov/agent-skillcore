from unittest.mock import patch
import json

from x_zk_refresh_fixtures import RefreshRecoveryCase
from x_curator import wiki_refresh, wiki_store
from x_curator.cli import arguments
from x_curator.wiki_refresh_recovery import grant


class EighthRefreshGrantTests(RefreshRecoveryCase):
    def exhaust_seventh(self):
        self.exhaust_fourth()
        for level in ('fifth', 'sixth', 'seventh'):
            grant(self.db, list(self.sources), 'Synthetic explicit approval', **{level: True})
            wiki_store.fail(self.db, wiki_store.reserve(self.db, self.inputs), 'Interrupted organization')

    def test_one_cli_grant_preserves_history_and_never_allows_ninth(self):
        self.exhaust_seventh()
        before = self.history()
        prior = list(self.db.execute('SELECT * FROM wiki_refresh_seventh_grants'))
        argv = ['x', '--state', str(self.root), 'zk-refresh', '--reason', 'Separate eighth approval', '--grant-eighth-attempt']
        for source in reversed(self.sources):
            argv.extend(['--publication', source])
        with patch('sys.argv', argv), patch('x_curator.wiki.initial', side_effect=AssertionError('history load')):
            result = wiki_refresh.command(self.db, arguments())
        self.assertEqual(result['attempt_limit'], 8)
        row = self.db.execute('SELECT * FROM wiki_refresh_eighth_grants').fetchone()
        self.assertEqual((row['limit_before'], row['limit_after']), (7, 8))
        self.assertEqual((json.loads(row['publications']), row['reason']), (sorted(self.sources), 'Separate eighth approval'))
        wiki_store.fail(self.db, wiki_store.reserve(self.db, self.inputs), 'Eighth interrupted')
        with self.assertRaisesRegex(ValueError, 'budget exhausted'):
            wiki_store.reserve(self.db, self.inputs)
        with self.assertRaises(ValueError):
            grant(self.db, list(self.sources), 'Duplicate eighth', eighth=True)
        self.assertEqual(list(self.db.execute('SELECT * FROM wiki_refresh_seventh_grants')), prior)
        self.assert_history(before)

    def test_missing_seventh_unspent_busy_withdrawn_and_combined_flags_rejected(self):
        self.exhaust_fourth()
        with self.assertRaises(ValueError):
            grant(self.db, list(self.sources), 'Missing seventh', eighth=True)
        for level in ('fifth', 'sixth', 'seventh'):
            grant(self.db, list(self.sources), 'Explicit approval', **{level: True})
            with self.assertRaises(ValueError):
                grant(self.db, list(self.sources), 'Unspent previous', eighth=True)
            identity = wiki_store.reserve(self.db, self.inputs)
            with self.assertRaisesRegex(ValueError, 'active'):
                grant(self.db, list(self.sources), 'Busy', eighth=True)
            wiki_store.fail(self.db, identity, 'Previous failed')
        with self.assertRaisesRegex(ValueError, 'one explicit'):
            grant(self.db, list(self.sources), 'Combined flags', sixth=True, eighth=True)
        with self.db:
            self.db.execute("UPDATE publications SET state='withdrawn-fixture' WHERE id=?", (self.publication,))
        with self.assertRaises(ValueError):
            grant(self.db, list(self.sources), 'Withdrawn', eighth=True)
        self.assertEqual(self.db.execute('SELECT count(*) FROM wiki_refresh_eighth_grants').fetchone()[0], 0)
        argv = ['x','--state',str(self.root),'zk-refresh','--publication',self.publication,'--reason','conflicting','--grant-seventh-attempt','--grant-eighth-attempt']
        with patch('sys.argv', argv), self.assertRaises(SystemExit), patch('sys.stderr'):
            arguments()

    def test_old_database_initialization_preserves_seventh_and_history(self):
        self.exhaust_seventh()
        before = self.history()
        self.db.execute('DROP TABLE wiki_refresh_eighth_grants')
        self.assertEqual(grant(self.db, list(self.sources), 'Explicit upgrade', eighth=True)['attempt_limit'], 8)
        self.assert_history(before)
