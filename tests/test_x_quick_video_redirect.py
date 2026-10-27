import time
from unittest.mock import patch

from x_publication_fixtures import PublicationCase
from x_curator import native_search, quick_linked, quick_sources, quick_store, quick_web
from x_curator.evidence import bundle


class QuickVideoRedirectTests(PublicationCase):
    def test_video_redirect_does_not_leave_invalid_evidence(self):
        quick_store.start(self.db, self.token, time.time())
        url = 'https://example.org/short'
        video = 'https://www.youtube.com/watch?v=abcdefghijk'
        identity = quick_sources.source(self.db, self.token, url)
        responses = [(302, 'text/plain', b'redirect', video),
                     (200, 'text/html', b'<p>Watch page metadata.</p>', None)]
        with patch('x_curator.quick_web.fetch', side_effect=responses):
            with self.assertRaisesRegex(ValueError, 'HTML/plain text'):
                quick_web.read(self.db, self.token, identity)
        self.assertEqual(bundle(self.db, self.token), self.evidence)
        self.assertEqual(self.db.execute('SELECT count(*) FROM captures').fetchone()[0], 1)
        self.assertEqual(self.db.execute('SELECT count(*) FROM retrievals').fetchone()[0], 2)

    def test_shortened_video_link_leaves_native_check_available(self):
        check = quick_store.start(self.db, self.token, time.time())
        alias = 'https://example.org/short'
        video = 'https://www.youtube.com/watch?v=abcdefghijk'
        selection = next(iter(self.evidence['captures'].values()))
        responses = [(302, 'text/plain', b'redirect', video),
                     (200, 'text/html', b'<p>Watch page metadata.</p>', None)]
        with patch('x_curator.quick_linked.links', return_value=[alias]), \
                patch('x_curator.quick_web.fetch', side_effect=responses):
            linked = quick_linked.capture(self.db, self.token, selection)
        self.assertIsNone(linked)
        self.assertEqual(bundle(self.db, self.token), self.evidence)
        request = quick_linked.request(self.db, self.token, check, self.evidence, native_search.MODE)
        self.assertEqual(request['search_mode'], native_search.MODE)
        self.assertNotIn('linked', request)
