from x_linked_fixtures import LinkedCase
from unittest.mock import patch
from x_curator.quick_failures import MEDIA_REFUSAL


class QuickPrefetchFailureTests(LinkedCase):
    def test_dead_link_does_not_block_attributed_content_or_manufacture_body_proof(self):
        def unavailable(_url):
            if _url.endswith('/short-video'):
                raise ValueError(MEDIA_REFUSAL)
            raise OSError('synthetic DNS failure')
        self.fetch = unavailable
        def subjective(request):
            capture = next(k for k, c in request['bundle']['captures'].items() if c['kind'] == 'selection')
            claim = self.source(capture, 'I recommend the tool.', 'subjective', False)
            claim.update(kind='recommendation', attribution='Liked post author')
            return dict(format='compact-v1', outcome='supported', reason='Attributed recommendation.', claims=[claim])
        self.decision = subjective
        with patch('x_curator.quick_linked.links', return_value=self.urls + ['https://example.test/short-video']):
            self.assertEqual(self.run_worker()['completed'], 1)
        self.assertIn('synthetic DNS failure', self.db.execute('SELECT body FROM publications').fetchone()[0].decode())
        self.assertEqual(self.db.execute('SELECT count(*) FROM executions').fetchone()[0], 1)
        self.assertEqual(self.db.execute('SELECT count(*) FROM research_permissions').fetchone()[0], 0)

    def test_dead_link_does_not_make_its_metadata_factual_body_evidence(self):
        self.fetch = lambda _url: (_ for _ in ()).throw(OSError('synthetic DNS failure'))
        def unsupported(request):
            capture = next(k for k, c in request['bundle']['captures'].items() if c['kind'] == 'unavailable')
            return dict(format='compact-v1', outcome='supported', reason='Invalid fact.',
                        claims=[self.source(capture, 'The tool was released in 2025.')])
        self.decision = unsupported
        self.assertEqual(self.run_worker()['completed'], 0)
        self.assertTrue(self.validation['isError'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)
