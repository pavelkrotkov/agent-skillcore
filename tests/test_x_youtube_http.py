import socket
from unittest.mock import patch

from yt_dlp.networking import Request

from x_publication_fixtures import PublicationCase
from x_curator import http_receipts, public_http
from x_curator.youtube_http import open_request
from x_curator.youtube_ranges import acquire


class YoutubeHttpTests(PublicationCase):
    def test_post_redirect_is_accounted_and_private_destination_is_rejected(self):
        request = Request('https://www.youtube.com/player', data=b'{}', headers={'Content-Type': 'application/json'})
        def exchange(url, method, body, headers, limit):
            if url.endswith('/player'):
                return 302, [('Location', 'http://127.0.0.1/private')], b'redirect'
            self.assertEqual((method, body), ('GET', None))
            self.assertNotIn('Content-Type', headers)
            return public_http.transmit(url, method, body, headers, limit)
        private = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 80))]
        with patch('x_curator.public_http.exchange', side_effect=exchange), \
                patch('x_curator.public_http.socket.getaddrinfo', return_value=private):
            with self.assertRaisesRegex(ValueError, 'private or reserved'):
                open_request(self.db, self.token, request, [])
        rows = self.db.execute('SELECT status,error FROM retrievals ORDER BY started').fetchall()
        self.assertEqual([tuple(row) for row in rows], [(302, None), (None, 'ValueError')])

    def test_interrupted_exchange_retains_request_and_reservation(self):
        with patch('x_curator.public_http.exchange', side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):
                http_receipts.request(self.db, self.token, 'https://example.org/media')
        row = self.db.execute('SELECT r.error,d.request_sha,d.response_sha FROM retrievals r JOIN http_details d ON d.id=r.id').fetchone()
        self.assertEqual((row['error'], row['response_sha']), ('TimeoutError', None))
        self.assertEqual(len(row['request_sha']), 64)

    def test_range_failure_keeps_raw_response_and_credentials_never_leave(self):
        value = dict(format_id='134', url='https://synthetic.googlevideo.com/video', filesize=7)
        with patch('x_curator.public_http.exchange', return_value=(200, [], b'no range')):
            with self.assertRaisesRegex(ValueError, 'interval'):
                acquire(self.db, self.token, value)
        self.assertEqual(self.db.execute('SELECT status FROM retrievals').fetchone()[0], 200)
        for header in ('Cookie', 'Authorization', 'Host', 'Content-Length'):
            with self.subTest(header=header), patch('x_curator.public_http.destination') as destination:
                with self.assertRaisesRegex(ValueError, 'credential headers'):
                    public_http.exchange('https://example.org/', headers={header: 'synthetic'})
                destination.assert_not_called()
