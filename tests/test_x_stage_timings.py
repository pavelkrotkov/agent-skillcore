"""Synthetic timing coverage without live sources, accounts or model calls."""
from multiprocessing import Process
from unittest.mock import patch
import os
import time
import sqlite3

from x_batch_fixtures import BatchCase
from x_curator import accounting, stage_timings, wiki_build, wiki_sources
from x_curator.storage import open_store
from x_curator.stage_store import path


def interrupt_process(root):
    with open_store(root) as db:
        with stage_timings.span(db, 'synthetic.interrupted'):
            os._exit(17)


class StageTimingTests(BatchCase):
    def test_worker_index_and_readback_expose_slowest_stage_and_proof_fences(self):
        source, site = wiki_sources.verify_publication, wiki_build.render_site

        def acquire(*args,**kwargs):
            time.sleep(.02)
            return source(*args,**kwargs)

        def render(*args):
            time.sleep(.3)
            return site(*args)

        with stage_timings.span(self.db, 'synthetic.pipeline'):
            with patch('x_curator.wiki_sources.verify_publication', side_effect=acquire), patch(
                    'x_curator.wiki_build.render_site', side_effect=render):
                self.assertEqual(self.run_batch(limit=1)['completed'], 1)
                accounting.report(self.db, self.root)
        report = stage_timings.report(self.db)
        self.assertEqual(report['state'], 'complete')
        self.assertEqual(report['slowest'][0]['stage'], 'wiki.site_render')
        phases = {r['phase'] for r in report['corpus_audits']}
        self.assertTrue({'input', 'readback'} <= phases)
        self.assertNotIn('precommit', phases)
        self.assertIn('wiki.precommit_replay', report['aggregates'])
        self.assertIn('wiki.lock_and_activate', report['aggregates'])
        self.assertGreater(report['wall_seconds'], report['local_processing_union_seconds'])
        self.assertEqual(len(report['models']), 1)
        self.assertEqual(report['aggregates']['wiki.source_audit']['samples'], len(report['corpus_audits']))
        with patch('x_curator.wiki_inputs.sources', side_effect=AssertionError('report retried source proof')):
            self.assertEqual(stage_timings.report(self.db, report['run'])['run'], report['run'])

    def test_timeout_failure_skip_and_retry_remain_distinct(self):
        with stage_timings.span(self.db, 'synthetic.states'):
            with self.assertRaises(TimeoutError):
                with stage_timings.span(self.db, 'synthetic.timeout'):
                    raise TimeoutError('private error payload must not enter receipts')
            with self.assertRaises(ValueError):
                with stage_timings.span(self.db, 'synthetic.failure'):
                    raise ValueError('private body')
            stage_timings.skip(self.db, 'synthetic.skipped', 'no selected items')
            with stage_timings.span(self.db, 'worker.item', attempt='synthetic-attempt', attempt_number=2,
                                    item='hashed-item', queue_wait_seconds=.5):
                pass
        original_run = stage_timings.report(self.db)['run']
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            self.db.execute('UPDATE jobs SET action=action')
            with stage_timings.span(self.db, 'synthetic.writer_locked'):
                pass
        stage_timings.timed('source.linked_excerpt', token_arg=True)(
            lambda db, token: 'read completed')(self.db, 'synthetic-attempt')
        report = stage_timings.report(self.db, original_run)
        self.assertIn('source.linked_excerpt', report['aggregates'])
        self.assertEqual(report['retries'], 1)
        self.assertEqual(report['queue_wait_seconds'], .5)
        self.assertEqual({row['stage']: row['outcome'] for row in report['stages']}['synthetic.timeout'], 'timeout')
        self.assertEqual({row['stage']: row['outcome'] for row in report['stages']}['synthetic.failure'], 'failed')
        self.assertEqual({row['stage']: row['outcome'] for row in report['stages']}['synthetic.skipped'], 'skipped')
        self.assertEqual(report['slow_items'][0]['context']['item'], 'hashed-item')
        self.assertNotIn('private body', str(report))
        self.assertNotIn('private error payload', str(report))

    def test_interrupted_child_and_missing_historical_receipts(self):
        child = Process(target=interrupt_process, args=(self.root,))
        child.start()
        child.join(timeout=10)
        self.assertEqual(child.exitcode, 17)
        with sqlite3.connect(path(self.db)) as receipts:
            record = receipts.execute("SELECT run FROM stage_spans WHERE stage='synthetic.interrupted'").fetchone()
        report = stage_timings.report(self.db, record[0])
        self.assertEqual(report['state'], 'incomplete')
        self.assertIsNone(report['wall_seconds'])
        self.assertIsNone(report['stages'][0]['finished'])
        self.assertEqual(report['stages'][0]['outcome'], 'interrupted')
        self.assertEqual(stage_timings.report(self.db, 'absent-run')['state'], 'incomplete')
