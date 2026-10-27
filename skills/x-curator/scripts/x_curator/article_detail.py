"""Read original full article evidence from retained authenticated detail responses."""
from . import x_detail
from .source_evidence import branch
from .x_urls import identity


def article(post):
    return branch(post.get('tweet', post), 'article', 'article_results', 'result')


def subset(old, new):
    if isinstance(old, dict):
        return isinstance(new, dict) and all(key in new and subset(value, new[key]) for key, value in old.items())
    return old == new


def full_body(value):
    return isinstance(value.get('plain_text'), str) and bool(value['plain_text'].strip())


def bodies(captures, source, read):
    for capture in captures.values():
        if capture['kind'] == 'x_detail' and (capture.get('focal_id') or identity(capture['url'])) == source:
            focal, _ = x_detail.validate(read(capture['body_sha']), source)
            if article(focal).get('plain_text'):
                yield article(focal)




def verify_bodies(captures, source, read, fresh):
    originals = list(bodies(captures, source, read))
    if not originals or not full_body(fresh):
        raise ValueError('article qualification requires original and fresh authenticated full bodies')
    if any(not subset(old, fresh) for old in originals):
        raise ValueError('authenticated article body or metadata changed')
