"""Strip typed native preview layout, retaining alt text and unknown values."""
from .source_evidence import branch



def strip_preview_cdn(value):
    image = branch(value, 'image_value')
    if str(image.get('url', '')).startswith('https://pbs.twimg.com/'):
        image.pop('url', None)
        numbers(image, ('width', 'height'))
    strip_empty(value, 'image_value', 'IMAGE')


def strip_preview_palette(value):
    color = branch(value, 'image_color_value')
    if isinstance(palette := color.get('palette'), list):
        for item in palette:
            strip_color(item)
        color['palette'] = [item for item in palette if item != {}]
        if not color['palette']:
            color.pop('palette')
    strip_empty(value, 'image_color_value', 'IMAGE_COLOR')


def strip_color(item):
    if not isinstance(item, dict):
        return
    numbers(item, ('percentage',))
    numbers(branch(item, 'rgb'), ('red', 'green', 'blue'))
    if item.get('rgb') == {}:
        item.pop('rgb')


def numbers(value, names):
    for name in names:
        if type(value.get(name)) in (int, float):
            value.pop(name)


def strip_empty(value, field, kind):
    if value.get(field) == {} and value.get('type') == kind:
        value.pop(field)
        value.pop('type')
