from x_reading_fixtures import ReadingCase
from x_curator.publication_audit import audit
from x_curator.verdicts import validate_approval
from x_curator.evidence import current_bundle


class ReadingPublicationTests(ReadingCase):
    def test_published_source_preserves_all_approved_claims_and_transitive_readback(self):
        identity = self.publish_reading()
        row = self.db.execute('SELECT * FROM publications WHERE id=?', (identity,)).fetchone()
        job = self.db.execute('SELECT * FROM jobs').fetchone()
        packet, _ = validate_approval(self.db, self.token, row['proposal'], row['review'], current_bundle(self.db, job, self.token))
        segments = [r for r in self.calls if r['role'] == 'research' and r['reading']['stage'] == 'segment']
        self.assertEqual(len(packet['claims']), sum(len(r['bundle']['captures']) for r in segments))
        self.assertEqual(len({c['id'] for c in packet['claims']}), sum(len(r['bundle']['captures']) for r in segments))
        self.assertEqual(audit(self.db, self.root), [])
        self.assertEqual(job['state'], 'published')

    def test_missing_segment_receipt_invalidates_a_previously_published_page(self):
        identity = self.publish_reading()
        with self.db:
            self.db.execute("UPDATE executions SET finished=NULL WHERE role LIKE 'read:%' AND id=(SELECT id FROM executions WHERE role LIKE 'read:%' LIMIT 1)")
        self.assertEqual(audit(self.db, self.root), [identity])
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'retry')

    def test_interrupted_segment_cannot_publish_or_reset_attempts(self):
        def stopped(_):
            raise RuntimeError('synthetic interruption')
        self.model = stopped
        with self.assertRaises(RuntimeError):
            self.publish_reading()
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)
        self.assertEqual(self.db.execute('SELECT attempts FROM jobs').fetchone()[0], 1)
