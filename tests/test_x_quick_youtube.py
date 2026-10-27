from unittest.mock import patch

from x_fixtures import Client, CollectionCase, collect, envelope, tweet_entry
from x_quick_fixtures import native
from x_curator import native_search, quick_mcp, quick_web
from x_curator.worker import work


class QuickYouTubeTests(CollectionCase):
    def test_watch_page_never_poisons_quick_evidence_or_blocks_native_check(self):
        url = 'https://www.youtube.com/watch?v=abcdefghijk'
        entry = tweet_entry('1')
        entry['content']['itemContent']['tweet_results']['result']['legacy'] = {
            'full_text': 'I recommend this posture.',
            'entities': {'urls': [{'expanded_url': url}]}}
        collect(self.db, Client([(200, envelope([{'type': 'TimelineAddEntries', 'entries': [entry]}]))]), 'likes', delay=0)
        self.token = None

        def runner(_db, token):
            self.token = token
            return checker

        def checker(request):
            self.assertEqual(request['search_mode'], native_search.MODE)
            self.assertNotIn('linked', request)
            with self.assertRaisesRegex(ValueError, 'HTML/plain text'):
                quick_web.read(self.db, self.token, url)
            capture = next(k for k, c in request['bundle']['captures'].items() if c['kind'] == 'selection')
            decision = {'format': 'compact-v1', 'outcome': 'supported', 'reason': 'Attributed recommendation only.',
                        'claims': [{'text': 'I recommend this posture.', 'kind': 'recommendation',
                                    'attribution': 'Liked post author', 'status': 'subjective',
                                    'limitations': ['No video content was reviewed.'],
                                    'sources': [{'capture': capture, 'quote': 'I recommend this posture.',
                                                 'primary': False, 'credible': False, 'origin': 'Liked post author',
                                                 'reason': 'Captured recommendation, not factual video evidence.'}]}]}
            validation = quick_mcp.call(self.db, self.token, 'validate', {'decision': decision})
            self.assertFalse(validation['isError'])
            return native(request, decision, [validation])

        with patch('x_curator.quick_web.fetch') as fetch, patch('x_curator.quick_process.runner', runner):
            result = work(self.db, self.root, Client([]), max_items=1, defer_index=True)
        fetch.assert_not_called()
        self.assertEqual(result['completed'], 1)
        self.assertEqual(self.db.execute('SELECT count(*) FROM captures').fetchone()[0], 2)
        self.assertEqual(self.db.execute('SELECT count(*) FROM executions').fetchone()[0], 1)
        self.assertEqual(self.db.execute('SELECT count(*) FROM research_permissions').fetchone()[0], 0)
