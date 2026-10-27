"""Pinned metadata extractor without plugins, JS runtimes or download handlers."""
from .youtube_http import open_request
from .youtube_urls import video_id


VERSION = '2026.08.19'


def resolve(db, token, url):
    from yt_dlp import YoutubeDL
    from yt_dlp.extractor.youtube import YoutubeIE
    from yt_dlp.globals import plugin_dirs
    from yt_dlp.version import __version__
    if __version__ != VERSION:
        raise ValueError('YouTube resolver version differs from qualified pin')
    plugin_dirs.value = []
    identities = []

    class Controlled(YoutubeDL):
        def urlopen(self, request):
            return open_request(db, token, request, identities)

    settings = dict(quiet=True, no_warnings=True, cachedir=False, noplaylist=True,
                    skip_download=True, extractor_retries=0, retries=0, js_runtimes={}, remote_components=[])
    with Controlled(settings, auto_init=False) as resolver:
        resolver.add_info_extractor(YoutubeIE())
        result = resolver.extract_info('https://www.youtube.com/watch?v=' + video_id(url), download=False, process=False)
    validate_result(result, video_id(url))
    return result, identities


def validate_result(result, identity):
    if result.get('id') != identity or result.get('live_status') != 'not_live':
        raise ValueError('YouTube identity or live status is unsupported')
    if not 0 < result.get('duration', 0) <= 1800:
        raise ValueError('YouTube duration exceeds current reading budget')
