import struct
from unittest.mock import patch

from x_reading_fixtures import ReadingCase
from x_curator import blobs
from x_curator.evidence import save_capture
from x_curator.pdf_pages import intervals
from x_curator.pdf_reader import FLAGS
from x_curator.storage import sha256


def png(tag):
    return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR' + struct.pack('>II', 32, 32) + tag


class PdfCase(ReadingCase):
    def setUp(self):
        super().setUp()
        patch.dict('x_curator.reading_plan.POLICIES', {2: {'width': 1000, 'context': 20, 'max_segments': 16, 'images': 2}}).start()
        text = 'First α page.\n\f\fLast β page.\n\f\f'
        images = [blobs.put(self.db, png(tag)) for tag in (b'first', b'empty', b'last', b'empty')]
        pages = [dict(span, image=image, width=32, height=32) for span, image in zip(intervals(text, 4), images)]
        body = blobs.put(self.db, b'%PDF-synthetic-controller-fixture')
        self.pdf_capture = {'kind': 'pdf', 'url': 'https://example.test/original.pdf', 'mime': 'application/pdf',
                            'body_sha': body, 'text': text, 'pages': pages, 'images': sorted(set(images)),
                            'pdf': dict(version=1, pdf_sha=body, text_sha=sha256(text.encode()),
                                        extractor='pdftotext version synthetic', extract_flags=['-layout'],
                                        renderer='pdftoppm version synthetic', render_flags=FLAGS, page_count=4)}
        self.pdf = save_capture(self.db, self.token, self.pdf_capture)

    def segment(self, request):
        packet = super().segment(request)
        for item in packet['coverage']:
            capture = request['bundle']['captures'][item['capture']]
            if capture['kind'] == 'pdf':
                item['pages'] = [dict(number=p['number'], status='reviewed', notes='Synthetic original page visually inspected.') for p in capture['pages']]
        return packet
