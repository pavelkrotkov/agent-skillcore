"""Qualify a sparse article selection using unchanged authenticated full bodies."""
from . import x_detail
from .source_currentness import currentness
from .source_references import reference_quotes
from .article_detail import article, verify_bodies, subset


def entry(post):
    return {'content': {'itemContent': {'tweet_results': {'result': post}}}}


def comparable(value, quotes):
    result = currentness(value, quotes)
    post = result[1]['tweet']
    post.pop('article', None)
    post.pop('grok_analysis_button', None)
    if post.get('has_birdwatch_notes') is False:
        post.pop('has_birdwatch_notes')
    return result


def verify(captures, current, body, source, read, packet=None):
    from .evidence import citation_quotes
    entries = {key: c['source']['entry'] for key, c in captures.items() if c['kind'] == 'selection'}
    focal, _ = x_detail.validate(body, source)
    fresh = article(focal)
    verify_bodies(captures, source, read, fresh)
    if not entries:
        raise ValueError('article qualification requires original source selection')
    quotes = reference_quotes(entries, current['entry'], citation_quotes(packet, entries), packet)
    target = comparable(current['entry'], quotes)
    if article(currentness(current['entry'], quotes)[1]['tweet']) or comparable(entry(focal), quotes) != target:
        raise ValueError('article qualification requires a sparse unchanged focal selection')
    verify_originals(entries.values(), fresh, target, quotes)


def verify_originals(entries, fresh, target, quotes):
    for old in entries:
        original = article(currentness(old, quotes)[1]['tweet'])
        if not original.get('rest_id') or not subset(original, fresh) or comparable(old, quotes) != target:
            raise ValueError('article metadata or substantive source revision changed')
