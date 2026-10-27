"""Commands that need the existing authenticated X session."""
from .transport import XClient
from .collect import collect


def live_dispatch(db, args):
    client = XClient()
    try:
        if args.command == 'recover':
            from .recovery import grant
            return grant(db, client.account, args.source, args.reason, args.request_extra)
        if args.command == 'supervise':
            from .supervisor import run
            return run(db, args.state, client, args.max_items, args.max_sources, args.seconds)
        if args.command == "work":
            from .worker import work
            return work(db, args.state, client, args.max_items, args.lease_seconds, args.defer_index, args.unspent_only)
        return collect(db, client, args.kind, args.max_requests, args.new_run)
    finally:
        client.close()
