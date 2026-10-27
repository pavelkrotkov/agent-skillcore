# Bounded fact-check admission

The fresh runtime's ordinary worker performs one `quick-factcheck/v1` pass per
selected revision. New checks use Codex's built-in live search through the existing
ChatGPT subscription and GPT-5.6 Sol high profile. Three focused queries is a target;
New text checks have a hard 120-second total deadline; checks with controller-verified,
source/revision-bound prepared video have 180 seconds. Setup, image previews, validation,
final output and publication proof all count from the original start. Acquisition still
stops at 80 seconds, with unchanged search and retrieval allowances. Existing persisted
120-second checks retain their original deadline; this change grants no repeat attempt.
The controller records observed native queries, including batched queries, from the
executor event log. Interrupted calls may have unknown additional usage; their raw
logs are retained and they cannot support publication. Restarting does not renew the
deadline or create another allowance. Historical controller-search checks retain their
hard three-query limit; approved deep research retains its hard twelve-query limit.

The model reads HTML/plain text through curator tools using exact URLs returned by
native search or registered in its initial context. Final proof rechecks those URLs
against the retained search events; native navigation and snippets cannot replace
captured page bodies. Native quick checks expose only curator read/validate tools.
Invalid search-result URLs are skipped individually. Text reads follow at most
three public redirects, charging and validating every request, and record the
final origin. A missing literal match returns the first bounded excerpt. HTTP
failures report their actual status; none of these paths renews an allowance.
Large resources retain at most a 1 MiB prefix plus one lookahead byte. The reader
parses only the prefix and marks truncation explicitly; the captured bytes remain
hashed and re-verifiable. Sparse prefixes still fail, and the normal full-resource
transport continues to reject oversize bodies. No additional request, larger
per-item allowance or complete-page coverage is implied.
A later member may reuse a fully verified quick text capture from the same account
for at most 24 hours when it requests the same registered URL. Reuse preserves the
original fetch time, final origin and body hash, records its reuse ancestor/time and
spends no new HTTP request. The checker still reassesses authority, relevance and
date-sensitive adequacy for the current item.
Search snippets and inaccessible media do not establish factual support.

The checker can call `validate` with its draft decision before final submission.
This runs the existing content/citation validator against current captured evidence
and returns errors within the original deadline. It does not fetch, publish, grant
queries or start another model execution. Every tool response remains bound to the
native transcript, and final submission still passes full publication verification.
A failed draft is feedback, never a factual disposition or research permission.

- Supported factual material requires one relevant authoritative primary source
  or two independent credible origins. The checker records its authority and
  independence assessment alongside exact excerpts. Host/body duplicate checks
  supplement that assessment; they do not establish semantic truth by themselves.
- Useful opinions and recommendations retain attribution; their factual details
  still need support. Independently useful supported parts of mixed items may stay.
- A disproven central premise excludes the item with a private reason.
- Inconclusive checks and processing failures remain outside the wiki with an
  explicit reason. Missing evidence is never a factual rejection.

The source publication validates the same native check execution and its observed
source bodies. It does not claim a second independent model review. Existing
historical publications retain their original verification contract.

No quick worker invokes the full-book, video, transcription or segmented research
pipeline. Deep work requires a separate, item-specific human approval. The [native chat bridge](chat-approvals.md) freezes approval requests and records
explicit decisions. Its explicit research command consumes only matching human
permissions; live rollout remains a separate gate; this policy does not activate a scheduler or imply deployment.

Private state includes decisions, source bodies, tool transcripts and operational
receipts. Git contains generic implementation and synthetic tests only. Completed
captured items and complete historical acquisition remain separate claims.

## Backlog batches

Ordinary `work` dispatch assigns stable cohorts of at most 50 account/source
identities. Existing leases and attempt counters remain authoritative. Workers
claim different members concurrently; restarts keep membership and the original
quick-check allowance. A delayed retry does not prevent ready work in a later
cohort. Pending decisions are never automatically claimed as fresh quick checks.

`python -m x_curator --state <private-state> batches` returns the consolidated
results; `--batch <batch-id>` selects one cohort. Each result separates supported,
excluded, pending-decision, failed-processing and still-processing counts.
Pending entries retain stable references, the checked revision, unresolved claim,
reason, proposed targeted scope and a 600-second request. This request is a
proposal, not permission to execute research. Infrastructure failures remain
visible separately and do not become deep-research approval requests. A completed
inconclusive answer with recorded search/read failures is also held for operator
triage, with the original errors shown separately from its unchanged answer.
A text-reader refusal of explicitly approval-gated media remains a valid scope
boundary. Draft-validation feedback does not count as a retrieval failure.
Previously frozen quick-check requests cannot authorize new decisions while the
current check still carries an acquisition failure; old messages remain immutable.

Publication withdrawal retains its original bounded verification error and time in
private append-only operational history. Recheck one publication with
`python -m x_curator --state PRIVATE_STATE diagnose-publication PUBLICATION_ID`.
This opens the database read-only and reports the current verifier result plus
retained failures, including for invalid publications. A passing diagnostic does
not restore a withdrawn page, change attempts, or grant another check; the existing
reviewed recovery eligibility still applies. Older stores report no historical
errors when none were retained.

Wiki organizers and reviewers receive a read-only `validate(proposal)` tool using
the same claims, catalog and contract as final acceptance. Missing/self-link
feedback names the originating and target keys. Organizers correct the draft in
the existing execution; no extra model call, mapping attempt or time is granted.
Final contract checks and independent approval remain mandatory. Invalid proposals
retain their failure reason and cannot replace a still-valid current generation.

A closed batch means all members have a disposition, including explicit failure;
it does not mean every item was admitted or that historical acquisition is complete.
If an existing member legitimately returns to the retry queue, its original batch
reopens rather than losing the item or creating duplicate membership.

## Daily new likes

The trusted operator explicitly enables the account policy with `configure-daily
--account <account> --chat <originating-chat-id> --timezone <IANA-zone>`. Setup
records the existing captured-backlog boundary. Repeating it preserves that
boundary; silently changing the chat or timezone is rejected. This configures
batching only, and does not create or activate a scheduler.

Existing workers and the existing supervisor/collector schedule continue to do
the work. On each ordinary dispatch, the controller freezes at most one daily
cohort for the current local-midnight cutoff. Eligibility uses each source's
original capture timestamp, not its tweet date. It includes unassigned newly
captured items before that cutoff, across likes and bookmarks. A catch-up after
downtime may cover multiple missed days; it is not a claim of daily acquisition
or complete history. Midnight is calculated in the configured IANA timezone,
including 23-hour and 25-hour daylight-saving days.

Even an empty cutoff is frozen. New arrivals and delayed recordings never append
to it: unassigned items carry over to a later cutoff. Existing account/source
membership prevents duplication across daily and backlog work. Pending new items
are reserved for their daily window; they are not absorbed into backlog cohorts.
Backlog cohorts retain their 50-item limit; one daily cohort covers its eligible
capture window. Supported material publishes immediately.

Ordinary successful dispatches alternate daily and backlog work, falling back
when one has no ready item. Approved deep runs do not advance this fairness
counter. The shared two-source-worker limit remains in force. Pending decisions,
deferred items and delayed retries do not hold ready work behind them.

Both workers and supervisor reconciliation prepare any missing closed-batch
status/approval digest in the existing private outbox, including after a restart
or a cycle with no new processing. Empty/supported-only batches remain silent;
technical failures produce a status digest without becoming research questions.
The digest reports useful notes, completed factual checks, technical failures and
still-processing members. Actual delivery still requires native originating-chat
observation; preparing a digest neither delivers it nor approves research.

## Repairing checks spoiled by software defects

An explicitly authorized operator may preview `recover-quick` and apply its exact
`--apply PREVIEW_DIGEST`. Eligibility requires a completed inconclusive check with
retained tool evidence of a repaired retrieval defect, unchanged source revision,
no human decision or research permission, and no prior replacement for that item.
It does not retry every inconclusive result or grant deep research.

Recovery appends a unique replacement identity, one persisted allowance under the current quick-search policy (120 seconds for text,
180 only for verified prepared video),
necessary attempt headroom and twenty HTTP requests of acquisition headroom. Original
checks, attempts, request counts and immutable approval messages remain intact.
Restarting the replacement preserves its deadline and query usage; repeated recovery
cannot replenish it. The original cohort reopens. After it finishes, unresolved
replacement checks enter one new consolidated request; old proposals cannot authorize
work against the replacement. Published and explicitly decided items are not eligible.
