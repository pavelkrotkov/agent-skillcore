---
name: x-curator
description: "Use when curating X likes/bookmarks into the llm-wiki."
metadata:
  version: 0.1.0
  platforms: [linux]
  hermes:
    tags: [wiki, twitter, curation, knowledge-base]
    category: research
---

# X Curator

Use the operator-configured private corpus and reviewed runtime. Legacy archive
imports require explicit authorization; never reset consumed budgets. All selected
topics are in scope.

1. Run each item through a [bounded fact-check](references/bounded-fact-check.md):
   native search targets three queries with recorded observed usage; new text checks have a 120-second hard deadline; source-bound verified prepared-video
   checks have 180 seconds. Both include context, startup, previews and finalization; acquisition
   still stops at 80 seconds. Persisted historical deadlines and consumed attempts never renew. Historical controller checks
   retain hard three queries and approved deep research retains hard twelve.
   One relevant authoritative primary source or two independent credible origins
   supports factual admission. Preserve useful supported parts and attributed opinions.
2. Publish supported knowledge and immediately rebuild the deterministic verified-source
   index with zero organizer calls. Keep central disproof out of the wiki; semantic
   organization is optional and requires explicit `wiki` or `--max-sources N` use.
   Keep inconclusive claims and processing failures visible outside the wiki.
3. Process stable backlog cohorts of fifty alongside daily fresh-arrival cohorts.
   Pending decisions do not stop other items. Two source-worker slots are shared
   by quick checks and explicitly approved research.
4. Deliver one consolidated decision batch to the originating chat using the
   [native approval bridge](references/chat-approvals.md). Prepared is not delivered;
   queued is not observed. Never infer a human approval from another agent or schedule.
5. Deep research requires an exact item/revision/question/scope/budget approval.
   Default proposal: 600 seconds. Full PDFs/videos and extensions require separate
   explicit scope. Do not automatically launch readers, transcription or deep work.
6. Audit publications and the connected wiki. Report captured coverage separately
   from historical completeness, which remains unproven.
7. Keep storage bounded with the [retention policy](references/fresh-rebuild.md#storage-retention).
   Preview with `retain`; use `retain --apply` for expired verified copies. Never delete
   canonical source evidence or reset consumed attempts to save space.
8. Inspect private stage timings with `policy-report --run latest` (or an exact run ID):
   this reads recorded spans without a new source proof audit or wiki rebuild.
   The default `policy-report` also includes the latest timings. Older runs remain incomplete.

[Rollout](references/bounded-rollout.md) covers dry-run migration, activation,
measurements and rollback. [Fresh collection](references/fresh-rebuild.md) covers
private storage and intake. [Historical implementation](references/legacy-fresh.md)
and [retired archive workflow](references/legacy-archive.md) exist only for receipt
interpretation and explicit maintenance; they are not current default instructions.

Use the configured ChatGPT subscription with the reviewed `gpt-5.6-sol` profile
and high reasoning.
No provider/model fallback. Keep credentials, source identities, approval routing,
content, receipts and operational reports outside Git and public issue comments.
