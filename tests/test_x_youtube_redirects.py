from unittest.mock import patch

from x_youtube_fixtures import YoutubeCase, URL
from x_curator.acquire import acquire, acquire_urls
from x_curator.coverage import require_acquisitions
from x_curator.evidence import current_bundle, save_capture


class YoutubeRedirectTests(YoutubeCase):
    def test_redirect_metadata_requires_authentic_video_and_rejects_old_html(self):
        responses = iter([(302, 'text/plain', b'redirect', URL), (200, 'text/html', b'<p>Video page metadata.</p>', None)])
        acquire(self.db, self.token, 'https://example.org/short', lambda _: next(responses))
        evidence = current_bundle(self.db, self.job, self.token)
        alias = next(c for c in evidence['captures'].values() if c['kind'] == 'metadata')
        self.assertEqual(alias['required_urls'], [URL])
        with self.assertRaisesRegex(ValueError, 'not been acquired'):
            require_acquisitions(evidence['captures'])
        video = self.acquire_video()
        save_capture(self.db, self.token, video)
        require_acquisitions(current_bundle(self.db, self.job, self.token)['captures'])
        save_capture(self.db, self.token, dict(alias, url=URL, final_url=URL, kind='text'))
        with self.assertRaisesRegex(ValueError, 'no authenticated media'):
            current_bundle(self.db, self.job, self.token)

    def test_cached_redirect_is_upgraded_and_transitive_acquisition_fetches_video(self):
        from x_curator.blobs import put
        old = dict(url='https://example.org/short', final_url=URL, mime='text/html', body_sha=put(self.db, b'old page'),
                   kind='text', text='Old page metadata only.', fetched=1)
        acquire(self.db, self.token, old['url'], lambda _: self.fail('reuse must not refetch page'), cached=old)
        video = self.acquire_video()
        with patch('x_curator.youtube.acquire', return_value=video) as adapter:
            acquire_urls(self.db, self.token, [], lambda _: self.fail('video uses the accounted adapter'))
        adapter.assert_called_once_with(self.db, self.token, URL)
        require_acquisitions(current_bundle(self.db, self.job, self.token)['captures'])
