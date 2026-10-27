from x_retention_fixtures import RetentionCase
from unittest.mock import patch
from x_curator import audit_memo, retention


class MemosRetentionTests(RetentionCase):
    def test_old_unknown_memos_expire_but_key_current_and_recent_memos_survive(self):
        self.build(1, current=True)
        record = (b'value', {}, {}, ({}, {}), {})
        audit_memo.write(self.root, ('wiki-checkpoint', 0), record)
        current, _ = audit_memo.target(self.root, ('wiki-checkpoint', 0))
        self.age(current)
        stale = current.with_name('a' * 64 + '.memo')
        stale.write_bytes(b'obsolete')
        self.age(stale)
        recent = current.with_name('b' * 64 + '.memo')
        recent.write_bytes(b'new worker cache')
        retention.run(self.db, self.root, apply=True)
        self.assertFalse(stale.exists())
        self.assertTrue(current.exists())
        self.assertTrue(recent.exists())
        # The shared signing key must survive expiration of obsolete proof namespaces.
        self.assertTrue((current.parent / 'key').exists())

    def test_symlinked_cache_directory_cannot_delete_another_namespace(self):
        self.build(1, current=True)
        outside = self.root / 'originals'
        outside.mkdir()
        original = outside / ('a' * 64 + '.memo')
        original.write_bytes(b'original')
        self.age(original)
        (self.root / 'audit-memos').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            retention.run(self.db, self.root, apply=True)
        self.assertEqual(original.read_bytes(), b'original')

    def test_missing_current_publication_proof_blocks_memo_expiration(self):
        self.build(1, current=True)
        folder = self.root / 'audit-memos'
        folder.mkdir()
        stale = folder / ('a' * 64 + '.memo')
        stale.write_bytes(b'old cache')
        self.age(stale)
        with patch('x_curator.retention_memos.ready', return_value=False):
            result = retention.run(self.db, self.root, apply=True)
        self.assertIn('action', result['memos'])
        self.assertTrue(stale.exists())
