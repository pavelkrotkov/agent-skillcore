import time
from unittest.mock import patch

from x_fixtures import Client
from x_publication_fixtures import PublicationCase
from x_curator import dropbox
from x_curator.readers import extract
from x_curator.retrievals import retrieve, request
from x_curator.acquire import acquire_urls
from x_curator.evidence import bundle, capture_selection, save_capture
from x_curator.leases import claim, fail_owned


class DropboxReaderTests(PublicationCase):
    def test_binary_download_uses_pdf_reader_without_changing_original_mime(self):
        body = b'%PDF-1.7\nSynthetic PDF bytes for dispatch only.'
        payload = retrieve(self.db, self.token, 'https://dropbox.com/s/id/a.pdf',
                           lambda _: (200, 'application/binary', body, None))
        with patch('x_curator.pdf_reader.extract', side_effect=lambda db, data: dict(data, kind='text', text='Complete synthetic PDF text.')) as reader:
            capture = extract(self.db, payload)
        reader.assert_called_once_with(self.db, payload)
        self.assertEqual(capture['mime'], 'application/binary')
        self.assertEqual(capture['body_sha'], payload['body_sha'])
        self.assertEqual(capture['text'], 'Complete synthetic PDF text.')
        with patch('x_curator.pdf_reader.extract', side_effect=ValueError('damaged PDF')):
            with self.assertRaisesRegex(ValueError, 'damaged PDF'):
                extract(self.db, payload)

    def test_short_link_to_dropbox_normalizes_redirect_and_remembers_pdf_requirement(self):
        start = 'https://example.org/short'
        shared = 'https://dropbox.com/s/id/book.pdf?dl=0'
        direct = 'https://dropbox.com/s/id/book.pdf?dl=1'
        final = 'https://dl.dropboxusercontent.com/content'
        responses = {start: (302, 'text/plain', b'short link', shared),
                     direct: (302, 'text/plain', b'download', final),
                     final: (200, 'application/binary', b'%PDF-1.7\nSynthetic PDF', None)}
        payload = retrieve(self.db, self.token, start, responses.__getitem__)
        self.assertTrue(payload['pdf_download'])
        self.assertEqual(payload['url'], start)
        with patch('x_curator.pdf_reader.extract', side_effect=lambda db, data: dict(data, kind='text', text='Complete synthetic PDF text.')) as reader:
            extract(self.db, payload)
        reader.assert_called_once_with(self.db, payload)
        responses[final] = (200, 'text/html', b'<p>Please sign in to see the document.</p>', None)
        with self.assertRaisesRegex(ValueError, 'PDF response'):
            retrieve(self.db, self.token, start, responses.__getitem__)
        urls = [r[0] for r in self.db.execute('SELECT url FROM retrievals ORDER BY started')]
        self.assertEqual(urls, [start, direct, final] * 2)

    def test_retry_reacquires_old_preview_capture_and_retains_its_history(self):
        url = 'https://dropbox.com/s/id/book.pdf?dl=0'
        status, mime, sha, _ = request(self.db, self.token, url,
                                      lambda _: (200, 'text/html', b'<p>Synthetic preview text with no document contents.</p>', None))
        old = dict(url=url, final_url=url, mime=mime, body_sha=sha, fetched=time.time(),
                   kind='text', text='Synthetic preview text with no document contents.')
        identity = save_capture(self.db, self.token, old)
        fail_owned(self.db, self.token, 'retry after reader fix', 0)
        token = claim(self.db, Client.account)['token']
        capture_selection(self.db, token)
        calls = []
        def fetch(target):
            calls.append(target)
            return 200, 'application/binary', b'%PDF-1.7\nSynthetic new PDF', None
        with patch('x_curator.pdf_reader.extract', side_effect=lambda db, data: dict(data, kind='text', text='Complete newly acquired PDF text.')):
            acquire_urls(self.db, token, {url}, fetch)
        self.assertEqual(calls, ['https://dropbox.com/s/id/book.pdf?dl=1'])
        self.assertIsNotNone(self.db.execute('SELECT id FROM captures WHERE id=?', (identity,)).fetchone())
        new = next(c for c in bundle(self.db, token)['captures'].values() if c.get('pdf_download'))
        self.assertNotEqual(new['body_sha'], sha)
        self.assertNotIn('reused_from', new)
        self.assertIsNone(dropbox.reusable(dict(old, url='https://example.org/short')))
