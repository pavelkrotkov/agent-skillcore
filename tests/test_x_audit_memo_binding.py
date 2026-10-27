import errno
from pathlib import Path
from unittest.mock import Mock, patch
from x_fixtures import CollectionCase
from x_curator import audit_memo, audit_reuse
from x_curator.audit_seal import binding
from x_curator.proof_mode import MaintenanceRequired


class MemoBindingTests(CollectionCase):
    def test_truncated_memo_does_not_access_or_create_a_key(self):
        identity = ('source', 'synthetic-short')
        path, _ = audit_memo.target(self.root, identity)
        path.parent.mkdir(mode=0o700, exist_ok=True)
        path.write_bytes(b'short')
        diagnostic = {}
        with patch.object(audit_memo, 'secret', side_effect=AssertionError('key access')):
            self.assertIsNone(audit_memo.read(self.root, identity, diagnostic))
        self.assertEqual(diagnostic, dict(stage='read', path=str(path), size=5, reason='short-body'))
        self.assertEqual(path.read_bytes(), b'short')
        self.assertFalse((path.parent / 'key').exists())

    def test_signed_wrong_shape_remains_unavailable_with_decode_diagnostic(self):
        identity = ('source', 'synthetic-shape')
        audit_memo.write(self.root, identity, ('not', 'a', 'proof'))
        diagnostic = {}
        self.assertIsNone(audit_memo.read(self.root, identity, diagnostic))
        self.assertEqual(diagnostic['stage'], 'decode')
        self.assertEqual(diagnostic['reason'], 'record-shape')

    def test_transient_read_failure_is_identified_without_replay_or_memo_change(self):
        identity = ('source', 'synthetic-transient')
        record = (b'value', {}, {}, ({}, {}), {})
        audit_memo.write(self.root, identity, record)
        path, _ = audit_memo.target(self.root, identity)
        original = path.read_bytes()
        compute = Mock(side_effect=AssertionError('historical replay'))
        audit_reuse._CACHE.clear()
        with patch.object(Path, 'read_bytes', side_effect=OSError(errno.EMFILE, 'synthetic')):
            with self.assertRaises(MaintenanceRequired) as failure:
                audit_reuse.cached(self.db, self.root, identity, compute, required=True)
        for detail in (str(path), repr(identity), "'stage': 'read'", "'reason': 'OSError'", f"'errno': {errno.EMFILE}"):
            self.assertIn(detail, str(failure.exception))
        compute.assert_not_called()
        self.assertEqual(path.read_bytes(), original)
        diagnostic = {'stale': True}
        self.assertEqual(audit_memo.read(self.root, identity, diagnostic), record)
        self.assertEqual(diagnostic, {})

    def test_signature_cannot_be_replayed_for_a_different_identity(self):
        audit_memo.write(self.root, ('source', 'first'), (b'value', {}, {}, ({}, {}), {}))
        first, _ = audit_memo.target(self.root, ('source', 'first'))
        other, _ = audit_memo.target(self.root, ('source', 'other'))
        other.write_bytes(first.read_bytes())
        diagnostic = {}
        with patch('x_curator.audit_seal.loads', side_effect=AssertionError('untrusted deserialize')):
            self.assertIsNone(audit_memo.read(self.root, ('source', 'other'), diagnostic))
        self.assertEqual(diagnostic['reason'], 'signature-mismatch')
        self.assertEqual(diagnostic['stage'], 'authenticate')
        self.assertNotEqual(binding(self.root, ('source', 'first')), binding(self.root, ('source', 'other')))

    def test_restart_preserves_empty_query_dependency_and_binary_parameters(self):
        self.db.execute('CREATE TABLE observed_dependencies (value BLOB)')
        def compute(reads):
            row = reads.execute('SELECT value FROM observed_dependencies WHERE value=?', (b'\0binary',)).fetchone()
            return None if row is None else tuple(row)
        self.assertIsNone(audit_reuse.cached(self.db, self.root, ('empty', 1), compute))
        audit_reuse._CACHE.clear()
        self.db.execute('INSERT INTO observed_dependencies VALUES (?)', (b'\0binary',))
        self.assertEqual(tuple(audit_reuse.cached(self.db, self.root, ('empty', 1), compute)), (b'\0binary',))
