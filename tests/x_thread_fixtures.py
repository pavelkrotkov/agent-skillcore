import json


ROOT = 'https://x.com/i/status/1'
MEDIA = 'https://example.org/parent-media'


def post(identity, author, conversation, **legacy):
    return {'__typename': 'Tweet', 'rest_id': identity, 'legacy': dict(full_text='Synthetic context evidence.',
            user_id_str=author, conversation_id_str=conversation, **legacy)}


def responses():
    root = post('1', 'a', '1', in_reply_to_status_id_str='3')
    continuation = post('2', 'a', '1')
    parent = post('3', 'b', '3', quoted_status_id_str='5',
                  entities={'urls': [{'expanded_url': MEDIA}]})
    sibling = post('4', 'b', '3')
    quoted = post('5', 'c', '5')
    return {'1': [root, continuation], '2': [continuation],
            '3': [parent, sibling], '4': [sibling], '5': [quoted]}


def fetch(url):
    if url == MEDIA:
        return 200, 'text/plain', b'Synthetic parent media context with sufficient readable evidence.', None
    return 200, 'application/json', json.dumps({'data': responses()[url.rsplit('/', 1)[1]]}).encode(), None
