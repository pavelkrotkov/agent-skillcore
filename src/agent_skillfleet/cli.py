"""Command-line entry point used by the small scripts under bin/."""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

if __package__ in {None, ""}:  # direct execution from bin scripts
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_skillfleet.core import (  # noqa: E402
    FleetError,
    Paths,
    _yaml_dump,
    activate_runtime,
    assemble_runtime,
    check_dirty,
    check_main_synced,
    diff_locks,
    doctor,
    install_links,
    load_manifest,
    load_lock,
    resolve_updates,
    run_native_commands,
)
from agent_skillfleet.validation import validate_reference, validate_runtime, validate_source  # noqa: E402


def _paths(args: argparse.Namespace) -> Paths:
    repo = Path(args.repo).resolve() if args.repo else None
    return Paths.from_environment(repo)


def _print(values: list[str]) -> None:
    for value in values:
        print(value)


def command_validate(args: argparse.Namespace) -> int:
    paths = _paths(args)
    if args.runtime:
        domain, messages = "runtime", validate_runtime(paths)
    elif args.reference:
        domain, messages = "reference", validate_reference(paths)
    else:
        domain, messages = "source", validate_source(paths)
    _print([f"✓ {domain} validation", *[f"✓ {message}" for message in messages]])
    return 0


def command_doctor(args: argparse.Namespace) -> int:
    paths = _paths(args)
    messages, errors = doctor(paths, fetch=args.fetch)
    _print(messages)
    return 1 if errors else 0


def command_install_links(args: argparse.Namespace) -> int:
    paths = _paths(args)
    _print(install_links(paths, dry_run=args.dry_run))
    return 0


def _candidate_runtime(paths: Paths, candidate: dict) -> tuple[Path, tempfile.TemporaryDirectory[str]]:
    temp = tempfile.TemporaryDirectory(prefix="agent-skillfleet-candidate-")
    candidate_root = Path(temp.name) / "runtime"
    release = assemble_runtime(paths, runtime=candidate_root, activate=False, lock=candidate)
    return release, temp


def command_sync(args: argparse.Namespace) -> int:
    paths = _paths(args)
    if args.dry_run:
        print("would verify clean main, fast-forward from origin/main, assemble the locked runtime, and repair managed links")
        return 0
    if check_dirty(paths):
        raise FleetError("refusing to sync: canonical checkout is dirty")
    _print(check_main_synced(paths))
    release = assemble_runtime(paths, activate=False)
    validate_runtime(paths, release)
    activate_runtime(paths.runtime, release)
    _print(install_links(paths))
    run_native_commands(load_manifest(paths), operation="update", allow=args.allow_native)
    _print(doctor(paths)[0])
    return 0


def command_bootstrap(args: argparse.Namespace) -> int:
    paths = _paths(args)
    required = ["git", "python3"]
    missing = [name for name in required if not shutil.which(name)]
    if missing:
        raise FleetError(f"missing prerequisites: {', '.join(missing)}")
    if args.dry_run:
        print(f"would create cache {paths.cache}, runtime {paths.runtime}, and state {paths.state}")
        print("would fetch locked external repositories, validate a candidate, activate it, and install links")
        return 0
    paths.cache.mkdir(parents=True, exist_ok=True)
    paths.runtime.mkdir(parents=True, exist_ok=True)
    paths.state.mkdir(parents=True, exist_ok=True)
    release = assemble_runtime(paths, activate=False)
    validate_runtime(paths, release)
    activate_runtime(paths.runtime, release)
    _print(install_links(paths))
    run_native_commands(load_manifest(paths), operation="install", allow=args.allow_native)
    _print(doctor(paths)[0])
    return 0


def command_update(args: argparse.Namespace) -> int:
    paths = _paths(args)
    candidate, updates = resolve_updates(paths, dry_run=args.dry_run)
    if not updates:
        print("✓ no upstream updates available")
        return 0
    print("Upstream updates available:")
    for update in updates:
        print(f"  {update['name']}: {update['old'][:12]} -> {update['new'][:12]} ({update['repo']})")
    if args.dry_run:
        print("dry-run: lockfile and production runtime were not changed")
        return 2 if args.check else 0
    candidate_path = paths.repo / "external" / "skills.lock.candidate"
    candidate_path.write_text(_yaml_dump(candidate), encoding="utf-8")
    print(f"✓ wrote review candidate to {candidate_path}")
    release, temp = _candidate_runtime(paths, candidate)
    try:
        validate_runtime(paths, release, lock=candidate)
    finally:
        temp.cleanup()
    print("✓ candidate runtime materialized and validated")
    if args.apply:
        paths.lockfile.write_text(_yaml_dump(candidate), encoding="utf-8")
        print(f"✓ wrote candidate lockfile to {paths.lockfile}")
    else:
        print("check: no files changed; use --apply to write the candidate lockfile")
    return 2 if args.check else 0


def command_diff(args: argparse.Namespace) -> int:
    paths = _paths(args)
    old = Path(args.old) if args.old else paths.lockfile
    new = Path(args.new) if args.new else paths.repo / "external" / "skills.lock.candidate"
    if not new.exists():
        raise FleetError(f"candidate lockfile does not exist: {new}; pass --new explicitly")
    lines = diff_locks(paths, old, new)
    _print(lines or ["no external skill differences"])
    return 0


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skillfleet")
    parser.add_argument("--repo", help="repository checkout to operate on")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate")
    modes = validate.add_mutually_exclusive_group()
    modes.add_argument("--source", action="store_true", help="offline source/manifest validation (default)")
    modes.add_argument("--runtime", action="store_true", help="validate the materialized deployed runtime")
    modes.add_argument("--reference", action="store_true", help="explicitly invoke the external skills-ref validator")
    modes.add_argument("--manifest-only", action="store_true", help="deprecated alias for --source")
    validate.set_defaults(function=command_validate)

    doctor_parser = sub.add_parser("doctor")
    doctor_parser.add_argument("--fetch", action="store_true", help="refresh cached upstream refs while checking")
    doctor_parser.set_defaults(function=command_doctor)

    links = sub.add_parser("install-links")
    links.add_argument("--dry-run", action="store_true")
    links.set_defaults(function=command_install_links)

    sync = sub.add_parser("sync")
    sync.add_argument("--dry-run", action="store_true")
    sync.add_argument("--allow-native", action="store_true")
    sync.set_defaults(function=command_sync)

    bootstrap = sub.add_parser("bootstrap")
    bootstrap.add_argument("--dry-run", action="store_true")
    bootstrap.add_argument("--allow-native", action="store_true")
    bootstrap.set_defaults(function=command_bootstrap)

    update = sub.add_parser("update")
    update_modes = update.add_mutually_exclusive_group()
    update_modes.add_argument("--check", action="store_true")
    update_modes.add_argument("--apply", action="store_true")
    update_modes.add_argument("--dry-run", action="store_true")
    update.set_defaults(function=command_update)

    diff = sub.add_parser("diff")
    diff.add_argument("--old")
    diff.add_argument("--new")
    diff.set_defaults(function=command_diff)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.function(args))
    except FleetError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
