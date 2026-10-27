from contextlib import closing
from pathlib import Path
from subprocess import CalledProcessError
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from x_daily_fixtures import DailyCase
from x_curator.command_lock import lockfile
from x_curator.index_pending import run as index_pending
from x_curator.storage import open_store


class WorkerIndexTests(DailyCase):
    def test_corrupt_current_pointer_reaches_the_existing_verified_rebuild(self):
        self.run_batch(defer_index=True)
        built = index_pending(self.db, self.root)
        (self.root / 'wiki/CURRENT.json').write_bytes(b'invalid pointer')
        repaired = index_pending(self.db, self.root)
        self.assertEqual(repaired['generation'], built['generation'])
        self.assertEqual(repaired['verified_sources'], 1)

    def test_deferred_worker_preserves_publication_and_batch_for_separate_indexing(self):
        with patch('x_curator.worker.wiki', side_effect=AssertionError('index must not occupy source worker')):
            result = self.run_batch(defer_index=True)
        self.assertEqual(result['completed'], 1)
        self.assertEqual(result['index']['state'], 'pending')
        self.assertIn('review_outbox', result)
        self.assertEqual(self.db.execute('SELECT state FROM curation_batches').fetchone()[0], 'closed')
        with patch('x_curator.wiki.organize', side_effect=AssertionError('semantic model forbidden')):
            built = index_pending(self.db, self.root)
        self.assertEqual(built['verified_sources'], 1)
        with patch('x_curator.index_pending.wiki', side_effect=AssertionError('unchanged catalog must not replay')):
            self.assertEqual(index_pending(self.db, self.root)['state'], 'idle')
        self.assertEqual(self.run_batch(defer_index=True)['attempted'], 0)

    def test_busy_wiki_preserves_completed_publication_and_flushes_batch(self):
        with lockfile(self.root, '.wiki.lock'), patch('x_curator.worker.wiki') as render:
            result = self.daily_work()
        render.assert_not_called()
        self.assertEqual(result['completed'], 1)
        self.assertEqual(result['index']['state'], 'blocked')
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 1)
        self.assertIn('review_outbox', result)
        self.assertEqual(self.daily_work()['attempted'], 0)

    def test_failed_index_keeps_publication_and_reconciles_closed_batch(self):
        with patch('x_curator.worker.wiki', side_effect=CalledProcessError(1, ['mkdocs'])):
            result = self.daily_work()
        self.assertEqual(result['completed'], 1)
        self.assertEqual(result['index']['state'], 'blocked')
        self.assertEqual(self.db.execute('SELECT state FROM curation_batches').fetchone()[0], 'closed')
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 1)
        self.assertIn('review_outbox', result)
        self.assertEqual(self.daily_work()['attempted'], 0)


class ColdIndexTests(unittest.TestCase):
    def test_timer_can_start_before_any_worker_without_model_or_publication_work(self):
        with TemporaryDirectory() as folder, closing(open_store(Path(folder))) as db:
            with patch('x_curator.index_pending.wiki', side_effect=AssertionError('cold empty index must not replay')):
                self.assertEqual(index_pending(db, Path(folder))['state'], 'idle')
            self.assertEqual(db.execute('SELECT count(*) FROM executions').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)
