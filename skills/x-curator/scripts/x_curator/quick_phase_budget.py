"""Bind both phases to the original check, cutoff, acquisition policy and source."""
from . import quick_store


def verify(check, row, initial, final, receipt):
    actual = (initial['role'], initial['policy'], initial['phase'], initial['check'], initial['deadline'],
              final['phase']['name'], final['check'], final['deadline'], final['search_mode'], final['linked'])
    expected = ('factcheck', quick_store.POLICY,
                dict(name='evidence', cutoff=min(check['started'] + 80, check['deadline']), image_policy='deferred-to-final'),
                check['id'], check['deadline'], 'final', check['id'], check['deadline'], 'captured-phase/v1', True)
    if actual != expected:
        raise ValueError('phase changed the original quick-check allowance or acquisition policy')
    if (initial['bundle']['account'], initial['bundle']['source']) != (final['bundle']['account'], final['bundle']['source']):
        raise ValueError('foreign evidence-phase context')
    timing(check, row, initial['phase']['cutoff'], receipt)


def timing(check, row, cutoff, receipt):
    stopped = receipt['stopped']
    if not check['started'] <= row['started'] <= stopped <= row['finished'] <= check['deadline']:
        raise ValueError('evidence phase exceeded the original deadline')
    if stopped > cutoff + 1 or (receipt['status'] == 'cutoff' and stopped < cutoff):
        raise ValueError('evidence phase did not stop at the controller cutoff')
    if receipt['status'] not in ('completed', 'cutoff'):
        raise ValueError('invalid evidence-phase disposition')
