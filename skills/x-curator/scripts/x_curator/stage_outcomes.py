"""Outcome classification for durable pipeline stage receipts."""
def exception_outcome(exc):
    if type(exc).__name__ in ('DeadlineExceeded', 'TimeoutExpired', 'TimeoutError'):
        return 'timeout'
    return 'interrupted' if isinstance(exc, (KeyboardInterrupt, SystemExit)) else 'failed'


def final_outcome(context, outcome):
    if outcome != 'completed':
        return outcome
    if context.get('skipped', False):
        return 'skipped'
    if context.get('result_state') in ('failed', 'blocked', 'provider_blocked', 'retry', 'needs_action'):
        return 'failed'
    return outcome
