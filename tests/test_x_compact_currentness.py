"""New acquisitions must preserve unchanged approvals and reject actual source changes."""
import json

from x_compact_fixtures import CompactCase
from x_fixtures import Client, collect, envelope
from x_curator import compact_history


class CompactCurrentnessTests(CompactCase):
    def acquire_again(self, changed=False):
        entry = json.loads(self.db.execute('SELECT entry FROM selections LIMIT 1').fetchone()[0])
        if changed:
            entry['content']['itemContent']['tweet_results']['result']['legacy']['full_text'] = 'Different source content.'
        page = envelope([dict(type='TimelineAddEntries', entries=[entry])])
        collect(self.db, Client([(200, page)]), 'likes', new=True, delay=0)

    def test_identical_new_collection_does_not_require_discarded_native_history(self):
        compact_history.run(self.db, self.root, apply=True)
        self.acquire_again()
        self.assertEqual(self.verified()[0], self.packet)

    def test_substantive_source_change_cannot_keep_its_old_compact_approval(self):
        compact_history.run(self.db, self.root, apply=True)
        self.acquire_again(changed=True)
        with self.assertRaises(ValueError):
            self.verified()
