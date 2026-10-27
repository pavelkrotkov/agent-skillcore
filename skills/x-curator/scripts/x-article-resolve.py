#!/usr/bin/env python3
"""Resolve x.com/i/article/<id> links for the x-curator.

Strategy (reuses TweetHoarder auth/infra; no Playwright/browser):
1. Local archive first: TweetHoarder's raw_json already contains the X Article
   entity (title + preview_text) captured during likes/bookmarks sync.
2. Live fallback: authenticated TweetDetail GraphQL call via the TweetHoarder
   client package (optional; required only when the archive lacks the entity).
3. twikit-mcp fallback: `get_article format=plain` / `get_article_preview` —
   the only headless full-text path for X Articles without a browser.
   Cookies are read by twikit-mcp from ~/.config/twitter-mcp/cookies.json
   (generate it ONCE from TweetHoarder's config; mode 600; never log values).
4. If only title/preview are available, status=partial (source_unavailable
   for full text): the curator scores from preview/context and queues
   high-value items for human review. Never discard solely because the body
   could not be fetched.
Output: JSON {status: ok|partial|unavailable, title, author, text, source}.
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

DB = Path(os.environ.get(
    "X_CURATOR_DB",
    str(Path.home() / ".local/share/tweethoarder/tweethoarder.db"),
))


def article_id(ref: str) -> str | None:
    m = re.search(r"(\d{10,})", ref)
    return m.group(1) if m else None


def _find_article(obj: object) -> dict | None:
    if isinstance(obj, dict):
        # Prefer an article that also carries its enclosing tweet's user, so
        # provenance isn't pulled from an unrelated injected reply/quoted user.
        res = obj.get("article")
        if isinstance(res, dict):
            result = res.get("article_results", {}).get("result", {})
            if result.get("title") or result.get("preview_text") or result.get("content"):
                return result
        for v in obj.values():
            r = _find_article(v)
            if r:
                return r
    elif isinstance(obj, list):
        for item in obj:
            r = _find_article(item)
            if r:
                return r
    return None


def _article_author(obj: object, art: dict) -> tuple[dict, str | None]:
    """Return the article entity paired with the article-bearing tweet's author.

    Walks for a dict that owns BOTH the selected `art` article and a user, so
    provenance never comes from an unrelated injected account.
    """
    if isinstance(obj, dict):
        # This node owns an article equal to the one we found.
        a = obj.get("article")
        if isinstance(a, dict):
            cur = a.get("article_results", {}).get("result", {})
            if cur is art or (cur and cur.get("title") == art.get("title")):
                author = (
                    obj.get("core", {})
                    .get("user_results", {})
                    .get("result", {})
                    .get("legacy", {})
                    .get("screen_name")
                )
                # Article entity may also embed an author field.
                author = author or art.get("author")
                return art, author
        for k, v in obj.items():
            got, author = _article_author(v, art)
            if got and got is art:
                return got, author
    elif isinstance(obj, list):
        for item in obj:
            got, author = _article_author(item, art)
            if got and got is art:
                return got, author
    return art, None


def from_archive(article_tweet_id: str) -> dict | None:
    if not DB.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    except sqlite3.Error:
        # Unreadable/corrupt DB: treat as a miss so the chain continues to
        # twikit/live (Codex: an optional archive tier must not disable the
        # resolution fallback).
        return None
    try:
        rows = conn.execute(
            "SELECT raw_json FROM tweets WHERE id = ? AND raw_json IS NOT NULL",
            (article_tweet_id,),
        ).fetchall()
        if not rows:
            # article_id() only returns digits, but guard anyway: LIKE is
            # parameterized, so this is defense-in-depth, not the injection fix.
            if not article_tweet_id.isdigit():
                return None
            rows = conn.execute(
                "SELECT raw_json FROM tweets WHERE raw_json LIKE ? LIMIT 5",
                (f"%{article_tweet_id}%",),
            ).fetchall()
    except sqlite3.Error:
        return None
    finally:
        conn.close()
    for (raw,) in rows:
        try:
            d = json.loads(raw)
        except Exception:
            continue
        art = _find_article(d)
        if art:
            _, author = _article_author(d, art)
            return {"entity": art, "author": author}
    return None


def _tweethoarder_src() -> Path | None:
    env = os.environ.get("X_TWEETHOARDER_SRC")
    if env:
        return Path(env) / "src"
    default = Path.home() / "src/tweethoarder/src"
    return default if default.exists() else None


def from_live(tweet_id: str) -> dict | None:
    """Live TweetDetail via TweetHoarder.

    Prefers an installed `tweethoarder` package; falls back to a source
    checkout at X_TWEETHOARDER_SRC (default ~/src/tweethoarder/src). The env
    var is operator-set local configuration, not untrusted input.
    """
    try:
        import httpx  # pyright: ignore[reportMissingImports]

        try:
            from tweethoarder.auth.cookies import resolve_cookies  # pyright: ignore[reportMissingImports]
            from tweethoarder.client.base import TwitterClient  # pyright: ignore[reportMissingImports]
            from tweethoarder.client.timelines import build_tweet_detail_url  # pyright: ignore[reportMissingImports]
            from tweethoarder.query_ids.store import (  # pyright: ignore[reportMissingImports]
                QueryIdStore,
                get_query_id_with_fallback,
            )
        except ImportError:
            src = _tweethoarder_src()
            if src is None:
                return None
            sys.path.insert(0, str(src))
            from tweethoarder.auth.cookies import resolve_cookies  # pyright: ignore[reportMissingImports]
            from tweethoarder.client.base import TwitterClient  # pyright: ignore[reportMissingImports]
            from tweethoarder.client.timelines import build_tweet_detail_url  # pyright: ignore[reportMissingImports]
            from tweethoarder.query_ids.store import (  # pyright: ignore[reportMissingImports]
                QueryIdStore,
                get_query_id_with_fallback,
            )

        cookies = resolve_cookies()
        client = TwitterClient(cookies=cookies)
        headers = client.get_base_headers()
        store = QueryIdStore(Path.home() / ".config/tweethoarder/query-ids-cache.json")
        qid = get_query_id_with_fallback(store, "TweetDetail")
        url = build_tweet_detail_url(qid, tweet_id)
        resp = httpx.get(url, headers=headers, timeout=30.0)
        if resp.status_code != 200:
            return None
        data = resp.json().get("data", {})
        tcv = data.get("threaded_conversation_with_injections_v2", {})
        art = _find_article(tcv)
        if not art:
            return None

        _, author = _article_author(tcv, art)
        return {"entity": art, "author": author}
    except Exception:
        return None


def from_twikit(tweet_id: str) -> dict | None:
    """Last-resort: twikit-mcp get_article / get_article_preview.

    twikit-mcp reads its own cookie file (~/.config/twitter-mcp/cookies.json,
    generated once from TweetHoarder's config; mode 600; values never logged).
    """
    try:
        subprocess.run(["twikit-mcp", "--version"], capture_output=True, timeout=30)
    except Exception:
        return None

    for tool in ("get_article", "get_article_preview"):
        try:
            # article_id() in the caller already returns digits-only; this is
            # defense-in-depth so the interpolated arg is never surprising.
            if not tweet_id.isdigit():
                return None
            r = subprocess.run(
                ["twikit-mcp", "call", tool, f"article_id={tweet_id}"]
                + (["format=plain"] if tool == "get_article" else []),
                capture_output=True, text=True, timeout=120,
            )
            if r.returncode != 0 or not r.stdout.strip():
                continue
            try:
                data = json.loads(r.stdout)
            except json.JSONDecodeError:
                # Malformed twikit output: fall through to next tier.
                continue
            text = data.get("plain_text") or data.get("preview_text")
            if not text and tool == "get_article_preview":
                continue
            full = tool == "get_article"
            return {
                "entity": {
                    "title": data.get("title"),
                    "preview_text": text,
                    # Only get_article's plain_text is the full body; a
                    # preview-only result must NOT carry a content mapping,
                    # or the caller would classify it as status "ok".
                    "content": {"plain_text": text} if full else None,
                    "_full": full,
                },
                "author": None,
            }
        except Exception:
            continue
    return None


def extract_text(entity: dict) -> str | None:
    """Full plain text if the content tree is present; else preview_text."""
    chunks: list[str] = []

    def collect(o: object) -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "text" and isinstance(v, str):
                    chunks.append(v)
                else:
                    collect(v)
        elif isinstance(o, list):
            for i in o:
                collect(i)

    collect(entity.get("content"))
    text = "\n\n".join(chunks).strip()
    return text or entity.get("preview_text")


def resolve(ref: str) -> dict:
    tweet_id = article_id(ref)
    if not tweet_id:
        return {"status": "unavailable", "reason": "unparseable reference"}
    src = f"https://x.com/i/article/{tweet_id}"

    hit = from_archive(tweet_id)
    # Archive entity carries only title+preview; if it has no full content,
    # prefer twikit-mcp / live which may return the whole body.
    if hit and "entity" in hit and not hit["entity"].get("content"):
        hit = from_twikit(tweet_id) or from_live(tweet_id) or hit
    else:
        hit = hit or from_twikit(tweet_id) or from_live(tweet_id)
    if not hit:
        # ADR-0001: total failure is source_unavailable — the curator must
        # route valuable/uncertain tweets to review, never silently discard.
        return {
            "status": "unavailable",
            "source": src,
            "note": "source_unavailable: no tier returned title or preview; "
                    "score from tweet context only and queue if valuable",
        }

    entity = hit.get("entity") if isinstance(hit, dict) else None
    # Guard against a fallback returning a dict without an "entity" key.
    if not isinstance(entity, dict):
        return {
            "status": "unavailable",
            "source": src,
            "note": "source_unavailable: no usable article entity returned; "
                    "score from tweet context only and queue if valuable",
        }
    full_content = bool(entity.get("_full")) or (
        "content" in entity and entity.get("content") is not None
    )
    title = entity.get("title")
    text = extract_text(entity)
    status = "ok" if full_content else "partial"
    out = {
        "status": status,
        "title": title,
        "author": hit.get("author"),
        "text": text,
        "source": src,
        "note": None
        if full_content
        else "only title+preview available; score from context and queue if valuable",
    }
    return {k: v for k, v in out.items() if v is not None}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: x-article-resolve <x.com/i/article/URL | tweet-id>")
    print(json.dumps(resolve(sys.argv[1]), indent=1, ensure_ascii=False))
