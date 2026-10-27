from copy import deepcopy

from x_reading_fixtures import ReadingCase
from x_curator.publication_audit import audit


class ReadingIntegrityTests(ReadingCase):
    def test_missing_or_changed_interval_invalidates_even_authentic_composition_receipt(self):
        identity = self.publish_reading()
        row, request, output = self.receipt('research')
        for mutate in ('omit', 'alter'):
            altered = deepcopy(request)
            if mutate == 'omit':
                altered['reading']['receipts'].pop()
            else:
                altered['reading']['plan']['parts'][0][0]['start'] += 1
            self.replace_receipt(row['id'], altered, output)
            self.assertEqual(audit(self.db, self.root), [identity])
            with self.db:
                self.db.execute("UPDATE publications SET state='published' WHERE id=?", (identity,))

    def test_forged_aggregate_and_swapped_review_are_rejected(self):
        identity = self.publish_reading()
        row, request, output = self.receipt('research')
        altered = deepcopy(request)
        altered['bundle']['approved_segment_claims']['claims'][0]['text'] = 'Invented synthesis.'
        self.replace_receipt(row['id'], altered, output)
        self.assertEqual(audit(self.db, self.root), [identity])
        with self.db:
            self.db.execute("UPDATE publications SET state='published' WHERE id=?", (identity,))
        altered = deepcopy(request)
        altered['reading']['receipts'][0]['review'] = altered['reading']['receipts'][1]['review']
        self.replace_receipt(row['id'], altered, output)
        self.assertEqual(audit(self.db, self.root), [identity])

    def test_segment_approval_requires_a_distinct_session(self):
        identity = self.publish_reading()
        _, request, _ = self.receipt('research')
        pair = request['reading']['receipts'][0]
        author = self.db.execute('SELECT session FROM executions WHERE id=?', (pair['proposal'],)).fetchone()[0]
        review = self.db.execute('SELECT role FROM executions WHERE id=?', (pair['review'],)).fetchone()[0]
        row, review_request, verdict = self.receipt(review)
        self.replace_receipt(row['id'], review_request, verdict, author)
        self.assertEqual(audit(self.db, self.root), [identity])

    def test_new_splitter_policy_does_not_invalidate_historical_complete_reading(self):
        from unittest.mock import patch
        self.publish_reading()
        with patch.dict('x_curator.reading_plan.POLICIES', {2: {'width': 200, 'context': 5, 'max_segments': 16}}), patch('x_curator.reading_plan.CURRENT_VERSION', 2):
            self.assertEqual(audit(self.db, self.root), [])

    def test_authenticated_but_changed_boundary_context_invalidates_publication(self):
        identity = self.publish_reading()
        _, composition, _ = self.receipt('research')
        segment = composition['reading']['receipts'][0]['proposal']
        role = self.db.execute('SELECT role FROM executions WHERE id=?', (segment,)).fetchone()[0]
        row, request, output = self.receipt(role)
        key = next(iter(request['bundle']['boundary_context']))
        request['bundle']['boundary_context'][key]['after'] += ' Altered context.'
        self.replace_receipt(row['id'], request, output)
        self.assertEqual(audit(self.db, self.root), [identity])
