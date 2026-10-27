from unittest.mock import patch

from x_quick_photo_fixtures import PhotoCase
from x_quick_fixtures import native
from x_review_fixtures import readback
from x_fixtures import Client, collect, envelope, tweet_entry
from x_curator import batch_report, deep_process, review_outbox, review_receipts, review_decisions


class DeepPhotoCase(PhotoCase):
    def authorize(self):
        entry = tweet_entry('1')
        entry['content']['itemContent']['tweet_results']['result'] = self.posts[0]
        collect(self.db, Client([(200, envelope([{'type': 'TimelineAddEntries', 'entries': [entry]}]))]), 'likes', new=True, delay=0)
        original = self.checker
        self.checker = lambda request: native(request, {'format': 'compact-v1', 'outcome': 'inconclusive',
            'reason': 'Synthetic artifact needs primary verification.', 'claims': []}, [], images=self.inputs(request))
        self.run_worker()
        self.checker = original
        batch = batch_report.report(self.db)['batches'][0]
        value = review_outbox.prepare(self.db, batch['id'], 'synthetic-chat')
        reference = batch['review'][0]['reference']
        review_receipts.observe(self.db, value['id'], readback('synthetic-chat', 'synthetic-proposal', value['message']), 'synthetic-proposal')
        reply = 'review ' + value['id'] + '; research ' + reference
        review_decisions.apply(self.db, value['id'], readback('synthetic-chat', 'synthetic-human', reply, 'userMessage'), 'synthetic-human', human_origin_confirmed=True)
        self.approval = self.db.execute('SELECT id FROM research_permissions').fetchone()[0]

    def deep(self):
        with patch('x_curator.public_http.exchange', self.exchange), patch('x_curator.deep_process.runner', self.runner), \
                patch('x_curator.readers.extract', side_effect=AssertionError('unapproved media reader forbidden')):
            return deep_process.work(self.db, self.root, self.approval)
