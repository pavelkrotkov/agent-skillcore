from copy import deepcopy

from x_reading_fixtures import ReadingCase
from x_curator import reading_aggregate
from x_curator.evidence import current_bundle
from x_curator.publication_audit import audit
from x_curator.receipts import digest
from x_curator.verdicts import validate_approval
from x_curator.worker_prompts import prompt


class ReadingCompositionTests(ReadingCase):
    def test_citation_heavy_packet_fits_composition_without_mutating_canonical_evidence(self):
        packet = deepcopy(self.packet)
        packet['claims'][0]['citations'][0]['quote'] = 'Original quotation. ' * 60000
        before = deepcopy(packet)
        evidence = {'account': 'synthetic', 'source': '1', 'captures': {}}
        header = {key: packet[key] for key in ('title', 'summary')}
        for role in ('research', 'review'):
            request = reading_aggregate.request(evidence, {}, [], packet, role, header if role == 'review' else None)
            self.assertLess(len(prompt(request)), 1000000)
            request['bundle']['approved_segment_claims'] = packet
            with self.assertRaises(ValueError):
                prompt(request)
        self.assertEqual(packet, before)

    def test_published_packet_keeps_exact_citations_absent_from_composition_view(self):
        identity = self.publish_reading()
        row = self.db.execute('SELECT * FROM publications WHERE id=?', (identity,)).fetchone()
        job = self.db.execute('SELECT * FROM jobs').fetchone()
        packet, _ = validate_approval(self.db, self.token, row['proposal'], row['review'], current_bundle(self.db, job, self.token))
        for claim in packet['claims']:
            self.assertTrue(claim['citations'][0]['quote'])
        for request in self.calls:
            if request['reading']['stage'] == 'composition':
                projected = request['bundle']['approved_segment_claims']['claims']
                self.assertEqual(projected, [{k: v for k, v in c.items() if k != 'citations'} for c in packet['claims']])
        self.assertEqual(audit(self.db, self.root), [])

    def test_changed_composition_qualifications_cannot_reuse_approval(self):
        identity = self.publish_reading()
        row, request, output = self.receipt('research')
        request['bundle']['approved_segment_claims']['claims'][0]['limitations'].append('Changed qualification.')
        request['bundle_sha'] = digest(request['bundle'])
        self.replace_receipt(row['id'], request, output)
        self.assertEqual(audit(self.db, self.root), [identity])
