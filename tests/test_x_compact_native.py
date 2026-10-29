"""Native search/tool attestations stay bound after full transcript removal."""
from x_native_search_fixtures import NativeCase
from x_curator import compact_history, wiki_store
from x_curator.publication_audit import verify_publication


class CompactNativeTests(NativeCase):
    def setUp(self):
        super().setUp()
        self.assertIsNotNone(self.run_check())
        wiki_store.initialize(self.db)
        self.db.commit()

    def test_native_search_approval_verifies_after_compaction(self):
        compact_history.run(self.db, self.root, apply=True)
        row = self.db.execute('SELECT * FROM publications').fetchone()
        self.assertIsNotNone(verify_publication(self.db, self.root, row))
        self.assertIsNone(self.db.execute('SELECT log FROM executions').fetchone()[0])

    def test_native_search_allowance_cannot_change_after_attestation(self):
        compact_history.run(self.db, self.root, apply=True)
        with self.db:
            self.db.execute('UPDATE quick_checks SET searches=searches+1')
        row = self.db.execute('SELECT * FROM publications').fetchone()
        with self.assertRaisesRegex(ValueError, 'dependency changed'):
            verify_publication(self.db, self.root, row)
