from copy import deepcopy

from x_pdf_fixtures import PdfCase
from x_curator import reading_plan, reading_views, reading_work
from x_curator.evidence import bundle
from x_curator.media_inputs import identities
from x_curator.pdf_schema import validate


class PdfPlanTests(PdfCase):
    def test_all_physical_pages_and_pixels_are_assigned_once_with_mixed_evidence(self):
        evidence = bundle(self.db, self.token)
        self.assertTrue(reading_work.required(evidence))
        plan = reading_plan.plan(evidence)
        self.assertEqual(plan['version'], 2)
        observed = []
        for index in range(len(plan['parts'])):
            view = reading_views.view(evidence, plan, index)
            self.assertLessEqual(len(identities(view)), 2)
            positions = {sha: number for number, sha in enumerate(sorted(identities(view)), 1)}
            for capture in view['captures'].values():
                for page in capture.get('pages', []):
                    observed.append(page['number'])
                    self.assertEqual(page['attachment'], positions[page['image']])
        self.assertEqual(sorted(observed), [1, 2, 3, 4])
        self.assertEqual(len(self.pdf_capture['images']), 3)
        self.assertNotIn('attachment', evidence['captures'][self.pdf]['pages'][0])

    def test_page_identity_offset_and_provenance_changes_reject(self):
        variants = [deepcopy(self.pdf_capture) for _ in range(4)]
        variants[0]['pages'][0]['number'] = 2
        variants[1]['pages'][1]['start'] += 1
        variants[2]['pdf']['render_flags'] = ['-scale-to', '100']
        variants[3]['images'].pop()
        for capture in variants:
            with self.assertRaises(ValueError):
                validate(capture)

    def test_empty_inventory_is_rejected_before_page_slicing(self):
        from x_curator.pdf_ranges import split
        capture = dict(self.pdf_capture, pages=[])
        with self.assertRaisesRegex(ValueError, 'pages or image inventory'):
            list(split(capture, 1000, 2))

    def test_ambiguous_formfeed_boundaries_cannot_assign_physical_pages(self):
        from x_curator.pdf_pages import intervals
        for text, count in (('missing delimiter', 1), ('\fextra', 1), ('\f', 2)):
            with self.assertRaises(ValueError):
                list(intervals(text, count))
