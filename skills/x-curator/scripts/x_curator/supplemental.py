"""Optional research failures remain visible while mandatory source links stay required."""
from .acquire import acquire_urls
from .deadlines import DeadlineExceeded
from .evidence import save_capture


def acquire_supplemental(db, token, urls, fetcher):
    for url in sorted(urls):
        try:
            acquire_urls(db, token, {url}, fetcher)
        except DeadlineExceeded:
            raise
        except Exception as exc:
            save_capture(db, token, {"url": url, "kind": "unavailable", "text": "",
                "error": type(exc).__name__ + ": " + str(exc)[:300],
                "limitations": [limitation(url)]})


def limitation(url):
    return "Unavailable supplemental source: " + url
