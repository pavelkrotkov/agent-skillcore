import json

from x_review_fixtures import ReviewCase, readback
from x_fixtures import Client, collect, envelope, tweet_entry
from x_curator import review_outbox, review_receipts
from x_curator.receipts import digest
from x_curator.storage import open_store


class ReviewRecoveryTests(ReviewCase):
    def test_restart_replay_preserves_one_permission_and_defer_can_be_revisited(self):
        value = self.prepare(2)
        self.observe()
        a, b = self.references
        self.reply(f'research {a}; defer {b}')
        self.db.close()
        self.db = open_store(self.root)
        self.assertEqual(review_outbox.prepare(self.db, value['batch'], value['chat'])['message'], value['message'])
        self.reply(f'research {a}; defer {b}')
        self.reply(f'research {b}', identity='later-human')
        self.assertEqual(self.db.execute('SELECT count(*) FROM research_permissions').fetchone()[0], 2)
        self.assertEqual(self.db.execute('SELECT count(*) FROM review_replies').fetchone()[0], 2)

    def test_legacy_v1_delivery_still_validates(self):
        value = self.prepare()
        payload = json.loads(value['payload'])
        identity = digest(['chat-review/v1', value['batch'], value['chat'], payload])
        message = review_outbox.render(identity, payload)
        self.assertNotIn('Status:', message)
        with self.db:
            self.db.execute('UPDATE review_deliveries SET id=?,message=? WHERE id=?', (identity, message, value['id']))
        receipt = readback(value['chat'], 'legacy-delivery', message)
        self.assertEqual(review_receipts.observe(self.db, identity, receipt, 'legacy-delivery')['state'], 'delivered')

    def test_changed_source_aborts_whole_reply_without_permission(self):
        self.prepare(2)
        self.observe()
        entry = tweet_entry('2')
        entry['content']['itemContent']['tweet_results']['result']['legacy'] = {'full_text': 'Changed synthetic claim'}
        collect(self.db, Client([(200, envelope([{'type': 'TimelineAddEntries', 'entries': [entry]}]))]), 'likes', new=True, delay=0)
        a, b = self.references
        with self.assertRaises(ValueError):
            self.reply(f'research {a}; research {b}')
        self.assertEqual(self.db.execute('SELECT count(*) FROM research_permissions').fetchone()[0], 0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM review_decisions').fetchone()[0], 0)

    def test_same_message_id_cannot_be_reused_for_new_decisions(self):
        self.prepare(2)
        self.observe()
        a, b = self.references
        self.reply(f'research {a}')
        with self.assertRaises(ValueError):
            self.reply(f'research {b}')
        self.assertEqual(self.db.execute('SELECT count(*) FROM research_permissions').fetchone()[0], 1)

    def test_modified_scope_cannot_reuse_the_original_observed_approval(self):
        value = self.prepare()
        self.observe()
        payload = json.loads(value['payload'])
        payload['review'][0].update(seconds=36000, scope='Read every full book and video')
        with self.db:
            self.db.execute('UPDATE review_deliveries SET payload=?', (json.dumps(payload),))
        with self.assertRaises(ValueError):
            self.reply('research ' + self.references[0])
        self.assertEqual(self.db.execute('SELECT count(*) FROM research_permissions').fetchone()[0], 0)
