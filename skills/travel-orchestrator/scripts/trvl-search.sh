#!/usr/bin/env bash

set -u

if [ "$#" -eq 0 ]; then
  echo "usage: trvl-search.sh <trvl arguments including --format json>" >&2
  exit 2
fi

for tool in trvl jq; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Missing required command: $tool" >&2
    exit 1
  fi
done

skill_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd) || {
  echo "Failed to locate the travel-orchestrator skill directory" >&2
  exit 1
}

trvl_raw=$(mktemp "${TMPDIR:-/tmp}/travel-orchestrator.XXXXXX") || {
  echo "Failed to create temporary file" >&2
  exit 1
}

cleanup() {
  rm -f -- "$trvl_raw"
}
trap cleanup EXIT HUP INT TERM

# Defaults are conservative, while explicit 0 values opt into the documented behavior.
: "${TRVL_NO_BROWSER_COOKIES:=1}"
: "${TRVL_NO_TIER2_CDP:=1}"
: "${TRVL_NO_TELEMETRY:=1}"
export TRVL_NO_BROWSER_COOKIES TRVL_NO_TIER2_CDP TRVL_NO_TELEMETRY

# Keep "$@" quoted so each caller argument remains one argv element; never use eval.
if ! trvl "$@" >"$trvl_raw"; then
  echo "trvl command failed" >&2
  exit 1
fi

if ! jq -e 'type == "object"' "$trvl_raw" >/dev/null; then
  echo "trvl returned invalid or non-object JSON" >&2
  exit 1
fi

if ! jq -f "$skill_dir/scripts/trvl-compact.jq" "$trvl_raw"; then
  echo "jq processing failed" >&2
  exit 1
fi
