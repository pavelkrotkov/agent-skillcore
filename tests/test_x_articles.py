import json
import time
from unittest.mock import patch

from x_fixtures import Client
from x_quick_fixtures import QuickCase
from x_curator import blobs, quick_articles, quick_context, quick_mcp, quick_sources, quick_store
from x_curator.evidence import bundle
from x_curator.receipts import digest, encoded


class ArticleExcerptTests(QuickCase):
    url = 'https://x.com/i/article/1234567890'

    def capture_article(self, article):
        focal = json.loads(Client([]).detail('1')[1])['data']
        focal['article'] = {'article_results': {'result': article}}
        self.client.detail = lambda _: (200, encoded(dict(data=focal)))
        quick_context.thread(self.db, self.token, self.client)
        quick_store.start(self.db, self.token, time.time())
        self.source = quick_sources.source(self.db, self.token, self.url)

    def read_article(self, match=''):
        with patch('x_curator.quick_web.fetch', side_effect=AssertionError('must not use public HTTP')):
            return quick_mcp.call(self.db, self.token, 'read', dict(source=self.source, match=match))

    def test_body_excerpt_matches_retained_identity_bytes_and_budget(self):
        text = '🧠' * 8000 + 'Target body.' + '🧠' * 8000
        self.capture_article(dict(rest_id='1234567890', plain_text=text, preview_text='Preview only.'))
        before = self.db.execute('SELECT count(*) FROM retrievals').fetchone()[0]
        result = json.loads(self.read_article('Target body.')['content'][0]['text'])
        excerpt = result['evidence']
        self.assertEqual((excerpt['text'], excerpt['excerpt_start'], excerpt['article_id']),
                         (text[6000:12000], 6000, '1234567890'))
        evidence = bundle(self.db, self.token)
        self.assertIn(text, blobs.read(self.db, excerpt['body_sha']).decode())
        self.assertEqual(self.db.execute('SELECT count(*) FROM retrievals').fetchone()[0], before)
        absent = json.loads(self.read_article('missing')['content'][0]['text'])['evidence']
        self.assertEqual(absent['text'], text[:6000])

    def test_preview_empty_body_and_wrong_identity_never_qualify(self):
        for article in (dict(rest_id='1234567890', title='Title', preview_text='Preview only.'),
                        dict(rest_id='1234567890', plain_text=' ', content_state={'blocks': []}),
                        dict(rest_id='9999999999', plain_text='Wrong body.', nested={'rest_id': '1234567890'})):
            with self.subTest(article=article):
                self.capture_article(article)
                result = self.read_article()
                self.assertTrue(result['isError'])
                self.assertIn('body', result['content'][0]['text'])

    def test_excerpt_tampering_cannot_be_rehashed_into_authentic_evidence(self):
        self.capture_article(dict(rest_id='1234567890', plain_text='Authentic body.'))
        result = json.loads(self.read_article()['content'][0]['text'])
        payload = dict(result['evidence'], text='Fabricated body.')
        self.db.execute('UPDATE captures SET payload=?,sha=? WHERE id=?',
                        (encoded(payload).decode(), digest(payload), result['capture']))
        with self.assertRaisesRegex(ValueError, 'article excerpt differs'):
            bundle(self.db, self.token)
        payload['text'] = 'Authentic body.'
        self.db.execute('UPDATE captures SET payload=?,sha=? WHERE id=?',
                        (encoded(payload).decode(), digest(payload), result['capture']))
        evidence = bundle(self.db, self.token)
        self.db.execute('UPDATE retrievals SET status=403')
        with self.assertRaisesRegex(ValueError, 'authenticated detail retrieval'):
            quick_articles.verify(self.db, evidence)
