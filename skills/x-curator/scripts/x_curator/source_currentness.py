"""Compare source publication currentness without rebinding receipt revisions."""
from .revisions import revision
from .profile_evidence import retain_profile_evidence
from .source_presentation import normalize
from .source_evidence import branch, nodes
from .profile_links import strip_entity_links, quoted_alias as cited

CURRENTNESS_POLICY = 'source-currentness/v8'


def currentness(entry, quotes=()):
    comparable = revision(entry)
    tweet = comparable['tweet']
    for post in (tweet, branch(tweet, 'quoted_status_result', 'result')):
        normalize(post, quotes)
        strip_uncited_profile(post, quotes)
        retain_profile_evidence(branch(post.get('tweet', post), 'core', 'user_results', 'result'), quotes)
    for node in nodes(comparable):
        if node.get('__typename') == 'User':
            retain_profile_evidence(node, quotes)
    return [CURRENTNESS_POLICY, comparable]


def strip_uncited_profile(post, quotes):
    user = branch(post.get('tweet', post), 'core', 'user_results', 'result')
    profile = branch(user, 'legacy')
    entities = branch(profile, 'entities')
    for field in ('legacy', 'profile_bio'):
        bio = branch(user, field)
        if isinstance(description := bio.get('description'), str) and not cited([description, entities.get('description')], quotes):
            bio.pop('description', None)
            if field == 'profile_bio' and not bio:
                user.pop(field, None)
    if not cited([profile.get('description'), branch(user, 'profile_bio').get('description'), entities.get('description')], quotes):
        strip_entity_links(entities, 'description')
    strip_uncited_links(profile, quotes)


def strip_uncited_links(profile, quotes):
    entities = branch(profile, 'entities')
    if not cited([profile.get('url'), entities.get('url')], quotes):
        profile.pop('url', None)
        strip_entity_links(entities, 'url')
    if not entities:
        profile.pop('entities', None)
