#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'USAGE'
Usage: github-repo-maintenance.sh <command> [args...]

Commands:
  prune     Identify or delete obsolete branches.
  protect   Ensure a managed ruleset protects default branches.

Run '<command> --help' for command-specific options.
USAGE
}

(($#)) || { usage >&2; exit 2; }
command=$1
shift

case "$command" in
  prune) exec bash "$SCRIPT_DIR/prune-branches.sh" "$@" ;;
  protect) exec bash "$SCRIPT_DIR/protect-default-branches.sh" "$@" ;;
  -h|--help|help) usage ;;
  *) echo "unknown command: $command" >&2; usage >&2; exit 2 ;;
esac
