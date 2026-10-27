"""Match only quote-reference enrichment inside one authenticated response."""
from .revisions import scrub
from .source_evidence import branch


def quote_view(post, expanded):
    """Compare only a bare matching reference with the same response's expansion."""
    value = scrub(post)
    quote = typed_post(branch(expanded, 'quoted_status_result', 'result'))
    if (quote and 'quoted_status_result' not in value
            and value.get('legacy', {}).get('quoted_status_id_str') == quote['rest_id']
            and value.get('quotedRefResult') == {'result': {'__typename': 'Tweet', 'rest_id': quote['rest_id']}}):
        value.pop('quotedRefResult')
        value['quoted_status_result'] = scrub(expanded['quoted_status_result'])
    return value


def typed_post(value):
    original = value.get('tweet', {}) if value.get('__typename') == 'TweetWithVisibilityResults' else value
    if not isinstance(original, dict) or {'legacy', 'note_tweet'}.isdisjoint(original):
        return None
    return original if original.get('__typename', value.get('__typename')) in ('Tweet', 'TweetWithVisibilityResults') and original.get('rest_id') else None
