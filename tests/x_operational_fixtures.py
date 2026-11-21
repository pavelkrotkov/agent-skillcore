import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from x_fixtures import SCRIPTS
from x_curator.storage import sha256


class OperationalCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE review_deliveries (id TEXT,observed TEXT,failure TEXT,created REAL);
            CREATE TABLE publications (id TEXT,state TEXT,account TEXT,source TEXT);
            CREATE TABLE jobs (account TEXT,id TEXT,state TEXT);
            CREATE TABLE wiki_runs (id TEXT,state TEXT,started REAL);
            CREATE TABLE wiki_builds (id TEXT,manifest TEXT,created REAL);
            CREATE TABLE collections (id TEXT,started REAL);
        """)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def generation(self, mapping):
        prefix = "wiki/builds/synthetic"
        target = prefix + "/site/source-map.json"
        body = json.dumps(mapping).encode()
        path = self.root / target
        path.parent.mkdir(parents=True)
        path.write_bytes(body)
        manifest = dict(generation="synthetic",sources=list(mapping),files={target: sha256(body)})
        self.db.execute("INSERT INTO wiki_builds VALUES (?,?,1)", ("synthetic",json.dumps(manifest)))
        (self.root / "wiki/CURRENT.json").write_text('{"generation":"synthetic"}')
        return path
