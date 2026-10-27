from x_publication_fixtures import PublicationCase
from unittest.mock import patch

from x_curator import publication_audit, publication_diagnostics
from x_curator.publication import publish
from x_curator.storage import sha256
from x_curator.verification_details import image_mismatch


class AuditDetailBoundsTests(PublicationCase):
    def test_both_image_hashes_survive_private_invalidation_with_process_context(self):
        identity = publish(self.db, self.root, self.token, *self.approved_executions())
        actual, expected = sha256(b'changed'), sha256(b'original')
        detail = image_mismatch([actual], [expected], 'x-curator-input-proof-v2')
        message = 'model image bytes differ from acquired attachments; ' + detail
        with patch('x_curator.publication_audit.verify_publication', side_effect=ValueError(message)):
            self.assertEqual(publication_audit.audit(self.db, self.root), [identity])
        result = publication_diagnostics.diagnose(self.root, identity)
        error = result['failures'][0]['error']
        self.assertEqual(result['state'], 'invalid')
        self.assertLessEqual(len(error), 300)
        for retained in ('pid=', 'code=', 'version=v2', actual, expected):
            self.assertIn(retained, error)
