import struct
import zlib

from x_publication_fixtures import PublicationCase
from x_curator.blobs import put
from x_curator.media_inputs import attachments


def chunk(kind, body):
    return struct.pack('!I', len(body)) + kind + body + struct.pack('!I', zlib.crc32(kind + body))


def png(red):
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', 1, 1, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(bytes((0, red, 0, 0)))) + chunk(b'IEND', b''))


class MediaInputTests(PublicationCase):
    def test_complete_unique_media_survives_attachment_and_remains_bounded(self):
        bodies = [png(n) for n in range(33)]
        identities = [put(self.db, body) for body in bodies]
        capture = {'images': identities[:32] + identities[:6]}
        evidence = {'captures': {'frames': capture}}
        paths = attachments(self.db, self.root / 'model-inputs', evidence)
        self.assertEqual(len(paths), 32)
        self.assertEqual({p.read_bytes() for p in paths}, set(bodies[:32]))
        capture['images'].append(identities[32])
        with self.assertRaisesRegex(ValueError, 'segmented review'):
            attachments(self.db, self.root / 'model-inputs', evidence)
        capture['images'] = [identities[0]]
        (self.root / 'blobs' / identities[0]).write_bytes(b'corrupt acquisition')
        with self.assertRaisesRegex(ValueError, 'tampered acquisition'):
            attachments(self.db, self.root / 'model-inputs', evidence)
