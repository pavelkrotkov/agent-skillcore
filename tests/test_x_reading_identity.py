from copy import deepcopy

from x_reading_fixtures import ReadingCase
from x_curator import reading_citations, reading_packets, reading_plan, reading_views
from x_curator.evidence import bundle
from x_curator.publication_audit import audit


class ReadingIdentityTests(ReadingCase):
    def test_controller_identity_preserves_raw_output_and_historical_canonical_packet(self):
        evidence = bundle(self.db, self.token)
        request = reading_views.request(evidence, reading_plan.plan(evidence), 0, 'research')
        original = dict(self.segment(request), source=request['bundle']['source'], bundle_sha=request['bundle_sha'])
        expected = reading_citations.materialize(original, request['bundle'])
        for fields in ({}, {'source': 'foreign', 'bundle_sha': request['reading']['plan_sha']}):
            raw = {key: value for key, value in original.items() if key not in ('source', 'bundle_sha')} | fields
            before = deepcopy(raw)
            canonical = reading_citations.materialize(raw, request['bundle'])
            reading_packets.validate(canonical, request['bundle'])
            self.assertEqual(canonical, expected)
            self.assertEqual(raw, before)

    def test_authenticated_foreign_segment_view_cannot_reuse_approval(self):
        from x_curator.receipts import digest
        identity = self.publish_reading()
        _, composition, _ = self.receipt('research')
        proposal = composition['reading']['receipts'][0]['proposal']
        role = self.db.execute('SELECT role FROM executions WHERE id=?', (proposal,)).fetchone()[0]
        row, request, output = self.receipt(role)
        request['bundle']['source'] = 'foreign-source'
        request['bundle_sha'] = digest(request['bundle'])
        self.replace_receipt(row['id'], request, output)
        self.assertEqual(audit(self.db, self.root), [identity])
