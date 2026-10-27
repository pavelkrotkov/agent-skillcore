from unittest import TestCase

from x_curator.youtube_urls import video_id
from x_curator.http_ranges import validate, validator


class RangeTests(TestCase):
    def test_representation_changes_and_ambiguous_headers_fail_closed(self):
        headers = [('Content-Range', 'bytes 0-6/7'), ('Content-Length', '7'), ('ETag', '"one"')]
        self.assertEqual(validate(dict(status=206, headers=headers), 0, 7, None), ['etag', '"one"'])
        for response in (dict(status=200, headers=headers), dict(status=206, headers=headers + [('ETag', '"two"')]),
                         dict(status=206, headers=headers + [('Content-Encoding', 'gzip')])):
            with self.subTest(response=response), self.assertRaises(ValueError):
                validate(response, 0, 7, None)
        with self.assertRaisesRegex(ValueError, 'changed'):
            validate(dict(status=206, headers=headers), 0, 7, ['etag', '"other"'])

    def test_only_strong_validators_allow_byte_assembly(self):
        for value in ('W/"one"', '"one", "two"', 'one'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validator([('ETag', value)])
        old = ('Last-Modified', 'Fri, 26 Jan 2024 09:37:25 GMT')
        later = ('Date', 'Fri, 26 Jan 2024 09:39:25 GMT')
        self.assertEqual(validator([old, later]), ['last-modified', old[1]])
        with self.assertRaisesRegex(ValueError, 'recent'):
            validator([old, ('Date', old[1])])

    def test_single_video_references_cannot_be_channels_or_ambiguous_watch_urls(self):
        self.assertEqual(video_id('https://youtu.be/Synthetic_1?t=2'), 'Synthetic_1')
        self.assertIsNone(video_id('https://example.org/Synthetic_1'))
        for url in ('https://www.youtube.com/playlist?list=synthetic', 'https://user@youtu.be/Synthetic_1',
                    'https://www.youtube.com/channel/Synthetic_1', 'https://www.youtube.com/watch?v=Synthetic_1&v=Synthetic_2'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                video_id(url)
