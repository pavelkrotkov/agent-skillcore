"""Render model prose as text; all navigation is controller-generated."""
from datetime import datetime, timezone
import html
import re


def text(value):
    return re.sub(r'([\\`*_{}\[\]()#+.!|>-])', r'\\\1', html.escape(str(value), quote=False))


def date(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat(timespec='seconds')


def claim_lines(claim):
    return [text(claim['text']), 'Attribution: ' + text(claim['attribution']),
            'Assessment: ' + text(claim['kind']), 'Limitations: ' + text('; '.join(claim['limitations']))]


def link(label, target):
    return '[' + text(label) + '](' + target + ')'


def document(parts):
    return ('\n\n'.join(parts) + '\n').encode()
