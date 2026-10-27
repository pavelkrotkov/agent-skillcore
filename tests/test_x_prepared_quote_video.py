import copy
import json

from x_video_fixtures import PreparedVideoCase
from x_fixtures import Client, collect, envelope
from x_curator import prepared_video
from x_curator.source_evidence import selected_source


class PreparedQuoteVideoTests(PreparedVideoCase):
    def quoted(self, identity='quoted', url=None):
        entry = copy.deepcopy(selected_source(self.db, self.job)['entry'])
        tweet = entry['content']['itemContent']['tweet_results']['result']
        media = tweet['legacy'].pop('extended_entities', {}).get('media', [])
        if not media:
            media = tweet['quoted_status_result']['result']['tweet']['legacy']['extended_entities']['media']
        if url:
            media[0]['video_info']['variants'][0]['url'] = url
        tweet['legacy']['quoted_status_id_str'] = 'quoted'
        tweet['quoted_status_result'] = dict(result=dict(__typename='TweetWithVisibilityResults', tweet=dict(
            __typename='Tweet', rest_id=identity, legacy=dict(full_text='Quoted clip', extended_entities=dict(media=media)))))
        collect(self.db, Client([(200, envelope([dict(type='TimelineAddEntries', entries=[entry])]))]),
                'likes', new=True, delay=0)

    def test_matching_quote_registers_attaches_and_rejects_changed_media(self):
        self.quoted()
        identity = prepared_video.store(self.db, self.job, self.payload(), 'Synthetic quote approval')
        payload = json.loads(self.db.execute('SELECT payload FROM prepared_videos WHERE id=?', (identity,)).fetchone()[0])
        prepared_video.attach(self.db, self.token)
        prepared_video.verify_one(self.db, payload, self.job)
        self.quoted(url='https://video.example.test/changed.mp4')
        with self.assertRaisesRegex(ValueError, 'stale, foreign or tampered'):
            prepared_video.verify_one(self.db, payload, self.job)

    def test_mismatched_quote_cannot_admit_its_media(self):
        self.quoted(identity='unrelated')
        with self.assertRaisesRegex(ValueError, 'not selected-post media'):
            prepared_video.store(self.db, self.job, self.payload(), 'Synthetic quote approval')
