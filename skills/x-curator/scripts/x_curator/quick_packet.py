"""Validate bounded decisions without inheriting mandatory outgoing-link closure."""
from .claim_validation import nonempty
from .quick_knowledge import packet
from .quick_support import validate_check


def checks(decision, evidence):
    rows = decision['checks']
    result = {c['id']: c for c in rows}
    if not result or len(result) != len(rows) or not decision['central'] or not set(decision['central']) <= result.keys():
        raise ValueError('distinct checks and central premise required')
    for row in rows:
        validate_check(row, evidence['captures'])
    return result


def validate(decision, evidence):
    if decision.get('format') == 'compact-v1':
        from .quick_compact import validate as compact
        return compact(decision, evidence)
    nonempty(decision['reason'])
    checked = checks(decision, evidence)
    false = any(checked[key]['status'] == 'disproven' for key in decision['central'])
    if false != (decision['outcome'] == 'disproven'):
        raise ValueError('disproven central premise must exclude the item')
    if decision['outcome'] == 'supported':
        return packet(decision['packet'], evidence, checked)
    if decision['outcome'] not in ('disproven', 'inconclusive') or decision.get('packet'):
        raise ValueError('unresolved/excluded material cannot enter the wiki')
    return None
