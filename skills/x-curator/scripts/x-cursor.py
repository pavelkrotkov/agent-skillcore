#!/usr/bin/env python3
"""x-curator: emit the next batch of unprocessed liked/bookmarked tweets.

Reads the TweetHoarder SQLite archive, tracks processed tweet IDs in an
append-only JSONL state file, and prints a JSON batch for the curation agent.
The agent calls `mark` after each item is dispositioned.

Paths are environment-configurable (defaults match the canonical setup):
  X_CURATOR_DB     TweetHoarder archive (default ~/.local/share/tweethoarder/tweethoarder.db)
  X_CURATOR_STATE  state dir (default ~/.local/state/x-curator)
"""
import fcntl
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB = Path(os.environ.get(
    "X_CURATOR_DB",
    str(Path.home() / ".local/share/tweethoarder/tweethoarder.db"),
))
STATE_DIR = Path(os.environ.get(
    "X_CURATOR_STATE",
    str(Path.home() / ".local/state/x-curator"),
))
PROCESSED = STATE_DIR / "processed.jsonl"
LOCKFILE = STATE_DIR / ".lock"

DISPOSITIONS = {"ingest", "update", "discard", "review"}
# reservation is an internal mark written by `next` so a concurrent/overlapping
# run cannot re-emit the same tweet and overwrite an immutable raw capture.
_RESERVED = "reserved"


class _Lock:
    """Exclusive advisory lock serializing next() vs next()/mark().

    Prevents two overlapping runs from emitting the same batch (Codex P2:
    reserve emitted IDs / serialize active runs). fcntl is Linux-only, which
    matches the skill's platforms: [linux].
    """

    def __init__(self) -> None:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self._f = open(LOCKFILE, "w")

    def __enter__(self) -> "_Lock":
        fcntl.flock(self._f.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc) -> None:
        fcntl.flock(self._f.fileno(), fcntl.LOCK_UN)
        self._f.close()


def load_processed() -> set[str]:
    if not PROCESSED.exists():
        return set()
    out = set()
    for line in PROCESSED.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            out.add(rec["id"])
        except (json.JSONDecodeError, KeyError, TypeError):
            # Fail closed: silently skipping a corrupt line would drop that
            # tweet's id from the checkpoint, so the next run would re-emit an
            # already-processed tweet and overwrite its immutable raw capture
            # (Codex P2). Abort and name the line so the operator can repair.
            sys.exit(
                "error: corrupt processed-state line in "
                f"{PROCESSED}: {line[:120]!r}; refusing to run"
            )
    return out


def _append(rec: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with PROCESSED.open("a") as f:
        f.write(json.dumps(rec) + "\n")


def _ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


def fetch_unseen(limit: int) -> list[dict]:
    if not DB.exists():
        sys.exit(f"error: TweetHoarder DB not found at {DB} — aborting without marking anything")
    if limit < 1:
        sys.exit("error: limit must be a positive integer")

    with _Lock():
        done = load_processed()
        try:
            conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        except sqlite3.Error as e:
            sys.exit(f"error: cannot open archive at {DB}: {e}; aborting (nothing marked)")
        try:
            output = conn.execute(
                """
                SELECT COUNT(DISTINCT t.id)
                FROM tweets t JOIN collections c ON t.id = c.tweet_id
                WHERE c.collection_type IN ('like', 'bookmark')
                """
            ).fetchone()
            total = output[0] if output else 0
            if total == 0:
                sys.exit(
                    "error: archive has no like/bookmark rows — unpopulated or broken "
                    "sync; refusing to report 'nothing new' (set X_CURATOR_DB to override the DB path)"
                )
            rows = conn.execute(
                """
                SELECT t.id, t.text, t.author_username, t.created_at,
                       t.like_count, t.retweet_count, t.reply_count,
                       t.urls_json, t.media_json,
                       GROUP_CONCAT(DISTINCT c.collection_type) AS collections
                FROM tweets t JOIN collections c ON t.id = c.tweet_id
                WHERE c.collection_type IN ('like', 'bookmark')
                GROUP BY t.id
                ORDER BY t.created_at DESC
                """
            ).fetchall()
        finally:
            conn.close()

        batch = []
        seen: set[str] = set()
        for r in rows:
            tweet_id = str(r[0])
            if tweet_id in done or tweet_id in seen:
                continue
            seen.add(tweet_id)
            urls, media = [], []
            try:
                urls = json.loads(r[7]) if r[7] else []
                media = json.loads(r[8]) if r[8] else []
            except (json.JSONDecodeError, TypeError):
                # Malformed JSON in a tweet's urls/media blobs: degrade to empty
                # for this tweet instead of crashing the whole batch (AWS Q).
                urls, media = [], []
            batch.append(
                {
                    "id": tweet_id,
                    "author": r[2],
                    "created_at": r[3],
                    "url": f"https://x.com/{r[2]}/status/{tweet_id}",
                    "collection": r[9],
                    "engagement": {"likes": r[4], "rts": r[5], "replies": r[6]},
                    "text": r[1],
                    "urls": urls,
                    "media": media,
                }
            )
            # Reserve the id BEFORE returning so an overlapping run's `next`
            # skips it; the final disposition is appended later via `mark`.
            _append({"id": tweet_id, "disposition": _RESERVED, "note": "reserved by next", "ts": _ts()})
            if len(batch) >= limit:
                break
        return batch


def mark(tweet_id: str, disposition: str, note: str = "") -> None:
    if not tweet_id or not tweet_id.isdigit():
        sys.exit("error: tweet id must be numeric")
    if disposition not in DISPOSITIONS:
        sys.exit(f"error: disposition must be one of {sorted(DISPOSITIONS)}")
    with _Lock():
        _append({"id": tweet_id, "disposition": disposition, "note": note, "ts": _ts()})


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "next"
    if cmd == "next":
        try:
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        except ValueError:
            sys.exit("error: limit must be an integer")
        print(json.dumps(fetch_unseen(limit), indent=1))
    elif cmd == "mark":
        if len(sys.argv) < 4:
            sys.exit("usage: x-cursor mark ID DISPOSITION [NOTE]")
        mark(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
        print(f"marked {sys.argv[2]}: {sys.argv[3]}")
    elif cmd == "count":
        total = len(load_processed())
        print(f"{total} processed")
    else:
        sys.exit("usage: x-cursor next [N] | mark ID DISPOSITION [NOTE] | count")
