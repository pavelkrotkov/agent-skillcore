"""Static metadata is useful evidence of a page description, never its unread body."""
from .html_text import HTMLText


class MetadataHTML(HTMLText):
    def __init__(self):
        super().__init__()
        self.metadata = []

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)
        values = dict(attrs)
        key = values.get('name', values.get('property', ''))
        if tag == 'meta' and key in ('description', 'og:title', 'og:description', 'twitter:title', 'twitter:description') and values.get('content'):
            self.metadata.append(values['content'].strip())


def read(body, url):
    parser = MetadataHTML()
    parser.feed(body.decode('utf-8', errors='replace'))
    text = '\n'.join(parser.parts)
    if len(text.strip()) >= 20:
        return {'kind': 'text', 'text': text}
    metadata = '\n'.join(dict.fromkeys(parser.metadata))
    if len(metadata.strip()) < 20:
        raise ValueError('source content unavailable or too sparse; recover original source')
    return {'kind': 'metadata', 'text': 'Page metadata (not page body):\n' + metadata,
            'limitations': ['Only static page metadata was readable; page body was not available: ' + url]}
