"""Bounded article bodies derived only from retained authenticated focal posts."""
from . import blobs, x_detail
from .source_evidence import branch
from .x_urls import identity as post_id, article_identity as identity
from .x_derived_receipts import retrieval


def entity(db, parent):
    focal, _ = x_detail.validate(blobs.read(db, parent['body_sha']), parent.get('focal_id') or post_id(parent['url']))
    return branch(focal, 'article', 'article_results', 'result')


def derive(db, evidence, key, url, start):
    parent = evidence['captures'][key]
    if parent['kind'] != 'x_detail':
        raise ValueError('article requires an authenticated focal post')
    retrieval(db, evidence, parent)
    article = entity(db, parent)
    if str(article.get('rest_id')) != identity(url):
        raise ValueError('authenticated article identity does not match requested article')
    text = article.get('plain_text')
    if not isinstance(text, str) or not text.strip():
        raise ValueError('authenticated article has no body; title/preview is not body evidence')
    if type(start) is not int or not 0 <= start < len(text):
        raise ValueError('invalid article excerpt offset')
    return dict(kind='text', url=url, requested_url=url, body_sha=parent['body_sha'], fetched=parent['fetched'],
                article_from=key, article_id=article['rest_id'], text=text[start:start + 6000],
                excerpt_start=start, quick_excerpt=True, truncated=len(text) > start + 6000,
                limitations=['Authenticated article body excerpt only; unseen article text was not reviewed.'])


def verify(db, evidence):
    for payload in evidence['captures'].values():
        if 'article_from' in payload:
            expected = derive(db, evidence, payload['article_from'], payload['url'], payload['excerpt_start'])
            if payload != expected:
                raise ValueError('article excerpt differs from its authenticated response')
