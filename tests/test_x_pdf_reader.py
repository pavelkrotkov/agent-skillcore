from copy import deepcopy
from unittest.mock import patch

from x_pdf_fixtures import PdfCase, png
from x_curator.acquire import acquire
from x_curator.evidence import bundle
from x_curator.readers import extract


class PdfReaderTests(PdfCase):
    def output(self, args, seconds=30):
        if '-v' in args:
            body = (args[0] + ' version synthetic').encode()
        elif args[0] == 'pdfinfo':
            body = b'Pages: 2\n'
        elif args[0] == 'pdftotext':
            body = b'\f\f'
        else:
            body = png(b'actual mocked page output')
        return type('Result', (), {'stdout': body, 'stderr': b''})()

    def test_scanned_text_empty_pages_are_rendered_and_legacy_cache_is_reextracted(self):
        cached = dict(self.pdf_capture, kind='text', mime='application/binary', pdf_download=True,
                      final_url=self.pdf_capture['url'], fetched=123, reused_from='fresh-parent')
        cached.pop('pdf')
        original = deepcopy(cached)
        with patch('x_curator.pdf_reader.command', side_effect=self.output) as run:
            capture = extract(self.db, cached)
            identity = acquire(self.db, self.token, cached['url'], lambda _: self.fail('must reuse original fresh bytes'), cached)
        self.assertEqual(cached, original)
        self.assertEqual((capture['kind'], capture['mime'], capture['text'], len(capture['pages'])),
                         ('pdf', 'application/binary', '\f\f', 2))
        self.assertEqual(len(capture['images']), 1)
        self.assertEqual(bundle(self.db, self.token)['captures'][identity]['fetched'], 123)
        self.assertEqual(sum(call.args[0][0] == 'pdftoppm' and '-f' in call.args[0] for call in run.call_args_list), 4)

    def test_renderer_failure_never_makes_partial_captures(self):
        with patch('x_curator.pdf_reader.command', side_effect=TimeoutError('renderer failed')), self.assertRaises(TimeoutError):
            extract(self.db, self.pdf_capture)

    def test_missing_page_count_rejects_before_rendering(self):
        results = [self.output(['pdftotext']), type('Result', (), {'stdout': b'Title: Missing count\n'})()]
        with patch('x_curator.pdf_reader.command', side_effect=results) as run, self.assertRaisesRegex(ValueError, 'physical pages'):
            extract(self.db, self.pdf_capture)
        self.assertEqual(run.call_count, 2)
