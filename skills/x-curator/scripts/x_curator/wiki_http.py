"""Serve only the latest completed wiki site on loopback."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sys


def current_site(root):
    wiki = Path(root).resolve() / 'wiki'
    generation = json.loads((wiki / 'CURRENT.json').read_text())['generation']
    site = wiki / 'builds' / generation / 'site'
    if not re.fullmatch('[0-9a-f]{64}', generation) or site.resolve(strict=True) != site:
        raise ValueError('wiki site unavailable')
    return site


class Handler(SimpleHTTPRequestHandler):
    def send_head(self):
        try:
            site = current_site(self.server.root)
            self.directory = str(site)
            target = Path(self.translate_path(self.path))
            if any(not p.resolve().is_relative_to(site) for p in (target, target / 'index.html', target / 'index.htm')):
                return self.send_error(403)
        except (OSError, ValueError, KeyError, TypeError):
            return self.send_error(503, 'Completed wiki unavailable')
        return super().send_head()

    def list_directory(self, path):
        return self.send_error(403, 'Directory listing disabled')

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('Usage: python -m x_curator.wiki_http STATE')
    # Tailscale is the access-control boundary; never bind this reader to all interfaces.
    with ThreadingHTTPServer(('127.0.0.1', 8043), Handler) as server:
        server.root = sys.argv[1]
        server.serve_forever()
