# Bounded-policy rollout

This is an offline transition of the existing **fresh** corpus, not a reset or an
implicitly authorized legacy import. Keep this runbook's filled-in values and all
command output private. Implementation CI is separate from live acceptance.

## Private browser access

`python -m x_curator.wiki_http "$CURATOR_STATE"` serves only the current
completed build's `site` directory at `127.0.0.1:8043`. It rereads `wiki/CURRENT.json`
for each request, disables directory listing, rejects escaping symlinks, and asks
browsers to revalidate cached files. It does not open the database or run indexing.
Install `templates/systemd/x-curator-wiki.service` as a user service, then add a
private route with `tailscale serve --bg --set-path=/x-likes http://127.0.0.1:8043`.
Keep the trailing slash on browser links (`/x-likes/`) for relative assets. Do not
use Funnel or replace other Serve routes. A GoLink can point to that HTTPS URL.
For access logs, override `StandardOutput` and `StandardError` with
`append:/absolute/approved-state-folder/wiki-http.log` in the installed unit.

## Prepare and pause

Use a reviewed commit that passed the full gate and independent review. Verify
its required Python/Codex profile through the existing authenticated subscription.
Do not change unrelated services or provision mandatory media helpers.

Stop the existing curator intake/wiki supervisor and both worker timers/services.
Confirm their process groups have exited. Fence any old deep leases only after
stopping their processes: retain the previous job/attempt state in a private receipt,
mark interrupted attempts honestly, and clear old tokens. Do not relabel an
interruption as factual disproof. No leased job may survive migration, even expired.
Preserve a private SQLite backup for forensic recovery; normal rollback must never
restore an old database or erase consumed work.

## Inspect and apply

```sh
python -m x_curator --state PRIVATE_STATE migrate-quick > PRIVATE_PREVIEW
python -m x_curator --state PRIVATE_STATE migrate-quick --apply PREVIEW_DIGEST > PRIVATE_APPLY
```

The first command opens the original SQLite database read-only and normalizes
schema only in an in-memory copy. Original publication proof and artifacts are
verified against the real private paths. It accounts for every captured identity,
including jobs not yet enqueued. It reports valid publications, already-governed
new-policy work, planned quick checks, orphan jobs and blocking inconsistencies.
It does not alter job state, files, budgets or the live schema.

Review the exact preview before passing its digest to `--apply`. Invalid or missing
published artifacts, orphan jobs, consumed requests beyond their recorded allowance,
and leased jobs block the entire apply. Repair and re-preview explicitly; never
silently delete or bless them. Keep **all curator processes stopped** throughout.
Apply verifies publications again and compares the full plan while holding one
SQLite writer transaction. This deliberately trades migration downtime for an
atomic transition. Other operators must not modify private artifacts during it.

Only legacy unresolved items receive pending quick work. Each transition snapshots
the old job, counters, reasons and publication inventory under a unique policy /
account / source key. It records the new attempt ceiling and linked recovery grant.
Consumed attempts and requests are never reset. The new ceiling is the greater of
the old ceiling and consumed attempts plus one. When fewer than twenty requests
remain, one explicit twenty-request grant supplies bounded acquisition headroom;
the preview shows the exact resulting allowance. The persisted hard deadline still applies: 120 seconds for new text checks, 180 for verified prepared video. New native checks target three queries
and retain observed usage; historical controller checks keep their hard three-query cap. Re-previewing/applying transitioned sources grants nothing more.
Valid publications and existing new-policy decisions/permissions stay untouched.

## Activate reviewed defaults

Do not activate this default until #273 records a passing representative qualification
and reviewed activation decision. The supervisor default keeps semantic organization
disabled with `--max-sources 0`.

Pin `PYTHONPATH` to the reviewed code directory in the existing private runtime
configuration. Install the reviewed `templates/systemd/x-curator-worker@.service`:
240-second crash-recovery lease and outer timeout (quick checks remain capped at 120 seconds for text or 180 for verified prepared video), full process-group termination, and deferred indexing with `--unspent-only`. This mode holds previously attempted pending/retry or expired jobs for explicit operator recovery; both batch readiness and transactional claims exclude them. It preserves consumed receipts and existing approved recovery tools. Install the
reviewed worker timer too: five seconds after each invocation, one-second accuracy.
Install the reviewed index service/timer alongside it: workers signal a nonblocking
index pass; the timer catches arrivals during a build and interrupted passes. The
index owns a separate 1200-second outer limit, the existing wiki lock and full
proof/artifact verification. It uses zero semantic model calls. An unchanged catalog
skips expensive replay and makes no freshness claim; supervisor/report proofs remain.
Route index stdout/stderr to files inside the approved private corpus via an existing
systemd drop-in before activation, rather than storing private results in the journal.
Queue retry times and provider cooldowns still govern eligibility; an unavailable
provider or empty queue spends no source attempt or model call. Preserve the
existing supervisor; start exactly worker instances 1 and 2. Validate
unit syntax and effective commands before reloading the user service manager.
Never restart the old four-hour automatic research workers.

```sh
python -m x_curator --state PRIVATE_STATE configure-daily --account PRIVATE_ACCOUNT --chat ORIGINATING_CHAT --timezone LOCAL_TIMEZONE
```

This stores the private route, timezone and baseline once; repeated setup cannot
silently move the daily cutoff. Use the [chat bridge](chat-approvals.md) to deliver
and read back digests in the originating chat. An outbox alone is not a working
chat integration. If scheduling or native delivery is unavailable, keep that blocker
visible; do not substitute another channel, fabricate a receipt, or infer approval.

## Live qualification and completion

Record reviewed revision, effective units, provider profile, pause/fence evidence,
preview/apply receipts and timestamps privately. Then verify:

- One actual fifty-item backlog cohort has explicit supported, excluded, pending
  decision or failed-processing dispositions; valid earlier publications survive.
- A controlled fresh-arrival daily case freezes at the configured civil cutoff,
  runs alongside the backlog and creates at most one consolidated digest.
- A real human decision in the originating chat authorizes one exact item/revision,
  question, scope and budget. Only that permission can launch research. Deferred
  and excluded items do not execute. Timeout does not extend itself.
- `policy-report` records observed quick/approved processing and capture-to-disposition
  times, first new source-publication latency, searches, reserved model calls, retry
  evidence, failures and incomplete timing receipts. Cohort counts cover assigned
  members; queue counts include unassigned jobs. Observed retries associate the
  current token and matching execution receipts; consult retained attempt history
  for crashes before any model reservation. A model reservation can fail
  before provider execution; do not call it a proven completed model invocation.
  Budget overruns fail qualification. Missing timing receipts need live investigation,
  never fabricated zero durations. Ordinary publication is immediately indexed;
  semantic mapping remains a separate optional wiki phase.
- `report` verifies actual publication evidence and the connected wiki's active
  generation. Record time to the first useful verified wiki result from rollout
  timestamps and the generation receipt. Reconcile every captured item, including
  items not yet assigned a batch. Neither report proves full historical acquisition.

Keep the operator’s rollout tracking open until these live checks pass. Infrastructure or
human-approval blockers remain explicit; successful CI alone cannot close rollout.

## Reinstating verified withdrawn pages

An operator may use `complete-publication PUBLICATION_ID --reason REASON` for an
exact prepared or invalid page whose full retained approval, current source,
evidence and file bytes verify. The source must be unleased and have no competing
published version. No model, HTTP request, new allowance or attempt is needed.
Invalid reinstatement preserves the original completed quick check and withdrawal
history, retains the first completion receipt and appends a hashed reinstatement
event. Repeating a successful request revalidates without duplicating an event.
Diagnosis alone never reinstates a page; missing or invalid proof remains withheld.

## Rollback

Stop affected services and retain all data, receipts, decisions and consumed budgets.
Point only to a reviewed version capable of interpreting the new policy records.
If that is unavailable, leave source dispatch stopped. Never restore old database
snapshots or re-enable automatic deep research as a rollback shortcut. Intake/wiki
may resume separately only after their compatibility and effective commands are
verified. No unrelated services or authorizations change.
