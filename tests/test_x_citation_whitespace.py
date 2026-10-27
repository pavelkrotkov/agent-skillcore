from copy import deepcopy
import unittest

from x_curator.claim_validation import validate_citation


class CitationWhitespaceTests(unittest.TestCase):
    def test_html_spacing_is_accepted_without_rewriting_authentic_evidence(self):
        capture = {'kind': 'text', 'text': 'At the exit, pressure is 25 psi. In the\nburner\nair ignites.'}
        citation = {'capture': 'selected', 'quote': 'pressure is 25 psi. In the burner air ignites.'}
        original = deepcopy((capture, citation))
        validate_citation(citation, capture)
        self.assertEqual((capture, citation), original)

    def test_changes_beyond_whitespace_or_from_another_capture_are_rejected(self):
        selected = {'kind': 'text', 'text': 'Fuel is 2 pounds/sec; air is 100 pounds/sec.'}
        quotes = ('Fuel is 20 pounds/sec;', 'fuel is 2 pounds/sec;',
                  'Fuel is 2 pounds/sec,', 'Fuel is 2pounds/sec;', 'Fuel is 2 pounds/sec; steam is hot.')
        for quote in quotes:
            with self.subTest(quote=quote), self.assertRaisesRegex(ValueError, 'excerpt is absent'):
                validate_citation({'quote': quote}, selected)

    def test_unicode_and_repeated_whitespace_preserve_all_nonwhitespace_characters(self):
        capture = {'kind': 'text', 'text': 'The\tcompressor\u00a0\nraises  pressure (25 psi).'}
        validate_citation({'quote': 'The compressor raises pressure (25 psi).'}, capture)
        with self.assertRaisesRegex(ValueError, 'excerpt is absent'):
            validate_citation({'quote': 'The compressor raises pressure [25 psi].'}, capture)
