from unittest.mock import Mock, patch

from x_wiki_fixtures import WikiCase
from x_curator.deadlines import DeadlineExceeded
from x_curator.wiki_mapping import map_sources


class ZKTimeoutTests(WikiCase):
    def test_timeout_retains_the_original_trace_and_spends_only_the_mapping_attempt(self):
        failure = DeadlineExceeded('Synthetic cutoff')
        failure.log = b'{"synthetic":"retained partial trace"}\n'
        with patch('x_curator.wiki_mapping.runner', return_value=Mock(side_effect=failure)):
            with self.assertRaises(DeadlineExceeded):
                map_sources(self.db, self.inputs)
        row = self.db.execute('SELECT * FROM wiki_runs').fetchone()
        self.assertEqual((row['state'], row['proposal'], row['review']), ('failed', failure.log, None))
        self.assertEqual(self.db.execute('SELECT attempts FROM wiki_sources').fetchone()[0], 1)
