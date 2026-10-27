from x_repair_fixtures import QualificationCase
import repair_history
import repair_manifest
import repair_qualification


class RepairHistoryTests(QualificationCase):
    def test_actual_execution_bytes_and_prior_attempts_are_part_of_the_frozen_gate(self):
        manifest = self.manifest()
        approval = repair_manifest.identity(manifest)
        log = self.db.execute('SELECT log FROM executions LIMIT 1').fetchone()[0]
        with self.db:
            self.db.execute('UPDATE executions SET log=?', (b'changed without changing log_sha',))
        with self.assertRaisesRegex(ValueError, 'history changed'):
            repair_qualification.prepare(self.db, manifest, approval)
        with self.db:
            self.db.execute('UPDATE executions SET log=log_sha')
        with self.assertRaisesRegex(ValueError, 'history changed'):
            repair_qualification.prepare(self.db, manifest, approval)
        with self.db:
            self.db.execute('UPDATE executions SET log=?', (log,))
            self.db.execute("UPDATE attempts SET action='different historical reason'")
        with self.assertRaisesRegex(ValueError, 'history changed'):
            repair_qualification.prepare(self.db, manifest, approval)
        self.assertEqual(self.db.execute('SELECT count(*) FROM quick_recoveries').fetchone()[0], 0)

    def test_two_item_apply_rejects_one_stale_item_before_creating_any_grant(self):
        manifest = self.manifest()
        self.add_items(2)
        self.run_batch()
        check = self.db.execute("SELECT * FROM quick_checks WHERE source='2'").fetchone()
        current = self.db.execute("SELECT * FROM jobs WHERE id='2'").fetchone()
        from x_curator.receipts import digest
        item = dict(category='irrelevant_search', account=check['account'], source=check['source'],
                    revision=check['revision'], original=check['id'], job_sha=digest(dict(current)),
                    attempts=current['attempts'], max_attempts=current['max_attempts'],
                    **repair_history.snapshot(self.db, dict(original=check['id'])))
        manifest['items'].append(item)
        manifest['scope']['count'] = 2
        approval = repair_manifest.identity(manifest)
        with self.db:
            self.db.execute("UPDATE jobs SET action='changed second item' WHERE id='2'")
        with self.assertRaisesRegex(ValueError, 'job changed'):
            repair_qualification.prepare(self.db, manifest, approval)
        self.assertEqual(self.db.execute('SELECT count(*) FROM quick_recoveries').fetchone()[0], 0)
