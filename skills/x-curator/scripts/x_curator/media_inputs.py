"""Model attachments come only from controller-verified acquisition blobs."""
from . import blobs
from .publication_files import write_verified


def attachments(db, root, evidence, presentations=None):
    from . import media_presentations
    media_presentations.verify(db, evidence, presentations)
    images = media_presentations.identities(evidence, presentations)
    if len(images) > 32:
        raise ValueError("media needs segmented review beyond attachment budget")
    paths = []
    for identity in images:
        body = blobs.read(db, identity)
        name = identity + image_suffix(body)
        write_verified(root, name, body)
        paths.append(root / name)
    return paths


def image_suffix(body):
    signatures = [(b"\x89PNG\r\n\x1a\n", ".png"), (b"\xff\xd8\xff", ".jpg"), (b"GIF8", ".gif")]
    for magic, suffix in signatures:
        if body.startswith(magic):
            return suffix
    if body.startswith(b"RIFF") and body[8:12] == b"WEBP":
        return ".webp"
    raise ValueError("unsupported model image format; convert original evidence")


def identities(evidence):
    return {image for capture in evidence["captures"].values() for image in capture.get("images", [])}


def deferred(request):
    return (request.get('role'), request.get('policy'), request.get('phase', {}).get('name'),
            request.get('phase', {}).get('image_policy')) == (
                'factcheck', 'quick-factcheck/v1', 'evidence', 'deferred-to-final')


def input_images(request):
    from . import media_presentations
    if deferred(request):
        return []
    return media_presentations.identities(request['bundle'], request.get('image_presentations'))


def requires_partition(evidence):
    return any(c.get('kind') == 'pdf' for c in evidence['captures'].values()) or len(identities(evidence)) > 32
