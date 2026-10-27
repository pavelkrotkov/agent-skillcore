from x_publication_fixtures import PublicationCase
from x_curator import blobs
from x_curator.readers import extract
from x_curator.coverage import validate_item
from x_curator.claim_validation import validate_citation


class HTMLMetadataTests(PublicationCase):
    def capture(self, body):
        return extract(self.db, {'url': 'https://example.org/invite', 'mime': 'text/html',
                                 'body_sha': blobs.put(self.db, body)})

    def test_sparse_body_retains_actual_metadata_and_enforces_partial_coverage(self):
        body = b'<head><title>Join the Synthetic Research Community Today</title><meta name="description" content="Synthetic public community invitation"></head><script>unread private messages</script>'
        capture = self.capture(body)
        self.assertEqual(capture['kind'], 'metadata')
        self.assertEqual(blobs.read(self.db, capture['body_sha']), body)
        self.assertNotIn('private messages', capture['text'])
        self.assertNotIn('Today', capture['text'])
        item = {'status': 'metadata_only', 'notes': 'Only the invitation description is visible.'}
        validate_item(item, capture, capture['limitations'])
        with self.assertRaisesRegex(ValueError, 'unread-body limitation'):
            validate_item(item, capture, [])
        with self.assertRaisesRegex(ValueError, 'unresolved evidence'):
            validate_item(dict(item, status='covered'), capture, capture['limitations'])
        validate_citation({'quote': 'Synthetic public community invitation'}, capture)
        with self.assertRaisesRegex(ValueError, 'absent'):
            validate_citation({'quote': 'unread private messages'}, capture)

    def test_real_body_remains_readable_and_empty_shell_is_not_evidence(self):
        capture = self.capture(b'<head><title>Promotional claim</title><meta property="og:title" content="Promotional claim"><body><p>Actual readable body with enough original text.</p>')
        self.assertEqual(capture['kind'], 'text')
        self.assertNotIn('Promotional claim', capture['text'])
        with self.assertRaisesRegex(ValueError, 'format requires a reader'):
            extract(self.db, dict(capture, mime='application/not-html'))
        with self.assertRaisesRegex(ValueError, 'unavailable or too sparse'):
            self.capture(b'<title>A long title cannot stand in for an unreadable page body</title><script>hidden application code</script>')
