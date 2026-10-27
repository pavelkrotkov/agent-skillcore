from x_deep_photo_fixtures import DeepPhotoCase
from x_curator.publication_audit import audit


class DeepPhotoTests(DeepPhotoCase):
    def test_selected_photo_reaches_approved_input_and_historical_pixel_proof(self):
        self.authorize()
        original = dict(self.db.execute('SELECT * FROM quick_checks').fetchone())
        self.assertEqual(self.deep()['state'], 'published')
        images = [c for c in self.request['bundle']['captures'].values() if c['kind'] == 'image']
        self.assertEqual([c['url'] for c in images], ['https://example.test/a.png'])
        self.assertEqual(audit(self.db, self.root), [])
        self.assertEqual(dict(self.db.execute('SELECT * FROM quick_checks').fetchone()), original)

    def test_missing_selected_pixels_rejects_approved_publication(self):
        self.authorize()
        self.receipt_images = lambda _images: {}
        self.assertEqual(self.deep()['state'], 'awaiting_review')
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)
        self.assertIsNotNone(self.db.execute('SELECT consumed FROM research_permissions').fetchone()[0])
