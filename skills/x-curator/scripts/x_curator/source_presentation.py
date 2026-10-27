"""Remove acquisition presentation fields while retaining evidence-bearing values."""
from .source_evidence import branch
from .source_links import normalize_quote_link
from .source_cards import normalize as normalize_card
from .source_context import normalize_mentions, normalize_place
from .profile_links import normalize_profile_urls, normalize_homepage



def normalize(post, quotes=()):
    post = post.get('tweet', post)
    post.pop('source', None)
    branch(post, 'legacy').pop('source', None)
    user = branch(post, 'core', 'user_results', 'result')
    user.pop('profile_description_language', None)
    user.pop('avatar', None)
    profile = branch(user, 'legacy')
    for name in ('profile_banner_url', 'profile_background_image_url_https'):
        profile.pop(name, None)
    normalize_profile_urls(profile, quotes)
    normalize_homepage(profile, quotes)
    normalize_quote_link(post, quotes)
    normalize_mentions(post, quotes)
    normalize_place(post)
    normalize_card(branch(post, 'card', 'legacy'), quotes)
