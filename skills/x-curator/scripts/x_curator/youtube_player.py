"""Bind selected formats to original successful Innertube player responses."""
import json
from urllib.parse import urlsplit

from . import blobs, http_receipts, youtube_media, youtube_resolver
from .youtube_urls import video_id


# Normalized extractor output alone cannot authenticate a format. Check the raw player
# response before range downloads spend the remaining source allowance.
def selection(db, result, receipts, job, url):
    identity = video_id(url)
    youtube_resolver.validate_result(result, identity)
    selected = youtube_media.formats(result)
    players = player_responses(db, receipts, job, identity, result['duration'])
    for value in selected:
        verify_player(value, players)
    return selected


def player_responses(db, receipts, job, identity, duration):
    players = []
    for receipt in receipts:
        sent, response = http_receipts.read(db, receipt, job)
        body = blobs.read(db, response['body_sha'])
        if response['status'] != 200 or not body.lstrip().startswith(b'{'):
            continue
        data = json.loads(body)
        details = data.get('videoDetails', {})
        if details.get('videoId') == identity and data.get('playabilityStatus', {}).get('status') == 'OK':
            validate_player(sent, details, duration)
            players.extend(data.get('streamingData', {}).get('adaptiveFormats', []))
    return players


def validate_player(sent, details, duration):
    if details.get('isLiveContent') or abs(float(details['lengthSeconds']) - duration) >= 2:
        raise ValueError('YouTube player duration or live status differs')
    parts = urlsplit(sent['url'])
    if (parts.scheme, parts.netloc, parts.path) != ('https', 'www.youtube.com', '/youtubei/v1/player'):
        raise ValueError('YouTube player receipt has unexpected origin')


def verify_player(value, players):
    matching = [p for p in players if str(p['itag']) == value['format_id'] and p.get('url') == value['url']]
    if not matching or any(int(p.get('contentLength', 0)) != value['filesize'] for p in matching):
        raise ValueError('YouTube media is not bound to authentic player response')
