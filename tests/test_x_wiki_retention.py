from x_wiki_fixtures import WikiCase
"""Real compiler/checkpoint integration stays usable after generation pruning."""
import shutil
from unittest.mock import patch
from x_curator.wiki_input_load import Snapshot
from x_curator.wiki_index_result import publish
from x_curator.wiki import run
from x_curator import proof_revisions


class WikiRetentionTests(WikiCase):
    def test_repeated_publication_bounds_files_and_receipts_without_breaking_checkpoint(self):
        proof_revisions.prepare(self.db)
        for number in range(5):
            with patch('x_curator.wiki_build.policy', return_value=str(number)):
                result = publish(self.db, self.root, Snapshot(self.db, self.root))
        self.assertEqual(len(list((self.root / 'wiki/builds').iterdir())), 3)
        self.assertEqual(self.db.execute('SELECT count(*) FROM wiki_builds').fetchone()[0], 3)
        with patch('x_curator.wiki_build.render', side_effect=AssertionError('checkpoint lost')):
            self.assertEqual(run(self.db, self.root, 0), result)

    def test_missing_cached_build_is_rebuilt_instead_of_reusing_dangling_record(self):
        proof_revisions.prepare(self.db)
        first = publish(self.db, self.root, Snapshot(self.db, self.root))
        shutil.rmtree(self.root / 'wiki/builds' / first['generation'])
        second = publish(self.db, self.root, Snapshot(self.db, self.root))
        self.assertEqual(first['generation'], second['generation'])
        self.assertTrue((self.root / 'wiki/builds' / second['generation'] / 'site/index.html').is_file())
