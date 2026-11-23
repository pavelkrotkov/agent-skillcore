import json
from unittest.mock import patch

from x_video_fixtures import PreparedVideoCase
from x_fixtures import Client, collect, envelope, tweet_entry
from x_curator import blobs, prepared_video
from x_curator.evidence import bundle
from x_curator.source_evidence import selected_source
from x_curator.source_currentness import currentness
from x_curator.receipts import encoded


class PreparationPolicyTests(PreparedVideoCase):
    def historical(self, revision='832531cd1bfc31350589f8b3ffae816dc27631f8486747efc7fca3adb9305205'):
        payload = self.payload()
        manifest = json.loads(blobs.read(self.db, payload['preparation_sha']))
        manifest['revision'] = revision
        payload['preparation_sha'] = blobs.put(self.db, encoded(manifest))
        return prepared_video.store(self.db, self.job, payload, 'Approved historical preparation')

    def test_original_preparation_survives_publication_policy_change_without_rewrite(self):
        identity = self.historical()
        self.assertEqual(prepared_video.revision(self.db, self.job),
                         '832531cd1bfc31350589f8b3ffae816dc27631f8486747efc7fca3adb9305205')
        before = tuple(self.db.execute('SELECT * FROM prepared_videos WHERE id=?', (identity,)).fetchone())
        with patch('x_curator.public_http.exchange', side_effect=AssertionError('No network')), \
                patch('x_curator.source_currentness.CURRENTNESS_POLICY', 'source-currentness/v99'):
            prepared_video.attach(self.db, self.token)
            captures = bundle(self.db, self.token)['captures']
            self.assertEqual(len(prepared_video.registered(self.db, self.job)), 1)
            self.assertEqual(prepared_video.seconds(self.db, self.job), 180)
        self.assertTrue(any(value.get('prepared_video') == identity for value in captures.values()))
        self.assertEqual(tuple(self.db.execute('SELECT * FROM prepared_videos WHERE id=?', (identity,)).fetchone()), before)

    def test_changed_authentic_source_still_rejects_historical_preparation(self):
        identity = self.historical()
        entry = tweet_entry('1')
        entry['content']['itemContent']['tweet_results']['result']['legacy'] = dict(
            full_text='Changed source', extended_entities=dict(media=[dict(type='video', video_info=dict(
                variants=[dict(content_type='video/mp4', bitrate=100, url=self.url)]))]))
        collect(self.db, Client([(200, envelope([dict(type='TimelineAddEntries', entries=[entry])]))]), 'likes', new=True, delay=0)
        payload = self.db.execute('SELECT payload FROM prepared_videos WHERE id=?', (identity,)).fetchone()[0]
        with self.assertRaisesRegex(ValueError, 'stale'):
            prepared_video.verify_one(self.db, json.loads(payload), self.job)
        self.assertEqual(prepared_video.registered(self.db, self.job), [])

    def test_preparation_keeps_original_note_and_duplicate_alt_binding(self):
        entry = selected_source(self.db, self.job)['entry']
        post = entry['content']['itemContent']['tweet_results']['result']
        post['note_tweet'] = dict(note_tweet_results=dict(result=dict(text='A clip', entity_set=dict(
            user_mentions=[dict(id_str='2', name='Original author', screen_name='handle')]))))
        post['card'] = dict(legacy=dict(binding_values=[
            dict(key='thumbnail_image', value=dict(type='IMAGE', image_value=dict(
                url='https://pbs.twimg.com/card_img/example', alt='Retained alt'))),
            dict(key='thumbnail_image_alt_text', value=dict(type='STRING', string_value='Retained alt'))]))
        collect(self.db, Client([(200, envelope([dict(type='TimelineAddEntries', entries=[entry])]))]), 'likes', new=True, delay=0)
        identity = self.historical('3a2087e90ff7a71f873863027a0aa7dfb18173f60f8a7b74d922bc6e5a0abedc')
        self.assertEqual(prepared_video.revision(self.db, self.job),
                         '3a2087e90ff7a71f873863027a0aa7dfb18173f60f8a7b74d922bc6e5a0abedc')
        self.assertNotEqual(currentness(entry)[1], currentness(entry, preparation=True)[1])
        payload = json.loads(self.db.execute('SELECT payload FROM prepared_videos WHERE id=?', (identity,)).fetchone()[0])
        prepared_video.verify_one(self.db, payload, self.job)
        post['note_tweet']['note_tweet_results']['result']['entity_set']['user_mentions'][0]['name'] = 'Changed author'
        collect(self.db, Client([(200, envelope([dict(type='TimelineAddEntries', entries=[entry])]))]), 'likes', new=True, delay=0)
        with self.assertRaisesRegex(ValueError, 'stale'):
            prepared_video.verify_one(self.db, payload, self.job)
