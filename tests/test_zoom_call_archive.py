"""Safety and verification contracts for local call publication."""
import argparse
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/zoom-call-archive/scripts/archive_call.py'
SPEC = importlib.util.spec_from_file_location('zoom_call_archive', SCRIPT)
archive = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(archive)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.stage = self.root / 'stage'
        (self.stage / 'transcript').mkdir(parents=True)
        (self.stage / 'transcript/cleaned.md').write_text('Original words and 12.5%\n')
        self.share = self.root / 'mounted-share'
        self.share.mkdir()
        self.destination = self.share / 'dated-call'

    def publish(self, **kwargs):
        args = argparse.Namespace(stage=kwargs.get('stage', self.stage),
                                  destination=kwargs.get('destination', self.destination))
        with contextlib.redirect_stdout(io.StringIO()):
            archive.publish(args)

    def test_success_receipt_matches_every_byte_and_preserves_source(self):
        before = archive.inventory(self.stage)
        self.publish()
        receipt = json.loads((self.destination / 'publication.json').read_text())
        self.assertEqual(receipt['files'], before)
        self.assertEqual(archive.inventory(self.stage), before)
        self.assertEqual(archive.digest(self.destination / 'transcript/cleaned.md'),
                         before['transcript/cleaned.md']['sha256'])
        self.assertEqual(sorted(p.name for p in self.share.iterdir()), ['dated-call'])

    def test_existing_target_is_not_overwritten_even_when_empty(self):
        self.destination.mkdir()
        with self.assertRaises(FileExistsError): self.publish()
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_offline_parent_is_not_created(self):
        target = self.root / 'disconnected-share/dated-call'
        with self.assertRaisesRegex(ValueError, 'parent'): self.publish(destination=target)
        self.assertFalse(target.parent.exists())

    def test_symlinked_source_content_and_destination_ancestors_refused(self):
        (self.stage / 'secret-link').symlink_to(self.stage / 'transcript/cleaned.md')
        with self.assertRaisesRegex(ValueError, 'Symlink'): self.publish()
        (self.stage / 'secret-link').unlink()
        alias = self.root / 'alias'
        alias.symlink_to(self.share, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlink'): self.publish(destination=alias / 'call')
        self.assertFalse(self.destination.exists())

    def test_overlap_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'overlap'):
            self.publish(destination=self.stage / 'transcript/call')

    def test_copy_failure_keeps_source_and_leaves_incomplete_directory(self):
        marker = self.share / 'unrelated.txt'
        marker.write_text('keep')
        before = archive.inventory(self.stage)
        with mock.patch.object(archive.shutil, 'copyfileobj', side_effect=OSError('offline')):
            with self.assertRaises(OSError): self.publish()
        self.assertEqual(archive.inventory(self.stage), before)
        self.assertEqual(set(self.share.iterdir()), {marker, self.destination})
        self.assertFalse((self.destination / 'publication.json').exists())

    def test_mutating_source_fails_verification_and_does_not_publish(self):
        copy = archive.shutil.copyfileobj
        def mutate(source, target):
            copy(source, target)
            Path(source.name).write_text('changed while copying')
        with mock.patch.object(archive.shutil, 'copyfileobj', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'verification'): self.publish()
        self.assertTrue(self.destination.exists())
        self.assertFalse((self.destination / 'publication.json').exists())
        self.assertEqual(list(self.share.iterdir()), [self.destination])

    def test_concurrent_noncooperating_target_is_never_overwritten(self):
        mkdir = Path.mkdir
        def race(path, *args, **kwargs):
            if path == self.destination:
                mkdir(path)
                (path / 'other-writer.txt').write_text('keep')
            return mkdir(path, *args, **kwargs)
        with mock.patch.object(Path, 'mkdir', autospec=True, side_effect=race):
            with self.assertRaises(FileExistsError): self.publish()
        self.assertEqual((self.destination / 'other-writer.txt').read_text(), 'keep')
        self.assertFalse((self.destination / 'publication.json').exists())

    def test_destination_uses_normal_umask_permissions_not_temp_0700(self):
        previous = os.umask(0o022)
        try:
            self.publish()
        finally:
            os.umask(previous)
        self.assertEqual(self.destination.stat().st_mode & 0o777, 0o755)
        self.assertEqual((self.destination / 'transcript/cleaned.md').stat().st_mode & 0o777, 0o644)

    def test_existing_lock_is_preserved(self):
        lock = self.share / '.dated-call.publish-lock'
        lock.mkdir()
        with self.assertRaises(FileExistsError): self.publish()
        self.assertTrue(lock.is_dir())


class MediaValidationTests(unittest.TestCase):
    def test_rectangle_rejects_invalid_coordinates(self):
        for value in ['-1,0,10,10', '0,0,0,10', '0,0,10', 'a,b,c,d']:
            with self.assertRaises(argparse.ArgumentTypeError): archive.rectangle(value)
        self.assertEqual(archive.rectangle('0,2,40,30'), (0,2,40,30))

    def test_crop_cannot_exceed_recorded_bounds(self):
        with self.assertRaisesRegex(ValueError, 'exceeds'): archive.check_box((10,10,100,100), 100,100)

    def test_rotation_requires_explicit_orientation(self):
        data = dict(format=dict(duration='5'), streams=[dict(codec_type='video', width=100,
                    height=100, duration='5', side_data_list=[dict(rotation=90)])])
        with mock.patch.object(archive.subprocess, 'check_output', return_value=json.dumps(data)):
            with self.assertRaisesRegex(ValueError, 'Rotated'): archive.probe(Path('input.mov'))

    @unittest.skipUnless(importlib.util.find_spec('PIL'), 'Pillow is an optional image-review dependency')
    def test_small_change_survives_in_all_sample_review_when_filter_suppresses_it(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as temporary:
            samples = Path(temporary)
            first = Image.new('RGB', (320,180), 'white')
            first.save(samples / 'first.png')
            second = first.copy()
            second.putpixel((100,100), (0,0,0))
            second.save(samples / 'second.png')
            archive.write_json(samples / 'sample.json', dict(width=320, height=180,
                source_sha256='fixture', samples=[dict(file='first.png',target_seconds=0),
                                                  dict(file='second.png',target_seconds=5)]))
            args = argparse.Namespace(samples=samples, region=None, report=samples/'review',threshold=0.6)
            with mock.patch.object(archive, 'contact_sheets', wraps=archive.contact_sheets) as sheets:
                with contextlib.redirect_stdout(io.StringIO()): archive.dedupe(args)
            self.assertEqual(len(sheets.call_args_list[0].args[0]), 1)
            self.assertEqual(len(sheets.call_args_list[1].args[0]), 2)
            self.assertTrue((args.report/'all-samples/contact-000.jpg').exists())


if __name__ == '__main__':
    unittest.main()
