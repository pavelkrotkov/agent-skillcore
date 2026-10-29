"""Compaction must preserve explicit model-free recovery of an unchanged publication."""
from x_compact_fixtures import CompactCase
from x_curator import compact_history
from x_curator.publication_recovery import complete


class CompactRecoveryTests(CompactCase):
    def test_withdrawn_unchanged_publication_can_be_reinstated_without_raw_history(self):
        compact_history.run(self.db, self.root, apply=True)
        budget = tuple(self.db.execute('SELECT attempts,max_attempts FROM jobs').fetchone())
        with self.db:
            self.db.execute("UPDATE publications SET state='invalid'")
            self.db.execute("UPDATE jobs SET state='needs_action',action='synthetic withdrawal'")
        result = complete(self.db, self.root, self.publication, 'restore unchanged synthetic publication')
        self.assertEqual(result['state'], 'published')
        self.assertEqual(self.verified()[0], self.packet)
        self.assertEqual(budget, tuple(self.db.execute('SELECT attempts,max_attempts FROM jobs').fetchone()))
