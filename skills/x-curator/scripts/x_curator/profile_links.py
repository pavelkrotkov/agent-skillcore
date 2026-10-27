"""Canonical profile links retain targets and any explicitly cited aliases."""
from .source_evidence import branch, strings

URL_FIELDS = ('url', 'display_url', 'expanded_url', 'indices')


def normalize_profile_urls(profile, quotes):
    for field in ('description', 'url'):
        for url in branch(profile, 'entities', field).get('urls', []):
            url.pop('indices', None)
            if isinstance(url.get('expanded_url'), str) and url['expanded_url'] and not quoted_alias([url.get('url'), url.get('display_url')], quotes):
                url.pop('url', None)
                url.pop('display_url', None)


def normalize_homepage(profile, quotes):
    homepage = next(iter(branch(profile, 'entities', 'url').get('urls', [])), {}).get('expanded_url')
    if isinstance(homepage, str) and homepage and not quoted_alias(profile.get('url'), quotes):
        profile['url'] = homepage


def quoted_alias(value, quotes):
    return any(quote in text for quote in quotes for text in strings(value))


def strip_entity_links(entities, field):
    entity = entities.get(field)
    if not isinstance(entity, dict):
        return
    if isinstance(urls := entity.get('urls'), list):
        for url in urls:
            strip_url_fields(url)
        entity['urls'] = list(filter(lambda url: url != {}, urls))
        if not entity['urls']:
            entity.pop('urls')
    if not entity:
        entities.pop(field, None)


def strip_url_fields(url):
    if isinstance(url, dict):
        for key in URL_FIELDS:
            url.pop(key, None)
