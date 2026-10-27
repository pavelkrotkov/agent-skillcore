"""Optional signed restart reuse; a cache miss always requires the original proof."""
from contextlib import suppress
import os
from marshal import dumps
import tempfile

from .audit_seal import binding, signature, authenticated_record
from .audit_key import secret
from .publication_files import private_target


def target(root, identity):
    context = binding(root, identity)
    return private_target(root, 'audit-memos/' + context.decode() + '.memo'), context


def read(root, identity, diagnostic=None):
    """Replace diagnostic with this read's failure details; empty means success."""
    diagnostic = {} if diagnostic is None else diagnostic
    diagnostic.clear()
    diagnostic['stage'] = 'target'
    try:
        path, context = target(root, identity)
        diagnostic.update(path=str(path), stage='read')
        body = path.read_bytes()
        diagnostic['size'] = len(body)
        if len(body) < 32:
            diagnostic['reason'] = 'short-body'
            return None
        diagnostic['stage'] = 'key'
        key = secret(root)
        return authenticated_record(key, context, body, diagnostic)
    except (OSError, ValueError, EOFError) as error:
        diagnostic.update(reason=type(error).__name__, errno=getattr(error, 'errno', None))
        return None


def write(root, identity, record):
    path, context = target(root, identity)
    payload = dumps(record)
    body = signature(secret(root), context, payload) + payload
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        try:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
            os.replace(stream.name, path)
        finally:
            if os.path.exists(stream.name):
                os.unlink(stream.name)


def retain(root,identity,record):
    with suppress(OSError,ValueError):
        write(root,identity,record)
