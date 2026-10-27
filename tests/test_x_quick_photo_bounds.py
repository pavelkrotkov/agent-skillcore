from x_quick_fixtures import QuickCase
from x_curator import quick_photos
from x_curator.quick_photo_scope import bounded_urls


class QuickPhotoBoundsTests(QuickCase):
    def test_selected_post_media_is_never_silently_truncated(self):
        media = [{'type': 'photo', 'media_url_https': f'https://example.test/{n}'} for n in range(33)]
        focal = dict(rest_id='1', legacy=dict(extended_entities=dict(media=media)))
        with self.assertRaisesRegex(ValueError, 'selected-post photos'):
            bounded_urls([focal], '1')

    def test_oversized_photo_is_stopped_by_the_actual_bounded_transport(self):
        with self.transport(b'x' * (quick_photos.MAX_BYTES + 2)) as response:
            with self.assertRaisesRegex(ValueError, 'byte budget'):
                quick_photos.fetch('https://example.test/large')
            response.read.assert_called_once_with(quick_photos.MAX_BYTES + 1)
