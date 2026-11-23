"""Keep card evidence separate from native rendering and uncited live app metrics."""
from .source_evidence import branch, card_bindings
from .profile_links import quoted_alias
from .source_card_layout import strip_preview_cdn, strip_preview_palette
from .source_card_alts import explicit_alts, PREVIEW_STEMS


PREVIEW_COLORS = frozenset(stem + '_color' for stem in PREVIEW_STEMS)
PREVIEW_IMAGES = frozenset(stem + suffix
                          for stem in PREVIEW_STEMS
                          for suffix in ('', '_small', '_large', '_x_large', '_original'))

LIVE_METRICS = ('app_star_rating', 'app_num_ratings')


def normalize(card, quotes, *, preparation=False):
    bindings = list(card_bindings(card.get('binding_values') or []))
    alts = set() if preparation else explicit_alts(bindings, PREVIEW_STEMS)
    emptied = {id(value) for name, value in bindings if normalize_value(name, value, quotes, alts)}
    compact(card, emptied)


def normalize_value(name, value, quotes, alts):
    original = bool(value)
    if name in PREVIEW_IMAGES:
        strip_preview_cdn(value, alts)
    if name in PREVIEW_COLORS:
        strip_preview_palette(value)
    if name in LIVE_METRICS and not quoted_alias(value.get('string_value'), quotes):
        value.pop('string_value', None)
    return original and value == {}


def compact(card, emptied):
    values = card.get('binding_values')
    if isinstance(values, dict):
        card['binding_values'] = {key: value for key, value in values.items() if id(value) not in emptied}
    elif isinstance(values, list):
        card['binding_values'] = [item for item in values if id(branch(item).get('value')) not in emptied]
