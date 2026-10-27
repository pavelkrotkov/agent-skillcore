"""Trusted chat bridge commands; research workers have no access to these mutations."""
from .stage_timings import timed
import json
from pathlib import Path

from . import review_decisions, review_outbox, review_receipts, deep_cli


def configure(commands):
    parser = commands.add_parser('review')
    actions = parser.add_subparsers(dest='review_action', required=True)
    actions.add_parser('status')
    deep_cli.configure(actions)
    prepare = actions.add_parser('prepare')
    prepare.add_argument('--batch', required=True)
    prepare.add_argument('--chat', required=True)
    failure = actions.add_parser('failed')
    failure.add_argument('--delivery', required=True)
    failure.add_argument('--reason', required=True)
    for name in ('observe', 'reply'):
        action = actions.add_parser(name)
        action.add_argument('--delivery', required=True)
        action.add_argument('--receipt', type=Path, required=True)
        action.add_argument('--message', required=True)
        if name == 'reply':
            action.add_argument('--human-origin-confirmed', action='store_true', required=True)


@timed("source.review_gate", scope="selected")
def command(db, args):
    handlers = {
        'prepare-research': lambda: deep_cli.prepare(db, args),
        'status': lambda: review_outbox.status(db),
        'prepare': lambda: {'state': 'prepared', 'delivery': review_outbox.prepare(db, args.batch, args.chat)},
        'failed': lambda: review_receipts.failed(db, args.delivery, args.reason),
        'observe': lambda: review_receipts.observe(db, args.delivery, load(args.receipt), args.message),
        'reply': lambda: review_decisions.apply(db, args.delivery, load(args.receipt), args.message,
                                               human_origin_confirmed=args.human_origin_confirmed),
    }
    return handlers[args.review_action]()


def load(path):
    with path.open('rb') as source:
        data = source.read(2 * 1024 * 1024 + 1)
    if len(data) > 2 * 1024 * 1024:
        raise ValueError('use a bounded native chat readback')
    return json.loads(data)
