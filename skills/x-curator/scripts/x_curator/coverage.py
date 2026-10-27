"""Missing evidence cannot be silently promoted into complete coverage."""
from .claim_validation import nonempty
from .supplemental import limitation
from .pdf_coverage import validate as validate_pdf


def validate_coverage(packet, captures):
    if not isinstance(packet["limitations"], list):
        raise ValueError("limitations required")
    coverage = packet["coverage"]
    if len(coverage) != len(captures) or {c["capture"] for c in coverage} != set(captures):
        raise ValueError("all acquired sources and media need coverage")
    for item in coverage:
        validate_item(item, captures[item["capture"]], packet["limitations"])
    require_acquisitions(captures)


def validate_item(item, capture, limitations):
    validate_pdf(item, capture)
    expected = {'unavailable': 'unavailable', 'metadata': 'metadata_only'}.get(capture['kind'], 'covered')
    if item["status"] != expected:
        raise ValueError("unresolved evidence or media")
    nonempty(item["notes"])
    required = [limitation(capture['url'])] if expected == 'unavailable' else capture.get('limitations', []) if expected == 'metadata_only' else []
    if not set(required) <= set(limitations):
        raise ValueError('missing unread-body limitation or unavailable-source explicit limitation')


def require_acquisitions(captures):
    acquired = {c["url"] for c in captures.values() if c["kind"] != "unavailable"}
    required = {url for c in captures.values() for url in c.get("required_urls", [])}
    if not required <= acquired:
        raise ValueError("linked context or media has not been acquired")
