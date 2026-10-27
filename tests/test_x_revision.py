import json

from x_publication_fixtures import PublicationCase
from x_fixtures import Client, collect, envelope
from x_curator.publication import publish
from x_curator.publication_audit import audit


class RevisionTests(PublicationCase):
    def refresh(self, **changes):
        entry = json.loads(self.db.execute('SELECT entry FROM selections LIMIT 1').fetchone()[0])
        entry['sortIndex'] = 'new selection rank'
        entry['content']['itemContent']['tweet_results']['result']['legacy'].update(changes)
        collect(self.db, Client([(200, envelope([{'type': 'TimelineAddEntries', 'entries': [entry]}]))]),
                'likes', new=True, delay=0)

    def test_engagement_refresh_preserves_publication_but_changed_text_withdraws_it(self):
        proposal, review = self.approved_executions()
        publication = publish(self.db, self.root, self.token, proposal, review)
        self.refresh(favorite_count=500, retweet_count=20)
        self.assertEqual(audit(self.db, self.root), [])
        self.refresh(full_text='Changed substantive evidence.')
        self.assertEqual(audit(self.db, self.root), [publication])
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'retry')

    def test_profile_pin_refresh_preserves_publication_but_changed_author_withdraws_it(self):
        proposal, review = self.approved_executions()
        publication = publish(self.db, self.root, self.token, proposal, review)
        entry = json.loads(self.db.execute('SELECT entry FROM selections LIMIT 1').fetchone()[0])
        author = entry['content']['itemContent']['tweet_results']['result']['core']['user_results']['result']
        author['legacy']['pinned_tweet_ids_str'] = ['3']
        collect(self.db, Client([(200, envelope([{'type': 'TimelineAddEntries', 'entries': [entry]}]))]),
                'likes', new=True, delay=0)
        self.assertEqual(audit(self.db, self.root), [])
        author['rest_id'] = 'different-author'
        collect(self.db, Client([(200, envelope([{'type': 'TimelineAddEntries', 'entries': [entry]}]))]),
                'likes', new=True, delay=0)
        self.assertEqual(audit(self.db, self.root), [publication])
