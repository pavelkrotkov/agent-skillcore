from unittest.mock import patch
import json

from x_zk_refresh_fixtures import RefreshRecoveryCase
from x_curator import wiki_refresh, wiki_store
from x_curator.cli import arguments
from x_curator.wiki_refresh_recovery import grant


class SeventhRefreshGrantTests(RefreshRecoveryCase):
    def exhaust_sixth(self):
        self.exhaust_fourth()
        for level in ('fifth', 'sixth'):
            grant(self.db, list(self.sources), 'Synthetic explicit approval', **{level: True})
            wiki_store.fail(self.db, wiki_store.reserve(self.db, self.inputs), 'Interrupted organization')

    def test_one_cli_grant_preserves_history_and_never_allows_eighth(self):
        self.exhaust_sixth()
        before = self.history()
        prior = list(self.db.execute('SELECT * FROM wiki_refresh_sixth_grants'))
        argv = ['x', '--state', str(self.root), 'zk-refresh', '--reason', 'Separate seventh approval', '--grant-seventh-attempt']
        for source in reversed(self.sources):
            argv.extend(['--publication', source])
        with patch('sys.argv', argv), patch('x_curator.wiki.initial', side_effect=AssertionError('history load')):
            result = wiki_refresh.command(self.db, arguments())
        self.assertEqual(result['attempt_limit'], 7)
        row = self.db.execute('SELECT * FROM wiki_refresh_seventh_grants').fetchone()
        self.assertEqual((row['limit_before'], row['limit_after']), (6, 7))
        self.assertEqual((json.loads(row['publications']), row['reason']), (sorted(self.sources), 'Separate seventh approval'))
        wiki_store.fail(self.db, wiki_store.reserve(self.db, self.inputs), 'Seventh interrupted')
        with self.assertRaisesRegex(ValueError, 'budget exhausted'):
            wiki_store.reserve(self.db, self.inputs)
        with self.assertRaises(ValueError):
            grant(self.db, list(self.sources), 'Duplicate seventh', seventh=True)
        self.assertEqual(list(self.db.execute('SELECT * FROM wiki_refresh_sixth_grants')), prior)
        self.assert_history(before)

    def test_missing_sixth_unspent_busy_withdrawn_and_combined_flags_rejected(self):
        self.exhaust_fourth()
        with self.assertRaises(ValueError):
            grant(self.db, list(self.sources), 'Missing sixth', seventh=True)
        for level in ('fifth', 'sixth'):
            grant(self.db, list(self.sources), 'Explicit approval', **{level: True})
            with self.assertRaises(ValueError):
                grant(self.db, list(self.sources), 'Unspent previous', seventh=True)
            identity = wiki_store.reserve(self.db, self.inputs)
            with self.assertRaisesRegex(ValueError, 'active'):
                grant(self.db, list(self.sources), 'Busy', seventh=True)
            wiki_store.fail(self.db, identity, 'Previous failed')
        with self.assertRaisesRegex(ValueError, 'one explicit'):
            grant(self.db, list(self.sources), 'Combined flags', sixth=True, seventh=True)
        with self.db:
            self.db.execute("UPDATE publications SET state='withdrawn-fixture' WHERE id=?", (self.publication,))
        with self.assertRaises(ValueError):
            grant(self.db, list(self.sources), 'Withdrawn', seventh=True)
        self.assertEqual(self.db.execute('SELECT count(*) FROM wiki_refresh_seventh_grants').fetchone()[0], 0)

    def test_old_database_initialization_preserves_sixth_and_history(self):
        self.exhaust_sixth()
        before = self.history()
        self.db.execute('DROP TABLE wiki_refresh_seventh_grants')
        self.assertEqual(grant(self.db, list(self.sources), 'Explicit upgrade', seventh=True)['attempt_limit'], 7)
        self.assert_history(before)
