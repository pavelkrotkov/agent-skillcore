"""Fast file stamps never bless timestamp-restored or replaced evidence."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from x_curator import proof_files


class ProofFileTests(TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.path=self.root/'evidence'
        self.path.write_bytes(b'original')
        self.file=(str(self.root),'evidence')

    def test_unchanged_file_does_not_read_bytes_and_restored_mtime_is_detected(self):
        body,prior=proof_files.read(self.file,{})
        import hashlib
        digest=hashlib.sha256(body).digest()
        with patch.object(proof_files,'read',side_effect=AssertionError('byte reread')):
            self.assertEqual(proof_files.checked(self.file,digest,prior,{}),(digest,prior))
        before=self.path.stat()
        self.path.write_bytes(b'tampered')
        os.utime(self.path,ns=(before.st_atime_ns,before.st_mtime_ns))
        self.assertNotEqual(proof_files.checked(self.file,digest,prior,{})[0],digest)

    def test_identical_bytes_in_replacement_inode_are_freshly_verified(self):
        body,prior=proof_files.read(self.file,{})
        replacement=self.root/'replacement'
        replacement.write_bytes(body)
        replacement.replace(self.path)
        with patch.object(proof_files,'read',wraps=proof_files.read) as read:
            proof_files.checked(self.file,b'wrong',prior,{})
        read.assert_called_once()

    def test_symlinked_parent_is_rejected_even_when_target_bytes_are_identical(self):
        folder=self.root/'linked'
        folder.symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(ValueError):
            proof_files.metadata((str(self.root),'linked/evidence'),{})
