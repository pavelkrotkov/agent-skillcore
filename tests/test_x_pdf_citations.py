from copy import deepcopy

from x_pdf_fixtures import PdfCase
from x_curator import reading_citations, reading_plan, reading_views
from x_curator.claim_validation import validate_citation
from x_curator.evidence import bundle
from x_curator.pdf_coverage import validate as validate_coverage


class PdfCitationTests(PdfCase):
    def test_cross_page_quote_and_visual_observation_bind_exact_original_pages(self):
        evidence = bundle(self.db, self.token)
        plan = reading_plan.plan(evidence)
        index = next(i for i, spans in enumerate(plan['parts']) if any(s['capture'] == self.pdf for s in spans))
        view = reading_views.view(evidence, plan, index)
        capture = view['captures'][self.pdf]
        keys = sorted(capture['text_lines'])
        raw = dict(capture=self.pdf, line_start=keys[0], line_end=keys[-1])
        cite = reading_citations.citation(raw, view)
        validate_citation(cite, self.pdf_capture)
        self.assertEqual(cite['pdf_pages'], [1, 2])
        changed = dict(cite, pdf_pages=[3, 4])
        with self.assertRaisesRegex(ValueError, 'page reference'):
            validate_citation(changed, self.pdf_capture)
        visual = reading_citations.citation(dict(capture=self.pdf, quote='', page=2, observation='Observed synthetic page pixels.'), view)
        validate_citation(visual, self.pdf_capture)
        with self.assertRaises(ValueError):
            validate_citation(dict(visual, pdf_image='foreign'), self.pdf_capture)

    def test_missing_duplicate_foreign_and_unreadable_page_coverage_rejects(self):
        coverage = {'pages': [dict(number=p['number'], status='reviewed', notes='Observed original pixels.') for p in self.pdf_capture['pages']]}
        variants = [deepcopy(coverage) for _ in range(4)]
        variants[0]['pages'].pop()
        variants[1]['pages'][1]['number'] = 1
        variants[2]['pages'][1]['number'] = 99
        variants[3]['pages'][1]['status'] = 'unreadable'
        for item in variants:
            with self.assertRaises(ValueError):
                validate_coverage(item, self.pdf_capture)
