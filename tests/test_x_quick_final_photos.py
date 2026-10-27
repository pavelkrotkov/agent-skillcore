import copy
from unittest.mock import patch
from x_quick_photo_fixtures import PhotoCase
from x_quick_fixtures import native
from x_curator import quick_mcp
from x_curator.publication_audit import audit
from x_curator.receipts import digest
from test_x_quick_final import FORMAT


class PhotoFinalTests(PhotoCase):
    def terminal(self, request, decision, responses, *, images):
        missing = copy.deepcopy(decision)
        del missing['claims'][0]['sources'][0]['observation']
        rejected = quick_mcp.call(self.db, self.token, 'validate', {'decision': missing})
        self.assertTrue(rejected['isError'])
        self.assertIn('nonempty observation required', rejected['content'][0]['text'])
        accepted = quick_mcp.call(self.db, self.token, 'validate', {'decision': decision})
        self.assertFalse(accepted['isError'])
        final = {'format': FORMAT, 'decision_sha': digest(decision)}
        return native(request, final, responses + [rejected, accepted], images=images)

    def test_visual_schema_correction_and_short_final_preserve_pixel_proof(self):
        with patch('x_quick_photo_fixtures.native', side_effect=self.terminal):
            self.assertEqual(self.run_worker()['completed'], 1)
        self.assertEqual(audit(self.db, self.root), [])
