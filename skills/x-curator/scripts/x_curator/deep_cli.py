"""Explicit research execution and separately proposed extensions/resource scopes."""


def configure(actions):
    parser = actions.add_parser('prepare-research')
    parser.add_argument('--account', required=True)
    parser.add_argument('--chat', required=True)
    parser.add_argument('--run')
    parser.add_argument('--seconds', type=int, default=600)
    parser.add_argument('--native-search', action='store_true')
    parser.add_argument('--resource-kind', choices=('pdf', 'video'))
    parser.add_argument('--resource-url')


def prepare(db, args):
    from . import deep_review
    resource = None
    if args.resource_kind or args.resource_url:
        if not all((args.run, args.resource_kind, args.resource_url)):
            raise ValueError('resource approval requires a named run, exact type and URL')
        resource = {'kind': args.resource_kind, 'url': args.resource_url}
    return {'state': 'prepared', 'delivery': deep_review.prepare(db, args.account, args.chat, args.run, args.seconds, resource, native=args.native_search)}


def options(run, seconds, resource):
    if type(seconds) is not int or not 1 <= seconds <= 14400:
        raise ValueError('proposed budget must be between 1 and 14400 seconds')
    if not run and (seconds != 600 or resource is not None):
        raise ValueError('extensions and resource requests must identify one prior run')
    if resource is not None:
        from .deep_resource import validate
        validate(resource)
