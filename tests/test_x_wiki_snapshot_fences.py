"""Snapshot fences preserve withdrawal and exact file/database dependencies."""
import json
import os
from unittest.mock import patch

from x_wiki_fixtures import WikiCase
from x_curator.read_set import ChangedDependencies
from x_curator.wiki import run
from x_curator.wiki_build import build
from x_curator.wiki_input_load import Snapshot


class WikiSnapshotFenceTests(WikiCase):
    def setUp(self):
        super().setUp()
        with patch('x_curator.wiki_mapping.runner', return_value=self.model):
            run(self.db, self.root)

    def test_snapshot_activation_rejects_same_size_restored_mtime_tampering(self):
        snapshot = Snapshot(self.db, self.root)
        sources, runs, pages = snapshot.values
        path = self.root / self.db.execute('SELECT path FROM publications').fetchone()[0]
        before = path.stat()
        path.write_bytes(b'!' + path.read_bytes()[1:])
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        with self.assertRaises(ChangedDependencies):
            build(self.db, self.root, sources, pages, runs, snapshot)
        with self.assertRaises(ChangedDependencies):
            snapshot.current()
        self.assertIsNone(json.loads((self.root / 'wiki/CURRENT.json').read_text())['generation'])

    def test_accepted_mapping_change_cannot_reuse_snapshot(self):
        snapshot = Snapshot(self.db, self.root)
        sources, runs, pages = snapshot.values
        with self.db:
            self.db.execute("UPDATE wiki_runs SET state='failed'")
        with self.assertRaises(ChangedDependencies):
            build(self.db, self.root, sources, pages, runs, snapshot)
        with self.assertRaises(ChangedDependencies):
            snapshot.current()
        self.assertIsNone(json.loads((self.root / 'wiki/CURRENT.json').read_text())['generation'])
