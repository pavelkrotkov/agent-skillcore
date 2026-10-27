"""Bind the model-visible prompt, image bytes and final answer to the controller."""
import base64
import json

from .storage import sha256
from .verification_details import image_mismatch, require_prompt


def parts(messages, role):
    return [part for message in messages if message['role'] == role for part in message.get('content', [])]


def image_sha(part):
    header, data = part['image_url'].split(',', 1)
    if not header.startswith('data:image/') or not header.endswith(';base64'):
        raise ValueError('model image bytes not retained')
    return sha256(base64.b64decode(data, validate=True))


def verify_input(messages, proof):
    users = parts(messages, 'user')
    require_prompt(users, proof['prompt_sha'])
    images = [image_sha(part) for part in users if part['type'] == 'input_image']
    if proof['format'] == 'x-curator-input-proof-v1':
        images.sort()
    if images != proof['images']:
        raise ValueError('model image bytes differ from acquired attachments; ' +
                         image_mismatch(images, proof['images'], proof['format']))


def verify_messages(messages, proof, packet):
    verify_input(messages, proof)
    verify_answer(messages, packet)


def verify_answer(messages, packet):
    texts = [''.join(p.get('text', '') for p in m['content']) for m in messages
             if m['role'] == 'assistant' and m.get('phase') == 'final_answer']
    if not texts or json.loads(texts[-1]) != packet:
        raise ValueError('rollout final answer differs from executor output')
