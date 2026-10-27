"""Validate local links and assets in the actual rendered HTML tree."""
from functools import cache
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .html_text import check_anchor
from . import wiki_html_cache


def validate(site,root=None):
    site = Path(site).resolve()
    documents,facts=wiki_html_cache.documents(site,root)
    if not documents or site / 'index.html' not in documents:
        raise ValueError('rendered wiki has no index')
    resolve = cache(resolve_target)
    for path, parser in documents.items():
        for url in parser.urls:
            check(site, path, url, documents, resolve)
    wiki_html_cache.save(root,facts)
    return len(documents)


def check(site, path, url, documents, resolve):
    parts = urlsplit(url)
    if parts.scheme or parts.netloc:
        return
    base = site if parts.path.startswith('/') else path if not parts.path else path.parent
    target = resolve(site, base, parts.path)
    if target is None:
        raise ValueError('rendered link or asset is missing: ' + url)
    check_anchor(target, unquote(parts.fragment), documents)


def resolve_target(site, base, href):
    target = (base / unquote(href.lstrip('/'))).resolve() if href else base
    target = target / 'index.html' if target.is_dir() else target
    return target if target.is_relative_to(site) and target.is_file() else None
