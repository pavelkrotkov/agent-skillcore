
from x_publication_fixtures import PublicationCase
from x_curator.acquire import acquire_urls
from x_curator.evidence import bundle


from x_thread_fixtures import ROOT, MEDIA, fetch


class ThreadScopeTests(PublicationCase):
    def test_selected_thread_expands_but_foreign_context_keeps_only_direct_dependencies(self):
        acquire_urls(self.db, self.token, {ROOT, MEDIA}, fetch)
        captures = bundle(self.db, self.token)['captures'].values()
        urls = {c['url'] for c in captures if c['kind'] != 'selection'}
        self.assertEqual(urls, {ROOT, MEDIA, 'https://x.com/i/status/2', 'https://x.com/i/status/3', 'https://x.com/i/status/5'})
        details = [c for c in captures if c['kind'] == 'x_detail']
        self.assertTrue(all(c['thread_scope'] == ['a', '1'] for c in details))
        self.assertIn('Foreign surrounding', details[0]['limitations'][0])

    def test_foreign_direct_dependency_failure_still_blocks_acquisition(self):
        def missing(url):
            if url == MEDIA:
                return 404, 'text/plain', b'Unavailable', None
            return fetch(url)
        with self.assertRaises(ValueError):
            acquire_urls(self.db, self.token, {ROOT}, missing)
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)
