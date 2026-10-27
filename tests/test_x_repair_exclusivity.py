from x_repair_fixtures import QualificationCase
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import repair_dispatch
import repair_manifest
import repair_qualification
from x_curator.command_lock import lockfile


class RepairExclusivityTests(QualificationCase):
    def test_concurrent_claimers_reserve_only_one_replacement_attempt(self):
        manifest = self.manifest()
        approval = repair_manifest.identity(manifest)
        repair_qualification.prepare(self.db, manifest, approval)
        def claim():
            with closing(sqlite3.connect(self.root / 'curator.sqlite3')) as db:
                db.row_factory = sqlite3.Row
                return repair_dispatch.claim(db, manifest['items'][0], approval)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: claim(), range(2)))
        self.assertEqual(sum(value is not None for value in results), 1)

    def test_operator_apply_cannot_cross_the_existing_intake_lock(self):
        manifest = self.manifest()
        path = self.root / 'qualification.json'
        path.write_text(json.dumps(manifest))
        script = Path(repair_manifest.__file__).with_name('x-repair-qualify.py')
        with lockfile(self.root, '.collector.lock'):
            result = subprocess.run([sys.executable, str(script), '--state', str(self.root), '--manifest', str(path),
                                     '--apply', repair_manifest.identity(manifest)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('BlockingIOError', result.stderr)
        self.assertEqual(self.db.execute('SELECT count(*) FROM quick_recoveries').fetchone()[0], 0)
