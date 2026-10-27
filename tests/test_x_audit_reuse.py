from unittest.mock import patch
import os
from marshal import dumps

from x_publication_fixtures import PublicationCase
from x_curator.publication import publish
from x_curator import publication_audit, wiki_inputs, audit_reuse
from x_curator.read_set import ReadSet, ChangedDependencies


class AuditReuseTests(PublicationCase):
    def setUp(self):
        super().setUp()
        proposal, review = self.approved_executions()
        self.publication = publish(self.db, self.root, self.token, proposal, review)

    def test_repeated_audit_reuses_heavy_proof_despite_unrelated_writes(self):
        with patch.object(publication_audit, 'validate_approval', wraps=publication_audit.validate_approval) as proof:
            first = wiki_inputs.sources(self.db, self.root)
            self.db.execute('CREATE TABLE unrelated_progress (value INTEGER)')
            self.db.execute('INSERT INTO unrelated_progress VALUES (1)')
            self.assertEqual(wiki_inputs.sources(self.db, self.root), first)
        self.assertEqual(proof.call_count, 1)

    def test_cached_source_rejects_changed_approval(self):
        wiki_inputs.sources(self.db, self.root)
        with self.db:
            self.db.execute("UPDATE executions SET output='changed' WHERE role='review'")
        with self.assertRaises(ValueError):
            wiki_inputs.sources(self.db, self.root)

    def test_same_size_same_mtime_publication_tampering_cannot_reuse_proof(self):
        wiki_inputs.sources(self.db, self.root)
        path = self.root / self.db.execute('SELECT path FROM publications WHERE id=?', (self.publication,)).fetchone()[0]
        before = path.stat()
        body = path.read_bytes()
        path.write_bytes(b'!' + body[1:])
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        with self.assertRaisesRegex(ValueError, 'verified evidence'):
            wiki_inputs.sources(self.db, self.root)

    def test_file_changed_between_proof_and_stamp_never_enters_cache(self):
        path = self.root / self.db.execute('SELECT path FROM publications WHERE id=?', (self.publication,)).fetchone()[0]
        original = ReadSet.fingerprint
        def changed(reads):
            path.write_bytes(b'!' + path.read_bytes()[1:])
            return original(reads)
        with patch.object(ReadSet, 'fingerprint', changed), self.assertRaises(ChangedDependencies):
            wiki_inputs.sources(self.db, self.root)
        with self.assertRaisesRegex(ValueError, 'verified evidence'):
            wiki_inputs.sources(self.db, self.root)


    def test_disk_hits_also_enforce_the_process_cache_bound(self):
        record=(dumps(True),{},{},({},{}),{})
        with patch('x_curator.audit_memo.read',return_value=record):
            for identity in range(1030):
                audit_reuse.cached(self.db,self.root,('bounded',identity),lambda reads: self.fail('disk hit recomputed'))
        self.assertLessEqual(len(audit_reuse._CACHE),1024)
