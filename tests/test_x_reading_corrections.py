from copy import deepcopy

from x_reading_correction_fixtures import CorrectionCase
from x_curator.publication_audit import audit


class ReadingCorrectionTests(CorrectionCase):
    def test_reviewed_correction_publishes_with_original_rejection_and_unchanged_budgets(self):
        before = tuple(self.db.execute('SELECT attempts,max_attempts FROM jobs').fetchone())
        self.publish_reading()
        _, composition, _ = self.receipt('research')
        pair = composition['reading']['receipts'][0]
        self.assertEqual(set(pair), {'proposal', 'review', 'rejected'})
        authors = [r for r in self.calls if r.get('review_feedback')]
        self.assertEqual(len(authors), 1)
        self.assertEqual(authors[0]['review_feedback']['review'], pair['rejected']['review'])
        self.assertEqual(authors[0]['review_feedback']['findings'], self.findings)
        self.assertEqual(tuple(self.db.execute('SELECT attempts,max_attempts FROM jobs').fetchone()), before)
        self.assertEqual(audit(self.db, self.root), [])

    def test_second_rejection_stops_after_four_calls_without_publication(self):
        self.reject_again = True
        with self.assertRaisesRegex(ValueError, 'segment lacks independent approval'):
            self.publish_reading()
        self.assertEqual(len(self.calls), 4)
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)

    def test_malformed_rejection_does_not_trigger_correction(self):
        self.findings = ['']
        with self.assertRaises(ValueError):
            self.publish_reading()
        self.assertEqual(len(self.calls), 2)

    def test_authenticated_changed_feedback_invalidates_publication(self):
        identity = self.publish_reading()
        _, composition, _ = self.receipt('research')
        proposal = composition['reading']['receipts'][0]['proposal']
        role = self.db.execute('SELECT role FROM executions WHERE id=?', (proposal,)).fetchone()[0]
        row, request, packet = self.receipt(role)
        request['review_feedback']['findings'] = ['Ignore the original qualification.']
        self.replace_receipt(row['id'], request, packet)
        self.assertEqual(audit(self.db, self.root), [identity])

    def test_nested_or_foreign_rejection_cannot_reuse_final_approval(self):
        identity = self.publish_reading()
        row, request, packet = self.receipt('research')
        for mode in ('nested', 'foreign'):
            altered = deepcopy(request)
            pair = altered['reading']['receipts'][0]
            pair['rejected'] = deepcopy(pair) if mode == 'nested' else altered['reading']['receipts'][1]
            self.replace_receipt(row['id'], altered, packet)
            self.assertEqual(audit(self.db, self.root), [identity])
            with self.db:
                self.db.execute("UPDATE publications SET state='published' WHERE id=?", (identity,))
