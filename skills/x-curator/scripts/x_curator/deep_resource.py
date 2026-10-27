"""Only a separately approved exact PDF/video URL may invoke an existing reader."""
from .stage_timings import timed
from . import deep_permission, deep_scope, public_http, readers, youtube
from .evidence import bundle, save_capture
from .retrievals import retrieve
from .youtube_urls import video_id


def validate(resource):
    if set(resource) != {'kind', 'url'} or resource['kind'] not in ('pdf', 'video'):
        raise ValueError('explicit PDF/video type and exact resource URL required')
    public_http.public_url(resource['url'])
    return resource


@timed('source.approved_media', scope='selected', token_arg=True)
def acquire(db, token, permission):
    allowed, proposal = deep_permission.verified(db, permission)
    deep_scope.selected(allowed, bundle(db, token))
    resource = proposal.get('resource')
    if resource is None:
        return None
    validate(resource)
    url = resource['url']
    if resource['kind'] == 'video' and video_id(url):
        payload = youtube.acquire(db, token, url)
    else:
        payload = retrieve(db, token, url, public_http.fetch)
        require_type(payload, resource['kind'])
        payload = readers.extract(db, payload)
    if payload['kind'] != resource['kind']:
        raise ValueError('resource does not match its approved reader type')
    save_capture(db, token, dict(payload, approved_resource=permission))
    return resource


def require_type(payload, kind):
    mime = 'application/pdf' if payload.get('pdf_download') else payload['mime'].split(';')[0].lower()
    accepted = {'pdf': mime == 'application/pdf', 'video': mime.startswith('video/')}
    if not accepted[kind]:
        raise ValueError('resource type differs from explicit approval')
