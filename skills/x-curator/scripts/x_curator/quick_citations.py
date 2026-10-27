"""Name the offending capture without relaxing source or citation validation."""
from .claim_validation import captured, nonempty, validate_citation


def validate_source(source, captures):
    capture = captured(captures, source['capture'])
    try:
        require_body(capture)
        validate_citation(source, capture)
        for key in ('origin', 'reason'):
            nonempty(source[key])
        if type(source['primary']) is not bool or type(source['credible']) is not bool:
            raise ValueError('explicit source assessment required')
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError(f"citation {source['capture']}: {exc}") from exc


def require_body(capture):
    if capture['kind'] == 'video' and capture.get('prepared_video'):
        return
    key = {'text': 'quick_excerpt', 'pdf': 'approved_resource', 'video': 'approved_resource'}.get(capture['kind'])
    if not capture.get(key):
        raise ValueError('factual support needs an observed source body')
