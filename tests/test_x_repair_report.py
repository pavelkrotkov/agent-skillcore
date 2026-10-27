from x_repair_fixtures import QualificationCase
import test_x_retrieval_triage
from unittest.mock import patch

import repair_dispatch
import repair_manifest
from x_fixtures import Client


class RepairReportTests(QualificationCase):
    def test_valid_inconclusive_answer_after_failed_retrieval_is_reported_as_operational(self):
        manifest = self.manifest()
        self.checker = lambda request: test_x_retrieval_triage.RetrievalTriageTests.checker(self, request)
        self.fetch = lambda url: (403, 'text/html', b'Forbidden', None)
        with patch('x_curator.quick_web.fetch', self.fetch), patch('x_curator.quick_process.runner', self.model):
            result = repair_dispatch.run(self.db, self.root, Client([]), manifest, repair_manifest.identity(manifest))
        item = result['results'][0]
        self.assertEqual(item['outcome'], 'inconclusive')
        self.assertIsNotNone(item['execution'])
        self.assertEqual(item['disposition'], 'failed_processing')
        self.assertIn('HTTP 403', item['retrieval_failures'][0])
