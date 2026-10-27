"""Compare quoted-post link destinations independently of username aliases."""
from urllib.parse import urlsplit

from .source_evidence import branch
from .profile_links import quoted_alias


def normalize_quote_link(post, quotes):
    legacy = branch(post, 'legacy')
    link = branch(legacy, 'quoted_status_permalink')
    target = legacy.get('quoted_status_id_str')
    parsed = urlsplit(link.get('expanded', ''))
    if parsed.scheme in ('http', 'https') and parsed.netloc in ('twitter.com', 'x.com', 'www.twitter.com', 'www.x.com') and parsed.path.split('/')[-2:] == ['status', target]:
        if not quoted_alias([link.get('expanded'), link.get('display')], quotes):
            link['expanded'] = 'https://x.com/i/status/' + target
            link.pop('display', None)


def handle_case_url(url):
    parts = urlsplit(str(url))
    path = parts.path.split('/')
    if len(path) == 4 and path[2] == 'status':
        path[1] = path[1].casefold()
    return parts._replace(path='/'.join(path))
