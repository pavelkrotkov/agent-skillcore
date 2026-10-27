#!/usr/bin/env bash
# Install x-curator helper scripts onto PATH and verify dependencies.
# Run once per machine from the skill directory (or anywhere with --skill-dir).
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET_BIN="${X_CURATOR_BIN_DIR:-$HOME/.local/bin}"
mkdir -p "$TARGET_BIN"

for s in x-cursor.py x-article-resolve.py; do
  # Install as x-cursor / x-article-resolve (strip .py from the target name)
  name="${s%.py}"
  cp "$SCRIPT_DIR/$s" "$TARGET_BIN/$name"
  chmod +x "$TARGET_BIN/$name"
done
echo "installed into $TARGET_BIN"

# Dependency checks (non-fatal; resolver degrades gracefully)
if ! command -v twikit-mcp >/dev/null 2>&1; then
  echo "WARN: twikit-mcp not found. For full X Article text, run: uv tool install twikit-mcp"
  echo "      and create ~/.config/twitter-mcp/cookies.json (auth_token + ct0, mode 600) from TweetHoarder's config."
fi
if [ ! -f "$HOME/.local/share/tweethoarder/tweethoarder.db" ]; then
  echo "WARN: TweetHoarder DB not found at default path (set X_CURATOR_DB to override)."
fi

echo "smoke test:"
"$TARGET_BIN/x-cursor" count