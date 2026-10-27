"""Redirect metadata creates a mandatory video obligation without claiming its contents."""
from .youtube_urls import video_id


def is_alias(payload):
    final = payload.get('final_url', '')
    return bool(final != payload['url'] and video_id(final))


def metadata(payload):
    return dict(payload, kind='metadata', text='This URL redirects to a YouTube video; its contents require separate acquisition.',
                required_urls=[payload['final_url']], limitations=['Redirect metadata only; video is a separate required source.'])


def validate(payload):
    if payload['kind'] == 'unavailable':
        return
    if video_id(payload['url']) and not payload.get('youtube_sha'):
        raise ValueError('YouTube capture has no authenticated media acquisition')
    if is_alias(payload):
        if payload['kind'] != 'metadata' or payload['final_url'] not in payload.get('required_urls', []):
            raise ValueError('YouTube redirect omits its required video')
