"""Read-only commands bypass store initialization and command telemetry."""


def handles(args):
    return args.command in ('diagnose-publication', 'migrate-quick') or (args.command == 'retain' and not args.apply)


def dispatch(args):
    if args.command == 'retain':
        from .retention import preview
        return preview(args.state)
    if args.command == 'diagnose-publication':
        from .publication_diagnostics import diagnose
        return diagnose(args.state, args.publication)
    from . import policy_migration
    return policy_migration.apply(args.state, args.apply) if args.apply else policy_migration.preview(args.state)
