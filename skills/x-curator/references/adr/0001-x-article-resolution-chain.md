# ADR-0001 — X Article resolution: authenticated cookie GraphQL + twikit-mcp, never browser automation

## Status

Accepted

## Context

The curator processes `x.com/i/article/<id>` links (X-native "Articles"). The
public HTML endpoint returns 404, and the normal web extractor gets nothing,
so candidates were initially discarded for being unfetchable — losing real
content. TweetHoarder (cookie-authenticated GraphQL) was tried next: the
`TweetDetail` op returns the article *entity* (title + preview_text) but not
the body. A public "ArticleEntityResultByRestId" op exists but is the *editor*
op (author-only). The X web client resolves articles through a two-hop reader
(`ArticleRedirectScreenQuery` → content fetch) that no standalone public op
exposes, and its query IDs rotate (must be scraped from abs.twimg.com bundles
when they do).

Options: (a) Playwright/headless browser rendering — heavy, slow, brittle,
against the project's lightweight constraint; (b) scrape-and-rotate the
web-client's private ops ourselves — duplicates what an upstream package
already maintains; (c) delegate full-text retrieval to twikit-mcp, a uv-tool
that implements the two-hop reader with self-refreshing query IDs, sharing the
same `auth_token`/`ct0` cookies TweetHoarder already uses.

## Decision

Resolution chain in `scripts/x-article-resolve.py`:

1. TweetHoarder archive `raw_json` (title + preview entity, free).
2. twikit-mcp `get_article format=plain` (full text), then `get_article_preview`.
3. Live TweetDetail GraphQL via the TweetHoarder client package (optional; only
   adds the title/preview entity from the web flow).

Cookies are shared, never duplicated: twikit-mcp reads
`~/.config/twitter-mcp/cookies.json` (auth_token + ct0), generated once from
TweetHoarder's config at mode 600; values are never logged or committed.

If all tiers fail, the item is `source_unavailable` (status: `unavailable`
with an explanatory note) and the curator scores from tweet context and
routes valuable/uncertain items to the review queue — it is NEVER discarded
solely because the body was unfetchable.

## Consequences

- Full article text is retrievable headlessly (verified: 14.6 KB and 14.8 KB
  bodies retrieved for two previously-unfetchable articles).
- twikit-mcp becomes a soft dependency: missing tool degrades to
  title+preview rather than failing; `install.sh` warns and documents
  `uv tool install twikit-mcp`.
- Query-ID rotation is upstream's problem, not ours (twikit-mcp refreshes
  them from public bundles).
- A second cookie file exists on disk (mode 600, secret). It must never be
  committed or echoed; regeneration is a one-liner from TweetHoarder's config.