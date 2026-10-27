# Wiki Schema

## Domain
AI/ML research, LLM tooling and agents, software engineering, and notable tech commentary — curated primarily from the user's X (Twitter) likes/bookmarks via TweetHoarder, verified against primary sources.

## Conventions
- File names: lowercase, hyphens, no spaces.
- Every page starts with YAML frontmatter (see below).
- `[[wikilinks]]`: minimum 2 outbound links per page; existing pages must link back.
- Bump `updated` on any edit. Every new/updated page goes into `index.md`; every action into `log.md`.
- Provenance: X-sourced claims carry a source line of the form
  `> Source: [X @user](https://x.com/user/status/<id>) — collected <INGESTION-DATE> — veracity A, value 4`
  (use the date the item is curated, since x-cursor exposes the tweet's
  `created_at` and collection type but not when the like/bookmark was
  recorded) plus `^[raw/x/<id>.md]` markers on multi-source pages.

## Frontmatter
```yaml
---
title:
created:
updated:
type: entity | concept | comparison | query
tags: []
sources: [raw/x/<tweet-id>.md]
confidence: high | medium | low   # optional but recommended for single-source or fast-moving claims
contested: true                   # when unresolved contradictions exist
contradictions: []
---
```

## Tag Taxonomy
- model, architecture, benchmark, training, inference, agents, tooling, data,
  alignment, evaluation, company, lab, person, open-source, comparison,
  controversy, prediction, economics, security

Rule: every tag must appear here first. Add new tags to SCHEMA.md before use.

## Page Thresholds
- Create a page when an entity/concept appears in 2+ sources OR is central to one high-value source.
- Add to existing page otherwise. Don't page passing mentions. Split pages over ~200 lines.
- Archive superseded pages to `_archive/`.

## Update Policy
1. Newer sources generally supersede older ones — note dates.
2. Genuinely contradictory claims: keep both with dates + sources, set
   `contradictions:` frontmatter and `contested: true` where unresolved.
3. Never silently overwrite uncertainty; lower `confidence` instead.

## Curation Dispositions (x-curator)
- `ingest`    — any liked source with real claims about a NEW topic AND veracity A/B
               (≥2 independent sources) → create a wiki page.
               EVERY new topic with A/B veracity gets a page. There is no out-of-domain discard.
- `update`    — claims that extend an existing page (same entity/topic already captured).
- `discard`   — ONLY true duplicates (same claim/topic already captured) or obvious spam
               (empty post, no claim, pure engagement bait). NOT for "out of scope".
- `review`    — veracity C/D/F + high value or meaningful conflict, single-source (C)
               new topic, or source is valuable but couldn't be fully fetched
               → review queue (status: open).
- Opinions/predictions are ingested but labeled "opinion" / "prediction" inline and
  tagged `prediction` where applicable; confidence set honestly.
- **N-A items (opinion/unfalsifiable)**: apply a value/novelty rule directly —
  value 4–5 → ingest (as labeled opinion/prediction), value 2–3 → update an
  existing page if relevant else discard, value 1 → discard, meaningful
  conflict → review. N-A never blocks ingestion of a high-value opinion.
