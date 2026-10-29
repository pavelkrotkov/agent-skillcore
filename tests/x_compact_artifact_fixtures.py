"""Authentication is required before decoding or discarding model-history copies."""
from pathlib import Path
import json
import os
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from x_fixtures import SCRIPTS
from x_curator import compact_seal, compact_artifacts, compact_codec
from x_curator.proof_mode import MaintenanceRequired


class ArtifactCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = sqlite3.connect(':memory:')
        self.addCleanup(self.db.close)
        compact_seal.initialize(self.db)
        self.identity = ('publication', 'synthetic-publication')
        self.record = dict(version=1, provenance=dict(sessions=[], events={}), value=b'approved facts')
        compact_seal.write(self.db, self.root, self.identity, self.record, active=1)


    def session_file(self, identity, observed=None):
        folder = self.root / "worker/sessions"
        folder.mkdir(parents=True)
        path = folder / ("rollout-" + identity + ".jsonl")
        path.write_text(json.dumps(dict(type="session_meta", payload=dict(id=observed or identity))) + "\n")
        os.utime(path, (time.time() - 600, time.time() - 600))
        self.record["provenance"]["sessions"] = [identity]
        compact_seal.write(self.db, self.root, self.identity, self.record, active=1)
        return path
