"""Select bounded direct streams and merge only retained local input files."""
import math

from .recovery import request_limit
from .leases import require_lease
from .http_ranges import WIDTH
from urllib.parse import urlsplit
import time


def formats(result):
    # ponytail: qualify 360p H.264 + AAC first; add formats only with acquisition/readback proof.
    values = {value['format_id']: value for value in result['formats']}
    if not {'134', '140'} <= values.keys():
        raise ValueError('YouTube lacks qualified video/audio formats')
    return [media_format({key: values[identity][key] for key in ('format_id', 'url', 'filesize')}) for identity in ('134', '140')]


def budget(db, token, selected):
    job = require_lease(db, token, time.time())
    used = db.execute('SELECT count(*) FROM retrievals WHERE account=? AND source=?', (job['account'], job['id'])).fetchone()[0]
    needed = sum(math.ceil(value['filesize'] / WIDTH) for value in selected)
    if used + needed > request_limit(db, job['account'], job['id']):
        raise ValueError('complete YouTube media exceeds remaining lifetime request budget')


def media_format(value):
    parts = urlsplit(value['url'])
    if parts.scheme != 'https' or not parts.hostname or not parts.hostname.endswith('.googlevideo.com'):
        raise ValueError('direct HTTPS YouTube media required')
    if type(value.get('filesize')) is not int or not 0 < value['filesize'] <= 128 * WIDTH:
        raise ValueError('YouTube media size unavailable or excessive')
    return value
