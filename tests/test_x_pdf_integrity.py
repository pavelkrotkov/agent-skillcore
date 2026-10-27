from functools import partial
from unittest.mock import patch

from x_pdf_fixtures import PdfCase
from x_publication_fixtures import PublicationCase
from x_trace_fixtures import proof
from x_curator import blobs
from x_curator.publication import publish
from x_curator.publication_audit import audit


class PdfIntegrityTests(PdfCase):
    def test_unknown_visual_page_invalidates_publication_without_aborting_audit(self):
        identity = self.publish_reading()
        _, composition, _ = self.receipt('research')
        for pair in composition['reading']['receipts']:
            role = self.db.execute('SELECT role FROM executions WHERE id=?', (pair['proposal'],)).fetchone()[0]
            row, request, output = self.receipt(role)
            if self.pdf in request['bundle']['captures']:
                break
        output['claims'][0]['citations'] = [dict(capture=self.pdf, quote='', page=99, observation='Foreign page')]
        images = {sha: blobs.read(self.db, sha) for c in request['bundle']['captures'].values() for sha in c.get('images', [])}
        with patch('x_reading_fixtures.proof', partial(proof, images=images)):
            self.replace_receipt(row['id'], request, output)
        self.assertEqual(audit(self.db, self.root), [identity])
        self.assertEqual(self.db.execute('SELECT state FROM publications WHERE id=?', (identity,)).fetchone()[0], 'invalid')


class NonPdfProvenanceTests(PublicationCase):
    def test_ordinary_evidence_cannot_publish_fabricated_pdf_provenance(self):
        self.packet['claims'][0]['citations'][0].update(pdf_pages=[99], pdf_image='not-an-acquired-image')
        proposal, review = self.approved_executions()
        with self.assertRaisesRegex(ValueError, 'requires acquired PDF evidence'):
            publish(self.db, self.root, self.token, proposal, review)
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)
