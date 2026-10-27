import os
from pathlib import Path
import tempfile
from unittest.mock import patch
from x_fixtures import CollectionCase
from x_curator import audit_key, audit_reuse


class KeyGuardTests(CollectionCase):
    def test_key_bytes_and_permissions_use_the_same_descriptor_after_replacement(self):
        original = audit_key.secret(self.root)
        replacement = self.root / 'replacement-key'
        replacement.write_bytes(b'x' * 32)
        replacement.chmod(0o600)
        fstat = os.fstat
        def replace(descriptor):
            info = fstat(descriptor)
            os.replace(replacement, self.root / 'audit-memos/key')
            return info
        with patch.object(audit_key.os, 'fstat', side_effect=replace):
            self.assertEqual(audit_key.secret(self.root), original)

    def test_directory_symlink_cannot_escape_the_state_root(self):
        with tempfile.TemporaryDirectory(dir=self.root.parent) as outside:
            (self.root / 'audit-memos').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                audit_key.secret(self.root)
            self.assertFalse((Path(outside) / 'key').exists())

    def test_missing_cache_directory_does_not_block_a_successful_proof(self):
        with patch('x_curator.audit_memo.write', side_effect=FileNotFoundError('cache removed')):
            self.assertEqual(audit_reuse.cached(self.db, self.root, ('optional', 1), lambda reads: b'valid'), b'valid')

    def test_cached_file_dependencies_remain_absolute_after_cwd_changes(self):
        (self.root / 'source.bin').write_bytes(b'original')
        old = Path.cwd()
        try:
            os.chdir(self.root.parent)
            result = audit_reuse.cached(self.db, self.root, ('relative', 1), lambda reads: reads.read_file(self.root.name, 'source.bin'))
        finally:
            os.chdir(old)
        audit_reuse._CACHE.clear()
        with patch('x_curator.audit_memo.write', side_effect=AssertionError('unexpected replay')):
            self.assertEqual(audit_reuse.cached(self.db, self.root, ('relative', 1), lambda reads: None), result)
