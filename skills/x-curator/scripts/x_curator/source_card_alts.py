"""Discard a preview alt duplicate only while its typed text binding remains."""


PREVIEW_STEMS = ('thumbnail_image', 'summary_photo_image', 'photo_image_full_size', 'player_image')


def explicit_alts(bindings, stems):
    names = {stem + '_alt_text' for stem in stems}
    return {value['string_value'] for name, value in bindings
            if name in names and value.get('type') == 'STRING'
            and isinstance(value.get('string_value'), str)}


def strip_duplicate(value, image, alts):
    alt = image.get('alt')
    if value.get('type') == 'IMAGE' and isinstance(alt, str) and alt and alt in alts:
        image.pop('alt')
