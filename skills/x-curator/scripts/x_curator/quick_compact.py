"""Expand a compact model verdict into the existing deterministic packet shape."""
from .claim_validation import nonempty
from .quick_knowledge import packet
from .quick_claims import citations
from .quick_support import validate_check


def validate(decision, evidence):
    nonempty(decision['reason'])
    rows = decision.get('claims')
    if not isinstance(rows, list):
        raise ValueError('compact decision needs claims')
    try:
        handler = {'supported': supported, 'disproven': disproven,
                   'inconclusive': inconclusive}[decision['outcome']]
    except KeyError as exc:
        raise ValueError('unknown compact outcome') from exc
    return handler(rows, evidence)


def inconclusive(rows, _evidence):
    if rows:
        raise ValueError('inconclusive compact decision cannot retain claims')


def disproven(rows, evidence):
    claims, _ = expand(rows, evidence)
    if len(claims) != 1 or rows[0]['kind'] != 'fact' or rows[0]['status'] != 'disproven':
        raise ValueError('disproven compact decision needs one central factual contradiction')


def supported(rows, evidence):
    claims, checked = expand(rows, evidence)
    if not claims:
        raise ValueError('supported compact decision needs useful claims')
    identities = [claim['id'] for claim in claims]
    return packet({'title': {'text': claims[0]['text'], 'claims': identities[:1]},
                   'summary': {'text': ' '.join(claim['text'] for claim in claims), 'claims': identities},
                   'claims': claims, 'limitations': []}, evidence, checked)


def expand(rows, evidence):
    claims, checked = [], {}
    for index, row in enumerate(rows, 1):
        check_id, claim_id = f'f{index}', f'c{index}'
        check = {'id': check_id, 'text': row['text'], 'status': row['status'], 'sources': row['sources']}
        validate_check(check, evidence['captures'])
        checked[check_id] = check
        claims.append({'id': claim_id, 'text': row['text'], 'kind': row['kind'], 'attribution': row['attribution'],
                       'limitations': row['limitations'],
                       'citations': citations(row['sources']),
                       'checks': [check_id], 'independently_useful': True})
    return claims, checked
