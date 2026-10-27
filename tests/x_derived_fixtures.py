import json

from x_thread_fixtures import post, ROOT


IMAGE = 'https://example.org/mandatory-image.png'
CHILD = 'https://x.com/i/status/2'


def response(media=False):
    root = post('1', 'a', '1', in_reply_to_status_id_str='2')
    child = post('2', 'b', '2')
    child['note_tweet'] = {'note_tweet_results': {'result': {'text': 'Complete synthetic long post.'}}}
    if media:
        child['legacy']['extended_entities'] = {'media': [{'type': 'photo', 'media_url_https': IMAGE}]}
    user = {'__typename': 'User', 'rest_id': '2', 'legacy': {'description': 'This is a user, not a post.'}}
    return json.dumps({'data': [user, root, {'__typename': 'TweetWithVisibilityResults', 'tweet': child}]}).encode()


def fetch(_):
    return 200, 'application/json', response(), None


def details(evidence):
    return {c['url']: (key, c) for key, c in evidence['captures'].items() if c['kind'] == 'x_detail'}
