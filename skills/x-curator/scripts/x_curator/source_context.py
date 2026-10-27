"""Stable account/place references are independent of mutable display metadata."""
from .source_evidence import branch
from .profile_links import quoted_alias


def normalize_mentions(post, quotes):
    for mention in branch(post, 'legacy', 'entities').get('user_mentions', []):
        if not isinstance(mention, dict):
            continue
        if not isinstance(mention.get('id_str'), str) or not mention['id_str']:
            continue
        for field in ('name', 'screen_name'):
            if not quoted_alias(mention.get(field), quotes):
                mention.pop(field, None)


def normalize_place(post):
    place = branch(post, 'legacy', 'place')
    box = branch(place, 'bounding_box')
    if isinstance(place.get('id'), str) and place['id'] and box.get('type') == 'Polygon' and coordinate_layout(box.get('coordinates')):
        box.pop('coordinates', None)


def coordinate_layout(value):
    if isinstance(value, list):
        return all(coordinate_layout(item) for item in value)
    return type(value) in (int, float)
