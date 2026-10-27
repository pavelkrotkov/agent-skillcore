from x_publication_fixtures import PublicationCase
from x_curator import blobs, dropbox
from x_curator.retrievals import retrieve, request


class DropboxTests(PublicationCase):
    def test_download_retains_original_url_parameters_and_actual_redirect_receipts(self):
        original = 'https://www.dropbox.com/scl/fi/synthetic/book.pdf?rlkey=a%2Bb&st=marker&dl=0&raw=1#page=2'
        download = 'https://www.dropbox.com/scl/fi/synthetic/book.pdf?rlkey=a%2Bb&st=marker&dl=1#page=2'
        final = 'https://dl.dropboxusercontent.com/synthetic/book.pdf'
        body = b'%PDF-1.7\nSynthetic PDF bytes for retrieval only.'
        responses = {download: (302, 'text/html', b'redirect receipt', final), final: (200, 'application/pdf', body, None)}
        payload = retrieve(self.db, self.token, original, responses.__getitem__)
        self.assertEqual((payload['url'], payload['final_url']), (original, final))
        self.assertEqual(blobs.read(self.db, payload['body_sha']), body)
        rows = self.db.execute('SELECT url,status,body_sha FROM retrievals ORDER BY started').fetchall()
        self.assertEqual([(r['url'], r['status']) for r in rows], [(download, 302), (final, 200)])
        self.assertEqual(blobs.read(self.db, rows[0]['body_sha']), b'redirect receipt')
        self.assertEqual(dropbox.download_url('https://dropbox.com/s/id/a.PDF?empty=&dl=1&dl=0'),
                         'https://dropbox.com/s/id/a.PDF?empty=&dl=1')

    def test_only_exact_public_shared_pdf_paths_are_rewritten(self):
        urls = ['https://dropbox.com/scl/fo/folder', 'https://dropbox.com/s/id/image.png',
                'https://dropbox.com.evil.example/s/id/a.pdf', 'https://example.org/s/id/a.pdf',
                'https://user:pass@dropbox.com/s/id/a.pdf', 'http://dropbox.com/s/id/a.pdf']
        for url in urls:
            with self.subTest(url=url):
                self.assertIsNone(dropbox.download_url(url))

    def test_download_html_and_denials_are_retained_but_not_accepted_as_pdf(self):
        original = 'https://dropbox.com/s/id/a.pdf?dl=0'
        for status in (200, 403):
            with self.subTest(status=status):
                with self.assertRaises(ValueError):
                    retrieve(self.db, self.token, original, lambda _: (status, 'text/html', b'<p>Sign in to preview this file.</p>', None))
        with self.assertRaisesRegex(ValueError, 'PDF response'):
            retrieve(self.db, self.token, original, lambda _: (200, 'text/html', b'%PDF-spoofed HTML response', None))
        rows = self.db.execute('SELECT status,body_sha FROM retrievals ORDER BY started LIMIT 2').fetchall()
        self.assertEqual([r['status'] for r in rows], [200, 403])
        self.assertTrue(all(blobs.read(self.db, r['body_sha']).startswith(b'<p>') for r in rows))

    def test_download_redirect_cannot_exceed_lifetime_request_budget(self):
        for _ in range(39):
            request(self.db, self.token, 'https://example.org/source', lambda _: (200, 'text/plain', b'retained', None))
        calls = []
        def redirect(url):
            calls.append(url)
            return 302, 'text/html', b'redirect', 'https://dl.dropboxusercontent.com/file.pdf'
        with self.assertRaisesRegex(ValueError, 'lifetime'):
            retrieve(self.db, self.token, 'https://dropbox.com/s/id/a.pdf', redirect)
        self.assertEqual(calls, ['https://dropbox.com/s/id/a.pdf?dl=1'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM retrievals').fetchone()[0], 40)
