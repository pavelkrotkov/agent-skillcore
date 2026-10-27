# Retired archive workflow

Historical reference only. Do not schedule or execute this workflow for fresh curation.
Use [bounded fact-checks](bounded-fact-check.md).

Turn unseen X likes/bookmarks (TweetHoarder SQLite archive) into curated wiki
knowledge. Run daily via cron; also usable on demand.

## Setup (once per machine)

```bash
bash <skill>/scripts/install.sh   # installs x-cursor + x-article-resolve onto PATH
uv tool install twikit-mcp        # optional but recommended: full X Article text
```

Create `~/.config/twitter-mcp/cookies.json` (mode 600) with `auth_token` +
`ct0` copied from TweetHoarder's config — never commit or echo these values.
The scripts read env overrides `X_CURATOR_DB` (archive path),
`X_CURATOR_STATE` (state dir), and `X_TWEETHOARDER_SRC` (TweetHoarder source
checkout for the live-TweetDetail tier; an installed `tweethoarder` package is
preferred automatically when importable).

Configure the daily cron (Hermes): job with `deliver=telegram` and
`attach_to_session=true`; the Telegram platform needs
`extra.cron_continuable_surface: in_channel` so replies route back to the
job's session (see `adr/0002-telegram-review-delivery.md`). The
cron prompt should be self-contained: "Load the x-curator skill and follow it.
If the skill cannot be loaded, do NOT make any disposal decisions — stop and
report the load failure; default is ingest-or-review, never discard."

## Inputs / State

- Archive DB (read-only): `~/.local/share/tweethoarder/tweethoarder.db`
- Batch/state tool: `x-cursor`
  - `x-cursor next N` → JSON batch of unprocessed tweets (newest first)
  - `x-cursor mark <id> <ingest|update|discard|review> [note]` → append-only state
  - `x-cursor count` → processed count
- Wiki: `${WIKI_PATH:-~/wiki}` — read `SCHEMA.md`, `index.md`, recent `log.md`
  FIRST. `templates/wiki-schema.md` is a starting schema for a new wiki.
- Review queue: `<wiki>/_review/` (one `.md` per item needing human decision)
- Raw captures: `<wiki>/raw/x/<tweet-id>.md`

## Workflow (per tweet)

1. **Orient**: read SCHEMA.md + index.md once per run before processing.
2. Read the tweet text/urls/media from the batch item. Fetch linked article
   with `web_extract` only if it is central to the claim (skip for
   one-liners/memes). Thread context optional if needed.
3. Extract main factual claims; label fact / opinion / prediction.
4. **Light verification ONLY**: ≤5 web searches, require ≥2 independent sources
   to reach veracity A or B (prefer primary, stop at adequate confidence).
   Single-source (veracity C) is NOT auto-ingested: high-value single-source
   claims go to the review queue instead (see step 7). If the claim is opinion
   or unfalsifiable, skip verification and grade veracity `N-A`.
5. Score:
   - veracity: A (primary-confirmed) / B (corroborated) / C (single-source /
     partially confirmed) / D (contradicted in part) / F (false) / N-A (opinion)
   - value: 1–5 (usefulness to the wiki domain)
   - novelty: new / extends / conflicts / duplicate / supersedes
     (check existing wiki pages via index.md + search BEFORE scoring)
6. Save a raw capture to `raw/x/<id>.md`: frontmatter
   (`source_url`, `author`, `ingested`, `collection`) + tweet text + expanded
   links + verification notes + scores. Never modify it afterwards.
7. Dispose per SCHEMA.md:
   - any NEW topic with real claims AND veracity A/B → **ingest** (create entity/concept/comparison page).
     NO out-of-domain discard — a topic the user liked is in scope by definition.
   - a NEW topic graded C (single-source) is NOT auto-ingested — it follows the
     review rule below (high-value C/D/F → review queue).
   - claims that extend an existing page → **update** that page.
   - **discard** ONLY for true duplicate (same topic already captured) or obvious spam
     (empty / no claim / pure engagement bait).
   - C/D/F + high value or meaningful conflict → **review** queue.
   - **N-A (opinion/unfalsifiable)** → value/novelty rule directly: 4–5 ingest
     (as labeled opinion/prediction), 2–3 update else discard, 1 discard,
     conflict → review. N-A never blocks a high-value opinion from ingestion.
   - Opinions/predictions are ingested but labeled inline "opinion"/"prediction"
     with honest confidence.
8. Ingest = synthesize into wiki pages (tweet is a SOURCE, not the knowledge):
   wikilinks ≥2, tags from taxonomy, provenance line back to the X URL,
   opinions/predictions clearly labeled inline, confidence set honestly,
   contradictions never overwritten (use `contradictions:`/`contested:`).
9. Update index.md counts/date and append log.md entries.
10. Mark state: `x-cursor mark <id> ingest|update|discard|review "<one-line note>"`.

## Run shape

- Default batch: 10 items/run (cron) — keep bounded; leftover items wait for tomorrow.
- Never expose cookie/auth material. The archive is read-only.

## Review Queue — Telegram is the UI

`<wiki>/_review/*.md` is the durable internal/audit queue; the human NEVER
opens these files manually. Each item file carries a status line:
`status: open` or `status: resolved YYYY-MM-DD (<decision>)`.

Once per daily run, if unresolved (open) items exist, send ONE compact
Telegram digest (via the cron job's own gateway delivery — see ADR-0002):
- numbered items, each terse: short title/@source; claim; veracity/value/
  novelty; why it needs review (≤1 line); 1–2 sentence research summary;
  recommended action.
- close with: 'Reply e.g. "accept 1,3; reject 2", "research 1 more", "accept all".'
- Send nothing when the queue is empty. Never tell the user to open _review files.

When the user replies with decisions: apply them (ingest/discard per
SCHEMA.md), rewrite each resolved file's status line, update index/log,
re-mark x-cursor if the disposition changed. "research N more" = one bounded
extra research pass (max 3 searches); resolve directly if clean, else keep
open for the next digest.

## Fail-safe (REQUIRED)

If the skill fails to load for ANY reason, OR web/network verification is
unavailable, the run MUST NOT mass-discard. A dead skill or dead network is
never a license to bin items as "out-of-domain". Default under any failure is
**ingest-or-review**, never discard. Route every uncertain, single-source, or
unverifiable claim to the review queue (`<wiki>/_review/`). Only true
duplicates or obvious spam are ever discarded — and that judgment must be made
per-item, never by blanket rule.

## X Article handling (`x.com/i/article/<id>` links)

Never discard a candidate merely because its article can't be fetched by the
normal web extractor. Instead (see `adr/0001-x-article-resolution-chain.md`):

1. Run `x-article-resolve <url-or-id>`. Resolution chain: TweetHoarder
   archive raw_json (title/preview) → twikit-mcp `get_article format=plain`
   (full text) → `get_article_preview` → live TweetDetail. Never use a
   browser/Playwright for articles.
2. `status: ok` → full text; proceed with normal verification.
3. `status: partial` → only title+preview. Score from preview/tweet context,
   save raw capture noting `source_unavailable` for full text, then:
   - value ≥3 or uncertain → **review queue** (`_review/`)
   - low-value → discard as usual
4. `status: unavailable` → every tier failed (no title or preview). Same
   routing as partial: score from tweet context only, queue if valuable or
   uncertain, note `source_unavailable`. Never discard an article tweet solely
   because its body could not be fetched.
5. Record the disposition honestly (e.g. `review` or `ingest` with note
   "title+preview only").

## Pitfalls

- Don't re-research processed items — the cursor is the checkpoint; append-only.
- Don't create pages for passing mentions (Page Thresholds in SCHEMA.md).
- t.co links in `urls_json` carry `expanded_url` — use that for extraction;
  if it matches `x.com/i/article/<id>`, use x-article-resolve instead of web_extract.
- If the TweetHoarder DB is missing/empty, abort without marking anything
  (x-cursor exits with an error by design).
- A digest sent via raw Bot API (sendMessage) from an agent session bypasses
  gateway session routing — user replies then land in the wrong conversation.
  ADR-0002: cron gateway delivery only.
