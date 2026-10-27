# Fresh collection and the bounded runtime

Use the existing fresh private corpus. A rebuild does not authorize importing the
rejected archive. Valid completed fresh publications and evidence remain available.
For an existing deployment, follow [migration and rollout](bounded-rollout.md)
before starting new workers.

From this skill's `scripts/` directory:

```sh
python -m x_curator --state /private/path/to/corpus collect likes
python -m x_curator --state /private/path/to/corpus collect bookmarks
python -m x_curator --state /private/path/to/corpus status
python -m x_curator --state /private/path/to/corpus work --max-items 1
python -m x_curator --state /private/path/to/corpus report
python -m x_curator --state /private/path/to/corpus policy-report
python -m x_curator --state /private/path/to/corpus wiki --max-sources 1  # optional semantic organization
```

Collection reuses the existing authenticated X client, never its archive. Response
bytes, hashes, selected entries and pagination checkpoints commit together. Repeating
collection resumes its existing cumulative request allowance; `--new-run` starts an
explicit new pass. `timeline_end` means the exposed timeline ended, not complete history.
The existing supervisor polls fresh heads and reconciles the deterministic verified-source
index by default; semantic organization is explicit and optional.

Default `work` runs the [quick policy](bounded-fact-check.md), using a 240-second
crash-recovery lease around its 120-second text or 180-second verified-video allowance, then rebuilds the deterministic
verified-source index with zero organizer calls after any supported publication. Two source slots are enforced
transactionally. PDF/video/ASR dependencies are optional for separately approved
reading; do not deploy or start them for ordinary tweets. The qualified Linux Python
runtime and Codex CLI use the existing ChatGPT subscription, required model and
high reasoning. Provider failure stays visible without substituting a model.

### Explicitly approved video preparation

Prepare media before spending a quick-check attempt. Retain the exact selected post
revision, actual downloaded MP4 variant, original video bytes, bounded mono PCM audio
chunks, qualified speech receipts and sampled frames. Preserve original subtitle
tracks as acquisition evidence; machine captions/transcripts are not independent
corroboration of a speaker's factual claims. Long audio may be split into contiguous
chunks inside the existing 30-minute speech-reader limit. Keep a hard preparation
deadline and retain incomplete outcomes; do not automatically repeat failed work.

Controller-owned extraction packages can be cached explicitly:

```sh
python -m x_curator --state /private/corpus prepare-video \
  --account ACCOUNT --source SOURCE --package /private/extraction --reason 'Exact user approval'
```

This command does not run research, grant a source attempt or approve publication.
Its private `package.json` names `account`, `source`, `revision` (the controller's
`prepared_video.revision`), `url` (the actual selected MP4 variant), `duration`,
`media_file`, `profile`, `frames: [{at, file}]`, and
`parts: [{offset, audio_file, receipt_file}]`. Files must remain inside the package
directory. Use only controller-generated packages from the approved acquisition
and qualified speech path; never accept a model-authored transcript as an extraction.
ASR packages also record `audio_duration` and `transcribed_duration`. Chunks must
cover the declared transcribed interval contiguously, inside the audio/video bounds.
The full and observed durations are carried into limitations; do not imply that
untranscribed tails or unrecognized speech were reviewed.
A retained WebVTT `caption_file` may replace ASR parts; preserve its acquisition
and language metadata. An actually silent clip may declare `silent: true` with no
speech parts. Both still require sampled visual evidence and explicit limitations.
Each receipt must match its exact audio bytes and the independently configured
`X_CURATOR_SPEECH_CONFIG` engine/model hashes. Frame timestamps and complete audio
chunk coverage are checked. Keep raw extraction logs beside the package.

The next separately authorized quick check attaches this immutable preparation
without network acquisition or transcription. Its original persisted allowance (120 seconds for historical/text checks, 180 only for new verified-video checks),
normal fact-check/publication proof, and history rules remain in force. Changed
post revisions, foreign packages, damaged media and edited transcripts fail closed.
Visual-only clips need frames; speech or captions alone cannot prove an unseen
technique, effectiveness, performance, identity or complete motion coverage.

Backlog cohorts contain at most fifty sources. Configure a private originating-chat
route and daily timezone once; midnight freezes each new-arrival cohort. Pending
review does not block source dispatch or wiki organization. Research starts only
through a consumed, exact [human approval](chat-approvals.md).

`report` audits publication evidence and the active wiki. `policy-report` records
measured dispositions, calls, queries, retries and timing; inspect incomplete receipts
and budget overruns. A supported source is distinct from a successfully organized,
validated connected wiki. Both reports contain private content and identifiers.

State directories must be outside Git, mode 0700; runtime configuration and database
files are private. Historical implementation and optional reader details are retained
in [legacy-fresh.md](legacy-fresh.md) for audit and explicitly authorized maintenance.

For a representative repair qualification, keep source workers paused and run
`python x-repair-qualify.py --state /private/path/to/corpus --manifest /private/path/to/manifest.json`.
The preview is read-only. Its private manifest freezes at most ten unique sources,
original checks, full executor/attempt receipts and source revisions. Only after
explicit approval, add `--apply <preview-digest>` for one replacement per item:
120 seconds for text or 180 for verified prepared video, native three-query target and twenty HTTP requests of headroom.
The operator holds the intake lock, claims only manifest members, preserves prior
history and treats interrupted claims as spent. Reapplying never adds another
allowance. It then rebuilds the deterministic verified-source index with zero
organizer model calls and reports each check's timing/usage plus verdict-to-index
latency. It does not start workers, flush review batches or authorize deep research.


### Retained proof reuse

Successful publication and mapping proofs are retained in private `audit-memos/` records, authenticated before deserialization by the controller-owned 0600 key. Bindings include the state root, proof identity, interpreter/package versions and the verifier's transitive code dependencies. Renderer changes invalidate rendering without discarding source approvals. Never publish the key or private memo records.

Routine indexing uses an authenticated input/artifact checkpoint. SQLite triggers increment monotonic row revisions in the same transaction as evidence changes; missing or changed tracking triggers fail closed. Consumed files retain their verified hashes only while device, inode, mode, link count, size, mtime and ctime match, with private parent namespaces checked on each fence. Changed dependencies rerun the affected proof. The epoch shortcut requires complete tracking of data tables; an untracked table forces query-footprint verification. Fresh activation still fences the accepted source set and artifacts; this grants no source attempt, research or approval.

An unchanged checkpoint skips source loading and rendering. Accepted arrivals append to the freshly fenced retained catalog; complete approved mapping packets are retained so previously absent claims are projected correctly. Other changes reuse valid per-source and mapping proofs. Indexing then builds a new immutable generation with the normal strict MkDocs compiler and actual link validation. Unchanged Markdown is linked into the new generation only after actual-byte comparison, with directory durability preserved. Strict compilation uses a reproducible build timestamp; HTML parsing facts are reused by authenticated content hash, while every link target and anchor is still checked against the new site. Small changed batches do not require a custom incremental compiler.

Historical sources with missing or differently bound proof seals require explicit maintenance rather than silently replaying the whole archive. Run `python -m x_curator --state /private/path/to/corpus wiki --audit --max-sources 0` after deployment changes the proof format or verifier policy. This performs the complete evidence audit and rebuilds proof checkpoints, always with zero organizer calls. Preserve the resulting private receipts; ordinary indexing can then reuse them after process restart. It does not retry fact checks or perform deep research.


### Storage retention

A verified wiki publication keeps the active generation plus the two newest completed
previous generations. It removes obsolete build rows with their directories, expires
uncommitted build directories after seven days, and refreshes artifact fingerprints
before saving the current checkpoint. Missing cached generations are rebuilt.

Run `python -m x_curator --state PRIVATE_STATE retain` for a read-only preview;
add `--apply` to delete eligible copies. The command holds the wiki lock while applying.
It preserves source blobs, acquisition responses, publications, approvals, attempts,
execution receipts and mapping history. It never resets consumed budgets.

Daily retention expires unreachable proof-memo identities after seven days, only when
all published sources and accepted mappings have current proof memo files. After verifier changes, first
run `wiki --audit --max-sources 0`; never bypass missing historical proofs by deleting
them. Current memo identities and the private signing key are retained.

For terminal runs older than seven days, staging image copies expire only after a
byte comparison with their original blob. Event and native session files expire only
when byte-identical to a transcript already retained in the canonical database receipt.
Active runs, unique/unrecorded bytes, unknown files and external CODEX_HOME directories
are excluded. Canonical transcripts remain unchanged and uncompressed in this release.

New supervisor rows store compact counts, generation, action and dependency diagnostics
rather than repeated source inventories and artifact manifests. Retention compacts the
same redundant fields in completed cycle rows older than seven days. SQLite reuses freed
pages; retention does not VACUUM or claim that logical savings shrink the database file.

Recognized `*-before.sqlite3` and `policy-transitions/*/before{,-migration}.sqlite3`
snapshots retain the two newest copies. Older copies expire after thirty days only
when their WAL and rollback journal are absent or empty. Unknown operator backups are not swept.

After reviewed activation, install `templates/systemd/x-curator-retention.{service,timer}`
using the existing runtime environment, run the preview, then enable the daily timer.
Do not activate branch code or bypass the reviewed-main deployment gate.

Operational qualifications must use `tempfile.TemporaryDirectory` under the approved
state's `ops/` directory and clean it on exit. Keep only compact result receipts;
copy the minimum fixtures required, never entire `runs/`, backup or qualification trees.
Existing unregistered operational directories require explicit inspection; retention
never guesses whether their contents are unique source evidence.
