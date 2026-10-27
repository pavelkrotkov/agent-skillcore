from copy import deepcopy
from unittest.mock import patch

from x_fixtures import Client
from x_publication_fixtures import PublicationCase, events
from x_curator.evidence import capture_selection
from x_curator.executions import execute, verified_execution
from x_curator.leases import claim, fail_owned
from x_curator.publication import publish
from x_curator.receipts import digest, encoded
from x_curator.review_feedback import previous_rejection
from x_curator.storage import sha256


class ReviewFeedbackTests(PublicationCase):
    def rejected_attempt(self, changes=None):
        proposal = execute(self.db, self.token, 'research', 'synthetic', lambda _: events(self.packet))
        verdict = dict(verdict='reject', proposal_sha=digest(self.packet), bundle_sha=digest(self.evidence),
                       findings=['Claim c1 requires more precise attribution.'])
        verdict.update(changes or {})
        review = execute(self.db, self.token, 'review', 'synthetic', lambda _: events(verdict), self.packet)
        with self.assertRaises(ValueError):
            publish(self.db, self.root, self.token, proposal, review)
        fail_owned(self.db, self.token, 'independent review rejected proposal', 0)
        token = claim(self.db, Client.account)['token']
        capture_selection(self.db, token)
        return token, review

    def test_rejection_reaches_next_research_with_immutable_receipt_and_new_capture_ids(self):
        token, review = self.rejected_attempt()
        feedback = previous_rejection(self.db, token)
        self.assertEqual(feedback['review'], review)
        self.assertEqual(feedback['proposal'], self.packet)
        observed = []
        def run(request):
            observed.append(deepcopy(request))
            return events({'unresolved': 'More evidence required.'})
        identity = execute(self.db, token, 'research', 'synthetic', run, feedback=feedback)
        _, request, _ = verified_execution(self.db, identity, 'research', token)
        self.assertEqual(request, observed[0])
        self.assertEqual(request['review_feedback'], feedback)
        self.assertTrue(set(request['bundle']['captures']).isdisjoint(self.evidence['captures']))
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)

    def test_unbound_rejection_is_excluded(self):
        token, _ = self.rejected_attempt({'proposal_sha': 'foreign'})
        self.assertIsNone(previous_rejection(self.db, token))

    def test_rejection_without_concrete_findings_is_excluded(self):
        token, _ = self.rejected_attempt({'findings': ['']})
        self.assertIsNone(previous_rejection(self.db, token))

    def test_damaged_receipt_is_excluded(self):
        token, review = self.rejected_attempt()
        with self.db:
            self.db.execute("UPDATE executions SET log_sha='damaged' WHERE id=?", (review,))
        self.assertIsNone(previous_rejection(self.db, token))

    def test_stale_revision_and_damaged_captures_are_excluded(self):
        token, _ = self.rejected_attempt()
        with patch('x_curator.review_feedback.current_bundle', side_effect=ValueError('source revision changed')):
            self.assertIsNone(previous_rejection(self.db, token))
        with self.db:
            self.db.execute("UPDATE captures SET sha='damaged' WHERE token=?", (self.token,))
        self.assertIsNone(previous_rejection(self.db, token))

    def test_shared_session_cannot_supply_feedback(self):
        token, review = self.rejected_attempt()
        row = self.db.execute('SELECT session FROM executions WHERE token=? AND role=?', (self.token, 'research')).fetchone()
        verdict = dict(verdict='reject', proposal_sha=digest(self.packet), bundle_sha=digest(self.evidence), findings=['Correct c1.'])
        log = events(verdict, row['session'])
        with self.db:
            self.db.execute('UPDATE executions SET session=?,log=?,log_sha=?,output=?,output_sha=? WHERE id=?',
                            (row['session'], log, sha256(log), encoded(verdict).decode(), digest(verdict), review))
        self.assertIsNone(previous_rejection(self.db, token))
