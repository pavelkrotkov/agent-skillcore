import struct
import zlib

from test_x_media_inputs import chunk
from x_publication_fixtures import PublicationCase
from x_curator import blobs


def frame(red, width=960, height=1704):
    row = b'\0' + bytes((red, 40, 80)) * width
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(row * height)) + chunk(b'IEND', b''))


class VideoPreviewCase(PublicationCase):
    def setUp(self):
        super().setUp()
        images = [blobs.put(self.db, frame(red)) for red in range(24)]
        self.video = dict(kind='video', prepared_video='controller-preparation', images=images,
                          frames=[dict(sha=sha, at=n * 10) for n, sha in enumerate(images)])
        self.evidence = dict(captures={'video': self.video})
