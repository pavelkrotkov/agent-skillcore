"""Readable HTML text excludes executable and navigational content."""
from html.parser import HTMLParser


class HTMLText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("title", "script", "style", "nav", "noscript"):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ("title", "script", "style", "nav", "noscript"):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.parts.append(" ".join(data.split()))


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        self.ids.add(values.get('id'))
        self.urls.extend(values[key] for key in ('href', 'src') if values.get(key))



def check_anchor(target, fragment, documents):
    if fragment and target in documents and fragment not in documents[target].ids:
        raise ValueError('rendered anchor is missing: ' + fragment)
