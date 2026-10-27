import base64
import uuid

from x_publication_fixtures import events
from x_curator.receipts import encoded
from x_curator.model_trace import pack
from x_curator.storage import sha256
from x_curator.worker_prompts import prompt

IMAGE = b'synthetic-image-bytes'
SESSION = '12345678-1234-1234-1234-123456789abc'


def trace_fixture():
    request = {'role': 'research', 'bundle': {'captures': {'c': {'text': 'Synthetic evidence.', 'images': [sha256(IMAGE)]}}}, 'proposal': None}
    packet = {'synthetic': True}
    rows = [
        {'type': 'session_meta', 'payload': {'id': SESSION}},
        {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user', 'content': [
            {'type': 'input_text', 'text': prompt(request)},
            {'type': 'input_image', 'image_url': 'data:image/png;base64,' + base64.b64encode(IMAGE).decode()}]}},
        {'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant', 'phase': 'final_answer',
             'content': [{'type': 'output_text', 'text': encoded(packet).decode()}]}}
    ]
    return request, events(packet, SESSION), rows


def rollout(rows):
    return b'\n'.join(encoded(row) for row in rows)


def image_content(images):
    return [{'type': 'input_image', 'image_url': 'data:image/png;base64,' + base64.b64encode(body).decode()}
            for _, body in sorted((images or {}).items())]


def proof(request, output, session=None, images=None):
    session = session or str(uuid.uuid4())
    content = [{'type': 'input_text', 'text': prompt(request)}]
    content.extend(image_content(images))
    rows = [{'type': 'session_meta', 'payload': {'id': session}},
            {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user',
              'content': content}},
            {'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant', 'phase': 'final_answer',
              'content': [{'type': 'output_text', 'text': encoded(output).decode()}]}}]
    return pack(request, prompt(request), ['synthetic'], events(output, session), b'\n'.join(encoded(r) for r in rows))
