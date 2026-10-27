"""Bounded Poppler extraction retains every original PDF page as visible evidence."""
import subprocess
import time

from . import blobs
from .deadlines import until
from .pdf_pages import dimensions, intervals
from .storage import sha256

FLAGS = ['-singlefile', '-scale-to', '1600', '-png']


def command(args, seconds=30):
    return subprocess.run(args, capture_output=True, check=True, timeout=seconds)


def version(binary):
    result = command([binary, '-v'], 10)
    return (result.stdout + result.stderr).decode().splitlines()[0]


def extract(db, payload):
    path = blobs.state_root(db) / 'blobs' / payload['body_sha']
    with until(time.time() + 900):
        text = command(['pdftotext', '-layout', str(path), '-'], 45).stdout.decode('utf-8')
        info = command(['pdfinfo', str(path)]).stdout.decode()
        count = int(next((line.split(':', 1)[1] for line in info.splitlines() if line.startswith('Pages:')), '0'))
        pages, total = [], 0
        for page in intervals(text, count):
            body = command(['pdftoppm', '-f', str(page['number']), *FLAGS, str(path)]).stdout
            total += len(body)
            if len(body) > 20 * 1024 * 1024 or total > 512 * 1024 * 1024:
                raise ValueError('PDF page rendering exceeds retained-byte budget')
            width, height = dimensions(body)
            pages.append(dict(page, image=blobs.put(db, body), width=width, height=height))
        policy = {'version': 1, 'pdf_sha': payload['body_sha'], 'text_sha': sha256(text.encode()),
                  'extractor': version('pdftotext'), 'extract_flags': ['-layout'],
                  'renderer': version('pdftoppm'), 'render_flags': FLAGS, 'page_count': count}
    return dict(payload, kind='pdf', text=text, pages=pages, images=sorted({p['image'] for p in pages}), pdf=policy)
