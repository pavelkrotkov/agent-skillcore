import json
from unittest.mock import patch

from x_publication_fixtures import PublicationCase
from x_curator.deadlines import DeadlineExceeded
from x_curator.readiness import blocked
from x_curator import cycle_store
from x_curator.accounting import report


class SpeechReadinessTests(PublicationCase):
    def test_explicit_reader_probe_records_failure_without_consuming_attempts(self):
        config = self.root / 'reader.json'
        config.write_text(json.dumps({'token': 'synthetic', 'engine_sha': 'engine', 'model_sha': 'model'}))
        with patch.dict('os.environ', {'X_CURATOR_SPEECH_CONFIG': str(config)}):
            with patch('x_curator.readiness.request', side_effect=[ConnectionRefusedError(), {'engine_sha': 'engine', 'model_sha': 'model'}]):
                dependency = blocked(self.db)
                result = {'state': 'blocked', 'attempted': 0, 'dependency': dependency}
            self.assertEqual((result['state'], result['attempted']), ('blocked', 0))
            self.assertEqual(result['dependency']['route'], 'speech')
            self.assertIn('SSH tunnel', result['dependency']['action'])
            identity, _ = cycle_store.begin(self.db, 30)
            cycle_store.finish(self.db, identity, 'finished', {'work': result})
            journal = report(self.db, self.root)['operations']['cycles'][0]
            self.assertEqual(journal['dependency'], result['dependency'])
            self.assertEqual(self.db.execute('SELECT attempts FROM jobs').fetchone()[0], 1)
            with patch('x_curator.readiness.request', side_effect=DeadlineExceeded):
                with self.assertRaises(DeadlineExceeded):
                    blocked(self.db)
