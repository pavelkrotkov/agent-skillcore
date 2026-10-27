import json
import sys

from .cli import arguments
from .command_lock import command_lock
from .queue import enqueue
from .storage import coverage, open_store
from .live_dispatch import live_dispatch
from .standalone import handles, dispatch as standalone
from . import stage_timings


def main():
    args = arguments()
    if handles(args):
        result = standalone(args)
        print(json.dumps(result, indent=2))
        return 2 if result['state'] == 'blocked' else 0
    db = open_store(args.state)
    try:
        with command_lock(args), stage_timings.command(db, args.command):
            result = dispatch(db, args)
        print(json.dumps(result, indent=2))
        return 2 if isinstance(result, dict) and result["state"] == "blocked" else 0
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__}), file=sys.stderr)
        return 1
    finally:
        db.close()


def dispatch(db, args):
    from . import accounting, batch_report, daily_store, deep_process, index_pending, policy_metrics, recovery, review_cli, wiki_index_result, quick_recovery, video_package, wiki_refresh, retention
    from .article_refresh_store import enable as enable_article_currentness
    handlers = {
        'configure-article-currentness': lambda: enable_article_currentness(db, args.publication, args.reason),
        'retain': lambda: retention.run(db, args.state, apply=args.apply),
        'prepare-video': lambda: video_package.ingest(db, args.account, args.source, args.package, args.reason),
        'recover-quick': lambda: quick_recovery.run(db, args.apply),
        'complete-publication': lambda: recovery.command(db, args),
        'recover-wiki': lambda: recovery.command(db, args),
        'configure-daily': lambda: daily_store.configure(db, args.account, args.chat, args.timezone),
        'research': lambda: deep_process.work(db, args.state, args.approval),
        'review': lambda: review_cli.command(db, args),
        'batches': lambda: batch_report.report(db, args.batch),
        'report': lambda: accounting.report(db, args.state),
        'policy-report': lambda: stage_timings.report(db, args.run_id) if args.run_id else policy_metrics.report(db),
        'queue': lambda: enqueue(db),
        'status': lambda: [coverage(db, row[0]) for row in db.execute('SELECT id FROM collections ORDER BY started')],
        'wiki': lambda: wiki_index_result.command(db,args),
        'zk-refresh': lambda: wiki_refresh.command(db,args),
        'index-pending': lambda: index_pending.run(db, args.state),
    }
    return handlers.get(args.command, lambda: live_dispatch(db, args))()



if __name__ == "__main__":
    sys.exit(main())
