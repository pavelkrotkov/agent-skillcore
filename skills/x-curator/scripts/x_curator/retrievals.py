"""Reserve every HTTP request before network activity; budgets survive restarts."""
from .stage_timings import timed
import time
from urllib.parse import urljoin

from . import blobs, dropbox
from .retrieval_store import finish, reserved


def request(db, token, url, fetcher):
    with reserved(db, token, url) as identity:
        status, mime, body, location = fetcher(url)
        body_sha = finish(db, identity, status, body)
        return status, mime, body_sha, location



@timed("source.http_acquisition", scope="selected", token_arg=True)
def retrieve(db, token, url, fetcher):
    current, pdf = url, False
    for _ in range(6):
        download = dropbox.download_url(current)
        current, pdf = download or current, pdf or bool(download)
        status, mime, body_sha, location = request(db, token, current, fetcher)
        if status == 200:
            return captured(db, url, current, mime, body_sha, pdf)
        if status not in (301, 302, 303, 307, 308) or not location:
            raise ValueError("source retrieval failed: HTTP " + str(status))
        current = urljoin(current, location)
    raise ValueError("source redirect budget exhausted")


def captured(db, url, final_url, mime, body_sha, pdf):
    payload = dict(url=url, final_url=final_url, mime=mime, body_sha=body_sha, fetched=time.time())
    if pdf:
        dropbox.validate(mime, blobs.read(db, body_sha))
        payload['pdf_download'] = True
    return payload
