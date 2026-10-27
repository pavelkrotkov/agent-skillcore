from x_pdf_fixtures import PdfCase
from x_curator.publication_audit import audit
from x_curator.wiki_sources import sources
from x_curator.wiki_render import render


class PdfPublicationTests(PdfCase):
    def test_pdf_publication_audits_all_page_coverage_proofs_pixels_and_readback(self):
        identity = self.publish_reading()
        current = sources(self.db, self.root)
        packet = current[identity]['packet']
        coverage = next(item for item in packet['coverage'] if item['capture'] == self.pdf)
        self.assertEqual([p['number'] for p in coverage['pages']], [1, 2, 3, 4])
        body = self.db.execute('SELECT body FROM publications WHERE id=?', (identity,)).fetchone()[0]
        self.assertIn(b'PDF physical pages', body)
        self.assertIn(b'#page=', render(current, {})['sources/' + identity + '.md'])
        self.assertEqual(audit(self.db, self.root), [])
        (self.root / 'blobs' / self.pdf_capture['pages'][1]['image']).write_bytes(b'damaged original page')
        self.assertEqual(audit(self.db, self.root), [identity])
