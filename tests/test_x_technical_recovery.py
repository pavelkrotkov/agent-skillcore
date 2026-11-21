"""Operator recovery admits exact retained technical failures without budget grants."""
import json
import time
from unittest.mock import patch

from x_fixtures import Client
from x_quick_fixtures import QuickCase, native
from x_curator import batch_queue, quick_process, quick_retry_recovery, quick_store, review_store


class TechnicalRecoveryTests(QuickCase):
    reason = 'Quick check inconclusive: DeadlineExceeded: execution deadline exhausted'

    def held(self, check=True):
        review_store.initialize(self.db)
        if check:
            quick_store.start(self.db, self.token, time.time())
            quick_store.finish(self.db, self.token, 'inconclusive', self.reason)
        else:
            with self.db:
                self.db.execute("UPDATE jobs SET state='awaiting_review',action=?,token=NULL,lease_until=NULL", (self.reason,))
                self.db.execute("UPDATE attempts SET state='awaiting_review',action=?,finished=?", (self.reason, time.time()))
        return quick_retry_recovery.run(self.db, Client.account, sources=['1'])

    def test_preview_and_exact_apply_preserve_original_check_attempt_and_limits(self):
        preview = self.held()
        old_check = dict(self.db.execute('SELECT * FROM quick_checks').fetchone())
        old_attempt = dict(self.db.execute('SELECT * FROM attempts').fetchone())
        self.assertEqual(len(preview['items']), 1)
        result = quick_retry_recovery.run(self.db, Client.account, preview['digest'], ['1'])
        self.assertEqual((result['extra_attempts'], result['extra_requests']), (0, 0))
        self.assertEqual(dict(self.db.execute('SELECT * FROM quick_checks').fetchone()), old_check)
        self.assertEqual(dict(self.db.execute('SELECT * FROM attempts').fetchone()), old_attempt)
        self.assertEqual(tuple(self.db.execute('SELECT state,attempts,max_attempts FROM jobs').fetchone()), ('retry', 1, 3))
        self.assertEqual(quick_retry_recovery.run(self.db, Client.account)['items'], [])

    def test_failure_before_check_creation_still_has_a_retained_attempt_anchor(self):
        preview = self.held(check=False)
        self.assertIsNone(preview['items'][0]['check'])
        quick_retry_recovery.run(self.db, Client.account, preview['digest'], ['1'])
        self.assertEqual(self.db.execute('SELECT check_id FROM quick_retry_failures').fetchone()[0], None)

    def test_other_accounts_and_unselected_sources_are_not_recovered(self):
        self.held()
        self.assertEqual(quick_retry_recovery.run(self.db, 'other-account')['items'], [])
        self.assertEqual(quick_retry_recovery.run(self.db, Client.account, sources=['different'])['items'], [])

    def test_factual_inconclusive_and_recorded_deferral_are_held(self):
        self.held()
        with self.db:
            self.db.execute("UPDATE quick_checks SET reason='A factual claim remains unresolved',execution='completed-model'")
        self.assertEqual(quick_retry_recovery.run(self.db, Client.account)['items'], [])
        with self.db:
            self.db.execute('UPDATE quick_checks SET reason=?,execution=NULL', (self.reason,))
            self.db.execute("INSERT INTO curation_batches VALUES ('batch',?,'backlog',0,0,'closed')", (Client.account,))
            self.db.execute("INSERT INTO review_deliveries VALUES ('delivery','batch','chat',?,'message',0,NULL,NULL)",
                            (json.dumps({'account': Client.account}),))
            self.db.execute("INSERT INTO review_decisions VALUES ('delivery','batch:1','defer','retained human decision',0)")
        self.assertEqual(quick_retry_recovery.run(self.db, Client.account)['items'], [])

    def test_preview_digest_rejects_changed_scope_or_budget(self):
        preview = self.held()
        with self.assertRaisesRegex(ValueError, 'preview changed'):
            quick_retry_recovery.run(self.db, Client.account, preview['digest'], ['different'])
        with self.db:
            self.db.execute('UPDATE jobs SET attempts=max_attempts')
        with self.assertRaisesRegex(ValueError, 'preview changed'):
            quick_retry_recovery.run(self.db, Client.account, preview['digest'], ['1'])

    def test_old_technical_receipt_cannot_reopen_a_later_factual_decision(self):
        preview = self.held()
        quick_retry_recovery.run(self.db, Client.account, preview['digest'], ['1'])
        next_at = self.db.execute('SELECT next_at FROM jobs').fetchone()[0]
        with patch('x_curator.batch_queue.time.time', return_value=next_at + 1):
            self.token = batch_queue.claim(self.db, Client.account)['token']
        decision = dict(outcome='inconclusive', reason='A factual claim remains unresolved.', central=['f1'],
                        checks=[dict(id='f1', text='The release was in 2025.', status='inconclusive', sources=[])])
        with patch('x_curator.quick_process.runner', return_value=lambda request: native(request, decision, [])):
            quick_process.research(self.db, self.root, self.client, self.token)
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'awaiting_review')
        self.assertEqual(quick_retry_recovery.run(self.db, Client.account)['items'], [])
