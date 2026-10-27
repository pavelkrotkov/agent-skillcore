import json
from unittest.mock import patch

from x_deep_fixtures import DeepCase
from x_fixtures import Client, collect, envelope, tweet_entry
from x_curator import deep_claim, deep_permission, deep_review, deep_scope
from x_curator.publication_audit import audit


class DeepScopeTests(DeepCase):
    def test_source_edit_between_claim_and_capture_never_reaches_model(self):
        self.authorize()
        claim = deep_claim.claim
        def changed(db, identity):
            job = claim(db, identity)
            entry = tweet_entry('1')
            entry['content']['itemContent']['tweet_results']['result']['legacy'] = {'full_text': 'Edited after approval claim'}
            collect(db, Client([(200, envelope([{'type': 'TimelineAddEntries', 'entries': [entry]}]))]), 'likes', new=True, delay=0)
            return job
        self.checker = lambda request: self.fail('unapproved revision reached model')
        with patch('x_curator.deep_claim.claim', changed):
            result = self.deep()
        self.assertEqual(result['state'], 'awaiting_review')
        self.assertIn('approved revision', result['reason'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)

    def test_historical_proof_checks_observed_revision_and_scope(self):
        self.authorize()
        self.checker = super().checker
        self.assertEqual(self.deep()['state'], 'published')
        permission, proposal = deep_permission.verified(self.db, self.approval)
        row = self.db.execute('SELECT input FROM executions WHERE token=(SELECT token FROM deep_runs)').fetchone()
        evidence = json.loads(row['input'])['bundle']
        with self.assertRaises(ValueError):
            deep_scope.observed(dict(permission, revision='changed'), proposal, evidence)
        self.assertEqual(audit(self.db, self.root), [])

    def test_resource_type_url_and_larger_budget_are_explicit_in_new_request(self):
        self.authorize()
        self.deep()
        account = self.db.execute('SELECT account FROM research_permissions').fetchone()[0]
        resource = {'kind': 'pdf', 'url': 'https://example.test/book.pdf'}
        value = deep_review.prepare(self.db, account, 'synthetic-chat', self.approval, 1200, resource)
        self.assertIn('https://example.test/book.pdf', value['message'])
        self.assertIn('1200 seconds', value['message'])
        self.assertEqual(json.loads(value['payload'])['review'][0]['resource'], resource)
        self.assertEqual(self.db.execute('SELECT count(*) FROM research_permissions').fetchone()[0], 1)
        with self.assertRaises(ValueError):
            deep_review.prepare(self.db, account, 'synthetic-chat', resource=resource)
