"""Authenticate local memo bytes before decoding; evidence dependencies stay separate."""
from importlib.metadata import packages_distributions,version
from functools import lru_cache
import hashlib
import hmac
from marshal import loads
import sys
from pathlib import Path

from .receipts import digest
from .proof_policy import dependencies


@lru_cache(maxsize=8)
def policy(kind='all'):
    paths,external = dependencies(kind)
    packages=versions(external,kind)
    return digest([sys.version, packages, [(path.name, hashlib.sha256(path.read_bytes()).hexdigest()) for path in paths]])


def binding(root, identity):
    return digest(['audit-memo/v2', str(Path(root).resolve()), policy(identity[0]), identity]).encode()


def signature(key, context, payload):
    return hmac.digest(key, context + payload, 'sha256')

installed=lru_cache(maxsize=1)(packages_distributions)


def versions(external,kind):
    packages=installed()
    distributions={name for module in external for name in packages.get(module,())}
    if kind in ('wiki-render','wiki-checkpoint'):
        distributions.add('mkdocs')
    return tuple(sorted((name,version(name)) for name in distributions))


def authenticated_record(key, context, body, diagnostic):
    diagnostic['stage'] = 'authenticate'
    if not hmac.compare_digest(body[:32], signature(key, context, body[32:])):
        diagnostic['reason'] = 'signature-mismatch'
        return None
    diagnostic['stage'] = 'decode'
    record = loads(body[32:])
    if not isinstance(record, tuple) or len(record) != 5:
        diagnostic['reason'] = 'record-shape'
        return None
    diagnostic.clear()
    return record
