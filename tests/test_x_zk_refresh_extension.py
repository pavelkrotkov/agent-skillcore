from unittest.mock import patch
import json

from x_zk_refresh_fixtures import RefreshRecoveryCase
from x_curator import wiki_refresh, wiki_store
from x_curator.cli import arguments
from x_curator.wiki_mapping import map_sources
from x_curator.wiki_refresh_recovery import grant


class ZKRefreshExtensionTests(RefreshRecoveryCase):
    def test_explicit_fifth_preserves_prior_grant_and_never_allows_a_sixth(self):
        self.exhaust_fourth()
        before = self.history()
        argv = ['x', '--state', str(self.root), 'zk-refresh', '--reason', 'Synthetic fifth approval', '--grant-fifth-attempt']
        for source in reversed(self.sources):
            argv.extend(['--publication', source])
        with patch('sys.argv', argv):
            args = arguments()
        with patch('x_curator.wiki.initial', side_effect=AssertionError('grant loaded history')), \
                patch('x_curator.wiki_mapping.runner', side_effect=AssertionError('grant invoked model')):
            result = wiki_refresh.command(self.db, args)
        self.assertEqual(result['attempt_limit'], 5)
        row = self.db.execute('SELECT * FROM wiki_refresh_extensions').fetchone()
        self.assertEqual((row['limit_before'], row['limit_after']), (4, 5))
        self.assertEqual((json.loads(row['publications']), row['reason']), (sorted(self.sources), args.reason))
        with patch('x_curator.wiki_mapping.runner', return_value=self.feedback_response):
            map_sources(self.db, self.inputs)
        with self.assertRaisesRegex(ValueError, 'budget exhausted'):
            wiki_store.reserve(self.db, dict(self.inputs, catalog_sha='changed', refresh_reason='changed'))
        for fifth in (False, True):
            with self.assertRaises(ValueError):
                grant(self.db, list(self.sources), 'Repeated request', fifth=fifth)
        self.assert_history(before)

    def test_premature_active_and_withdrawn_fifth_requests_are_rejected(self):
        self.exhaust()
        with self.assertRaises(ValueError):
            grant(self.db, list(self.sources), 'No fourth grant', fifth=True)
        grant(self.db, list(self.sources), 'Fourth approval')
        with self.assertRaises(ValueError):
            grant(self.db, list(self.sources), 'Unspent fourth', fifth=True)
        identity = wiki_store.reserve(self.db, self.inputs)
        with self.assertRaisesRegex(ValueError, 'active'):
            grant(self.db, list(self.sources), 'Running fourth', fifth=True)
        wiki_store.fail(self.db, identity, 'Synthetic fourth failure')
        with self.db:
            self.db.execute("UPDATE publications SET state='withdrawn-fixture' WHERE id=?", (self.publication,))
        with self.assertRaises(ValueError):
            grant(self.db, list(self.sources), 'Withdrawn source', fifth=True)
        self.assertEqual(self.db.execute('SELECT count(*) FROM wiki_refresh_extensions').fetchone()[0], 0)

    def test_old_schema_adds_extension_without_rewriting_existing_history(self):
        self.exhaust_fourth()
        before = self.history()
        self.db.execute('DROP TABLE wiki_refresh_extensions')
        result = grant(self.db, list(self.sources), 'Explicit upgraded fifth', fifth=True)
        self.assertEqual(result['attempt_limit'], 5)
        self.assert_history(before)

    def test_explicit_sixth_preserves_fifth_and_cannot_allow_a_seventh(self):
        self.exhaust_fourth()
        grant(self.db, list(self.sources), 'Fifth approval', fifth=True)
        wiki_store.fail(self.db, wiki_store.reserve(self.db, self.inputs), 'Fifth interrupted')
        before = self.history()
        fifth = list(self.db.execute('SELECT * FROM wiki_refresh_extensions'))
        argv = ['x', '--state', str(self.root), 'zk-refresh', '--reason', 'Separate sixth approval', '--grant-sixth-attempt']
        for source in self.sources:
            argv.extend(['--publication', source])
        with patch('sys.argv', argv), patch('x_curator.wiki.initial', side_effect=AssertionError('history load')):
            result = wiki_refresh.command(self.db, arguments())
        self.assertEqual(result['attempt_limit'], 6)
        identity = wiki_store.reserve(self.db, self.inputs)
        wiki_store.fail(self.db, identity, 'Sixth interrupted')
        with self.assertRaisesRegex(ValueError, 'budget exhausted'):
            wiki_store.reserve(self.db, self.inputs)
        with self.assertRaises(ValueError):
            grant(self.db, list(self.sources), 'Duplicate sixth approval', sixth=True)
        self.assertEqual(list(self.db.execute('SELECT * FROM wiki_refresh_extensions')), fifth)
        self.assert_history(before)

    def test_sixth_rejects_missing_fifth_unspent_busy_and_withdrawn(self):
        self.exhaust_fourth()
        with self.assertRaises(ValueError):
            grant(self.db, list(self.sources), 'Missing fifth', sixth=True)
        grant(self.db, list(self.sources), 'Fifth approval', fifth=True)
        with self.assertRaises(ValueError):
            grant(self.db, list(self.sources), 'Unspent fifth', sixth=True)
        identity = wiki_store.reserve(self.db, self.inputs)
        with self.assertRaisesRegex(ValueError, 'active'):
            grant(self.db, list(self.sources), 'Active fifth', sixth=True)
        wiki_store.fail(self.db, identity, 'Fifth failed')
        with self.db:
            self.db.execute("UPDATE publications SET state='withdrawn-fixture' WHERE id=?", (self.publication,))
        with self.assertRaises(ValueError):
            grant(self.db, list(self.sources), 'Withdrawn fifth', sixth=True)
        self.assertEqual(self.db.execute('SELECT count(*) FROM wiki_refresh_sixth_grants').fetchone()[0], 0)
