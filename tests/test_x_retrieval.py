import socket
from unittest.mock import patch

from x_publication_fixtures import PublicationCase
from x_curator.public_http import destination
from x_curator.retrievals import request, retrieve


class RetrievalTests(PublicationCase):
    def test_private_destinations_and_embedded_credentials_are_rejected(self):
        private = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]
        with patch("x_curator.public_http.socket.getaddrinfo", return_value=private):
            with self.assertRaisesRegex(ValueError, "private or reserved"):
                destination("https://example.org/source")
        with self.assertRaisesRegex(ValueError, "credential-bearing"):
            destination("https://synthetic:password@example.org/source")

    def test_requests_and_redirects_consume_a_lifetime_budget(self):
        responses = iter([(302, "text/plain", b"redirect", "/source"), (200, "text/plain", b"Source body", None)])
        result = retrieve(self.db, self.token, "https://example.org/start", lambda _: next(responses))
        self.assertEqual(result["final_url"], "https://example.org/source")
        for _ in range(38):
            request(self.db, self.token, "https://example.org/source", lambda _: (200, "text/plain", b"Source body", None))
        with self.assertRaisesRegex(ValueError, "lifetime"):
            request(self.db, self.token, "https://example.org/source", lambda _: self.fail("must not fetch"))
        self.assertEqual(self.db.execute("SELECT count(*) FROM retrievals").fetchone()[0], 40)

    def test_failed_request_is_reserved_and_keeps_failure_receipt(self):
        def failed(_):
            raise TimeoutError("synthetic timeout")
        with self.assertRaises(TimeoutError):
            request(self.db, self.token, "https://example.org/source", failed)
        row = self.db.execute("SELECT error,status,finished FROM retrievals").fetchone()
        self.assertEqual((row[0], row[1]), ("TimeoutError", None))
        self.assertIsNotNone(row[2])
