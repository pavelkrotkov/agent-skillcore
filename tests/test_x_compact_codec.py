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


class CodecOnlyTests(unittest.TestCase):
    def setUp(self):
        self.key = patch('x_curator.compact_codec.secret', return_value=b'synthetic-controller-key-32-bytes!')
        self.key.start()
        self.addCleanup(self.key.stop)
        self.root = Path('/synthetic/state')
        self.context = compact_seal.context(self.root, ('publication', 'one'))

    def test_signature_rejects_changed_bytes_before_decoding(self):
        body, signature = compact_codec.pack(self.root, self.context, dict(version=1))
        with self.assertRaisesRegex(MaintenanceRequired, 'signature'):
            compact_codec.unpack(self.root, self.context, body + b'changed', signature)

    def test_a_valid_signature_is_bound_to_root_and_proof_identity(self):
        record = dict(version=1, value=b'approved facts')
        body, signature = compact_codec.pack(self.root, self.context, record)
        self.assertEqual(compact_codec.unpack(self.root, self.context, body, signature), record)
        other = compact_seal.context(Path('/another/state'), ('publication', 'one'))
        with self.assertRaisesRegex(MaintenanceRequired, 'signature'):
            compact_codec.unpack(self.root, other, body, signature)

    def test_unknown_signed_format_requires_maintenance(self):
        body, signature = compact_codec.pack(self.root, self.context, dict(version=999))
        with self.assertRaisesRegex(MaintenanceRequired, 'decode'):
            compact_codec.unpack(self.root, self.context, body, signature)
