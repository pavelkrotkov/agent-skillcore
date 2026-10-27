from test_x_media_inputs import png
from x_quick_photo_fixtures import PhotoCase
from x_curator.publication_audit import audit


class QuickPhotoTests(PhotoCase):
    def test_oversized_thread_preserves_selected_photos_and_records_uninspected_scope(self):
        self.images.update({f'https://example.test/{n}.png': png(n) for n in range(40)})
        media = [{'type': 'photo', 'media_url_https': url} for url in self.images]
        self.posts[1]['legacy']['extended_entities']['media'] = media
        selected = self.posts[0]['legacy']['extended_entities']['media'][0]['media_url_https']
        self.assertEqual(self.run_worker()['completed'], 1)
        images = [c for c in self.request['bundle']['captures'].values() if c['kind'] == 'image']
        self.assertEqual(len(images), 32)
        self.assertIn(selected, {c['url'] for c in images})
        self.assertEqual(len(self.images), 42)
        self.assertIn('10 thread photos were not inspected', str(self.request['bundle']['captures']))
        body = self.db.execute('SELECT body FROM publications').fetchone()[0].decode()
        self.assertIn('10 thread photos were not inspected', body)
        self.assertEqual(audit(self.db, self.root), [])

    def test_post_and_thread_photos_reach_native_input_and_publish_with_visual_attribution(self):
        self.assertEqual(self.run_worker()['completed'], 1)
        self.assertFalse(self.validation['isError'], self.validation)
        self.assertEqual(audit(self.db, self.root), [])
        self.assertEqual(self.db.execute('SELECT count(*) FROM retrievals').fetchone()[0], 3)
        self.assertEqual(self.db.execute('SELECT count(*) FROM research_permissions').fetchone()[0], 0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM executions').fetchone()[0], 1)

    def test_missing_native_pixels_prevent_publication(self):
        self.receipt_images = lambda _images: {}
        self.assertEqual(self.run_worker()['completed'], 0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)
        self.assertIn('image', self.db.execute('SELECT reason FROM quick_checks').fetchone()[0])

    def test_substituted_native_pixels_prevent_publication(self):
        self.receipt_images = lambda images: {sha: png(42) for sha in images}
        self.assertEqual(self.run_worker()['completed'], 0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)
        self.assertIn('image', self.db.execute('SELECT reason FROM quick_checks').fetchone()[0])

    def test_non_image_response_fails_before_model_or_deep_reader(self):
        self.exchange = lambda *_args, **_kwargs: (200, [('Content-Type', 'application/pdf')], b'%PDF-1.7')
        self.assertEqual(self.run_worker()['completed'], 0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM executions').fetchone()[0], 0)
        self.assertIn('not an image', self.db.execute('SELECT reason FROM quick_checks').fetchone()[0])
