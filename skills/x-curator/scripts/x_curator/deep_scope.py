"""Bind observed evidence to the precise approved revision and optional resource."""
from .receipts import digest
from .revisions import revision


def selected(permission, evidence):
    selection, = [c for c in evidence['captures'].values() if c['kind'] == 'selection']
    if digest(revision(selection['source']['entry'])) != permission['revision']:
        raise ValueError('captured source differs from the approved revision')


def observed(permission, proposal, evidence):
    selected(permission, evidence)
    captures = [c for c in evidence['captures'].values() if c.get('approved_resource')]
    expected = proposal.get('resource')
    if expected is None:
        if captures:
            raise ValueError('unapproved full-resource evidence')
        return
    capture, = captures
    if (capture['approved_resource'], capture['url'], capture['kind']) != (permission['id'], expected['url'], expected['kind']):
        raise ValueError('observed resource differs from explicit permission')


def resource_limits(evidence):
    return [limit for capture in evidence['captures'].values() if capture.get('approved_resource')
            for limit in capture.get('limitations', [])]
