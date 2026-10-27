# Historical fresh runtime reference

These are implementation and audit notes for earlier revisions. Do not use their
deep-worker or media setup as the current default. See [rollout](bounded-rollout.md).

# Fresh rebuild

The new runtime lives beside the existing X-curator tools in this skill. Code
reuse does not authorize reuse of historical archive, research or wiki data.
The six sequential implementation issues are #170–175 in this repository.

## Collection (#170)

Use the Python environment containing the existing TweetHoarder client. Its
authentication and URL constructors are reused; its archive is never opened.
From this skill's `scripts/` directory:

```sh
python -m x_curator --state /private/path/to/new-corpus collect likes
python -m x_curator --state /private/path/to/new-corpus collect bookmarks
python -m x_curator --state /private/path/to/new-corpus status
```

State must be outside a Git checkout. Each response body, digest, selection and
checkpoint commits atomically in private SQLite storage. Repeating collection
resumes the same run with its cumulative request count. `--new-run` explicitly
starts a fresh pass; old response evidence remains. `--max-requests` is a total
per-run bound, not a new allowance on each restart.

`timeline_end` means the currently accessible timeline ended, not that every
historical like was recovered. Coverage always reports that limitation. HTTP
errors, malformed structures and cursor loops leave the run incomplete. The
collector does not retry rate limits inside a call or fabricate missing entries.
Exit 2 means blocked collection; exit 1 means a process/storage failure. Exit 0
means the bounded pass or status query succeeded: inspect the reported state to
distinguish a request-budget checkpoint from `timeline_end`.

## Durable queue (#171)

`python -m x_curator --state /private/path/to/new-corpus queue` idempotently
enqueues every fresh selection, including inaccessible sources. One job per
account/source retains all like/bookmark selection receipts. Published state
is reserved for the later verified publisher; enqueue never marks work done.

Workers use `leases.claim` and `leases.fail`: SQLite serializes claims, unique
lease tokens fence stale workers, and expired claims consume their original
attempt. Three attempts per source survive process restarts and re-enqueueing.
Exhaustion retains an actionable unresolved job. Durable alternating oldest /
newest selection gives backlog and arrivals time; retries honor `next_at`.

## Evidence and publication (#172)

Controller acquisitions produce sealed captures. Selected source text is checked
against its original response bytes and digest; a changed source revision makes
an older proposal stale. A model cannot supply its own capture receipt. Every
claim requires attribution, an epistemic category, limitations and exact source
excerpts. Title and summary reference supported claims. Controller-extracted
links, quoted/reply context and media remain acquisition obligations even if the
model omits them from its answer.

The controller reserves execution records before invoking an executor. It records
the input, model, role, original event stream, session, output and their hashes.
Research and verification use separate sessions; review must approve the exact
proposal and evidence bundle. Model-authored reviewer identities do not count.
The bounded executor below supplies these authentic execution receipts.

Publication first records a prepared immutable version, then writes it atomically
and reads back exact bytes. Only a final transaction with a still-valid lease,
evidence and verdict changes the job to published. Interruption can replay the
same version. Conflicting files are preserved and block completion. Audit removes
missing/damaged pages from completion; receipt replay restores missing bytes but
does not silently restore verified status. Previous versions remain available.
Both publication transactions validate through deferred read snapshots, preserving
other workers' ability to write during a long proof audit. Snapshot conflicts may
retry the complete publication at most three times within the same lease, with
the same model receipts and immutable version; they never rerun research or reset
budgets. Prepared versions survive a conflicted finalization. Evidence changes,
expired leases, deadlines, file conflicts and other database errors are not retried.

## Bounded research (#173)

Install the pinned `requirements-runtime.txt` into a separate Python 3.13
virtual environment. The NumPy pin supports the deployed host CPU baseline;
newer wheels require CPU features absent on that host. Verify `import numpy,
faster_whisper` on the deployment machine before starting media work. PyAV is
pinned below the release that removed the decoder argument used by Faster Whisper.
Qualify an actual audio transcription when changing either pin. Install system `ffmpeg`, `ffprobe` and `pdftotext`.
The qualified Codex CLI profile targets version 0.160.0 and requires an existing
ChatGPT subscription login (`codex login status`). `codex` must be on PATH.
No API-key fallback is permitted. Faster Whisper downloads its small model on
first use; its automated transcripts and six sampled video frames retain
explicit limitations. Unsupported or unreadable media remains unresolved.

```sh
python -m x_curator --state /private/path/to/new-corpus work --max-items 1
```

Each source receives at most three lifetime attempts, forty HTTP requests
(including redirects), and one discover/research/review execution per attempt.
A persisted lease bounds the entire attempt (one hour by default, explicitly
configurable up to four hours for standalone workers); a hard wall-clock alarm
also bounds each HTTP request to sixty seconds. Ordinary model calls have a five-minute
limit for discovery and ordinary review; research authors have fifteen minutes.
POSIX main-thread execution is required. Expired workers cannot modify a
replacement lease. Every failed call or retrieval remains in private receipts.

Fresh authenticated X detail expands author-thread, parent, quote, media and
link obligations to a bounded closure. Public retrieval rejects non-public
addresses and pins validated DNS destinations. All response bodies are retained
before semantic validation, including rejected X responses. Mandatory material
must be acquired; optional supplemental failures become explicit limitations
and cannot support claims. Missing load-bearing evidence blocks publication.

Public Dropbox shared PDF links use its documented `dl=1` download route while
retaining the original source URL and other link parameters. Every actual request
and redirect uses the same public-address checks and lifetime request budget.
A preview/login page or non-PDF response cannot stand in for the linked document;
normal PDF extraction must succeed before the capture is usable.

If a static HTML body is unreadable but public description/title metadata is
present, retain it as a distinct metadata-only capture with original bytes.
Its coverage must be `metadata_only`, and the proposal must retain the exact
unread-body limitation. Metadata can describe a linked page; it cannot establish
claims about unseen page or community content. Empty shells remain unresolved.

A pass stops on provider failure. Other failures remain queued with an explicit
action and retry time. `checkpoint` means the bounded pass ended, not that the
corpus is complete. Exit/status alone is not live acceptance: check publication
receipts, separate model sessions and exact page readbacks in private storage.

Research prompts use lossless compact JSON and a 1,000,000-character limit on the
complete instructions, evidence and proposal. This application bound is not a
token-window guarantee. All evidence fields and string contents remain intact;
larger inputs require segmented recovery rather than silent truncation. Provider
rejection or inadequate evidence coverage remains unresolved. Qualify both
research and independent review when recovering a previously oversized source.

Each model execution receives all unique acquired still images and sampled video
frames, up to a bounded allowance of 32. Duplicate blob references share one
attachment; no distinct image is silently dropped. Larger sets require segmented
review. The allowance is not a provider-capacity guarantee: full authentic
research and independent verification must still succeed before publication.

## Connected wiki (#174)

```sh
python -m x_curator --state /private/path/to/new-corpus wiki --max-sources 5
```

The organizer assigns approved claims to concept/entity pages; a separate model
session reviews topic meaning and relationships. It receives a bounded catalog
of existing page descriptions and evidence, not just ambiguous titles. Claims
retain their publication-revision/claim identifiers, original attribution and
limitations. Dated viewpoints remain side by side; the renderer does not invent
a reconciled conclusion. Related links are optional and independently reviewed.

Each publication has at most three mapping attempts. Actual inputs and event
streams persist in `wiki_runs`. Failed site builds reuse accepted mappings and
spend no new model calls. The wiki lock is separate from collection and source
workers. A completed mapping does not imply a completed or current site build.
Within a wiki run, the initial source/mapping audit also checks the current
generation. It is not reused across model execution: post-model reads and the
build-commit dependency fence still reverify freshness and artifact bytes.
A generation verifies its recorded publication members. New arrivals wait for a
later build without withdrawing valid existing knowledge; changed or withdrawn
included evidence still prevents activation or withdraws the generation.

Version-one organization inputs preserve all approved claim prose, epistemic kinds,
attribution and limitations while omitting citation excerpts from source and catalog
views. Canonical publications, citations, hashes and rendered provenance stay intact.
The complete compact prompt has a one-million-character bound; preflight reserves
100,000 characters for the review proposal before spending an attempt. Ranked
existing-page context uses at most 100,000 characters of the remaining envelope;
selected claims are never truncated. Reusing an omitted existing page fails closed.
The supervisor batches up to five sources per independent author/reviewer pair. Oversized
inputs therefore remain unresolved without consuming mapping attempts. An oversized
model-generated proposal consumes its author call and cannot start review. At most
thirty proposed pages must assign every claim. Organization authors have 900 seconds,
reviewers 600, within a persisted 1,800-second mapping attempt. These are bounded
allowances, not promises that arbitrary documents fit. Historical full-citation
mapping receipts remain independently auditable under their original inputs.

Markdown and a pinned MkDocs 1.6.1 site live under immutable
`wiki/builds/<generation>/`. Concept/entity pages link to source provenance;
source pages link back. `source-map.json` and the index reconcile organized and
awaiting-organization counts. The compiler rejects symlink/Git output trees;
actual rendered links, anchors, assets and file hashes are checked before
`wiki/CURRENT.json` names the generation. Earlier generations remain history.
`wiki_current.current` revalidates current sources, mappings and every artifact;
withdrawn or damaged evidence clears the current pointer instead of remaining
current knowledge. Consumers must use this validated current-generation API.
The supervisor runs these checks automatically.

Final build validation uses a read snapshot so its full source/receipt audit does
not hold the corpus write lock. A concurrent database commit rejects promotion
before the generation pointer changes; the supervisor records a blocked cycle
and a later stable build reuses accepted mappings. Continuous writes may delay
wiki freshness, while source workers continue and existing budgets remain intact.

Rejected organization or a cooling-down provider route leaves the mapping
unresolved while the compiler rebuilds verified sources and accepted mappings.
The result reports the blocked organization action alongside its valid generation
and accurate unmapped count. Deadline and build-integrity failures still block
completion; rejected mappings never become page content.

All corpus content, model receipts, Markdown and rendered HTML remain private.
Only code, synthetic tests and pinned dependencies belong in Git.

## Subsequent slices

Full-cohort live qualification remains tracked in #175. Collection alone is not ingestion
or completed research. Runtime data and live acceptance reports stay private.

## Engineering

Follow Ponytail: reuse first, stdlib where practical, smallest coherent change.
New runtime and its tests enforce MI >50 and cyclomatic complexity <8 in CI.
One logical multi-file change is one atomic commit. Run focused tests before
pushing; inspect exact-head CI before follow-up commits. Request `/q review`
and J-Bot for reviews only. Independently review and resolve material findings
before merging and closing each issue. No WIP pushes or per-file commit series.

## Supervision (#175)

The production schedule separates intake/wiki upkeep from research. The supervisor
runs with `--max-items 0`. Two instances of `x-curator-worker@.service` and its timer
perform research, each handling one source with an explicit four-hour persisted
lease and a slightly longer service timeout. Discovery and ordinary review remain
bounded at 300 seconds; research authors have 900 seconds, with segment review and composition
calls bounded at 600 seconds. A four-hour ceiling is not a promise
that every document fits; timeout remains unresolved and consumes its normal attempt.

Enable only worker instances `1` and `2`, preserving the qualified two-research-worker
limit. Their distinct private logs and SQLite lease tokens make ownership visible.
Intake and wiki upkeep can continue while a book is being researched. Before migrating,
disable both old timers with `systemctl --user disable --now x-curator-fresh.timer
x-curator-worker.timer` and let both the old supervisor and singleton worker finish.
Stop both old services before installing/reloading the new units and activating the
two instances: reloading alone does not change an already running supervisor. Do not
also enable the former singleton or research in the supervisor. Stop both instance timers and services
to stop background research; each service kills its full descendant process group.

The POSIX speech helper permits at most two forked request handlers, preserving
each handler's main-thread deadline. Health checks share those slots and may
pause new claims while both are busy. Qualify two simultaneous complete videos
on the speech host before enabling the extra worker; retain both receipts and
verify that stopping the user service also stops its handler/engine descendants.

```sh
python -m x_curator --state /private/path/to/new-corpus supervise --max-items 0 --max-sources 5 --seconds 3500
python -m x_curator --state /private/path/to/new-corpus report
```

Each cycle records its deadline, process identity, stages, outcome and recovery
actions in the private database. Separate supervisor, collector and wiki locks
prevent overlapping writers without blocking leased source workers. Research
reserves part of the cycle for organization and accounting. Linux process start
identity distinguishes a live process from a stale or reused PID; other hosts
report unverified liveness rather than guessing. Provider execution failure
pauses the fixed ChatGPT route for one hour before another bounded probe. It
cannot burn attempts from the rest of the queue while that circuit is open.

A later production execution can release its observed cooldown only with a complete
fixed-profile input proof and a native session started after that failure and after
the invocation began. The exact failure generation and proof are journaled privately
in the same transaction as release. A newer failure survives stale successes;
partial output, login success and historical receipts cannot recover the route.
Semantic unresolved output can establish route health while remaining unpublished.
Direct qualification calls do not change provider health or source budgets.

The health schema adds nullable generation/time columns. Drain all old workers and
the supervisor before deploying this migration. Legacy rows remain ineligible for
automatic recovery until a genuine new failure. Retain a schema-compatible rollback
release whose health INSERT explicitly names `route,retry_at,action`; unmodified old
three-value INSERTs cannot run against the migrated table. Code rollback preserves
the current database and all consumed budgets; never restore an old database snapshot.

Head polling resumes an unfinished poll with its original five-minute deadline
and cumulative 100-request limit. A new poll starts no sooner than 30 minutes
after the previous start. It stops at a complete page of previously observed
selections. These are incremental coverage boundaries, never proof of complete
history. Failed or expired polls retain their response receipts and actions.
Changed engagement counters do not invalidate research; changed substantive
source content still does. Publication validation always checks original HTTP
bytes before comparing normalized content revisions.

`report` audits published evidence and the active wiki before reporting them.
Every selected identity appears with publication count, job state, consumed
attempts and a concrete next action. Mapping attempts remain distinct from an
active verified site. Reports and stdout contain private identifiers: store
operational output outside Git and never paste it into public issues or CI.

For Linux user services, copy both `templates/systemd/x-curator-fresh.service` and
`.timer` plus `x-curator-worker@.service` and `x-curator-worker@.timer` to the user's
`~/.config/systemd/user/` and adapt
`runtime.env.example` into `~/.config/x-curator-fresh/runtime.env` (mode 0600).
Set an absolute private corpus path and a versioned, reviewed code directory in
PYTHONPATH. Create `~/.local/state/x-curator-fresh/` mode 0700 for the service
logs. Use the separately qualified runtime environment described above.

Validate units with `systemd-analyze --user verify`, then reload and enable the
timers with `systemctl --user daemon-reload` and
`systemctl --user enable --now x-curator-fresh.timer x-curator-worker@1.timer
x-curator-worker@2.timer`. Each service kills its full
process group after its outer deadline, so child models cannot outlive a cycle.
Check `systemctl --user status x-curator-fresh.service`, `list-timers`, and the
private report. A user manager with lingering enabled continues after logout.
Stop future work using `systemctl --user disable --now x-curator-fresh.timer
x-curator-worker@1.timer x-curator-worker@2.timer`; stop active invocations with
`systemctl --user stop x-curator-fresh.service x-curator-worker@1.service
x-curator-worker@2.service`.

This scheduler runs only the installed pipeline. It cannot edit code, push Git,
message other chats, or assert that an unresolved corpus is complete. Legacy
archive and publishing services retain separate names, data and outputs.

## Explicit recovery of fresh work (#185)

Retries can reuse fully verified captures from the same fresh corpus, source
identity and substantive revision for at most 24 hours. Original acquisition
timestamps and body hashes remain unchanged; each new capture records its reuse
ancestor and time. Changed source content, damaged evidence, missing blobs and
unavailable captures cannot be reused. Reuse is on demand: only captures reached
from current required or discovered URLs enter a retry bundle. X requirements are
re-derived from original authenticated bytes with a versioned extraction policy.
The selected post freezes author/conversation scope; foreign parents and quotes
retain direct links, media and explicit context without expanding their surrounding
threads. Hidden reply pagination and foreign surrounding conversations remain
explicit limitations. Required URL closure still applies, and new research plus
independent review are required for publication.

An operator may grant one additional attempt after diagnosing and fixing a
specific exhausted source. This is never invoked by the scheduler:

```sh
python -m x_curator --state /private/path/to/new-corpus recover SOURCE_ID --reason 'Reviewed fix and concrete recovery rationale'
```

The grant records the previous/new allowance, reason and time. It leaves consumed
attempts, requests and failures intact. At most two lifetime recovery grants are
allowed per source. `--request-extra 20` explicitly adds twenty requests when a
qualified repair requires fresh acquisition; the default adds none. This is an
observable budget extension, not a reset. Active or published jobs cannot receive
a grant. Keep real source identifiers and recovery records in private operations.

### Qualified speech helper

A slow controller CPU can delegate speech extraction through an authenticated
loopback service carried by an outgoing SSH tunnel. The helper uses the unchanged
[whisper.cpp v1.9.4 release](https://github.com/ggml-org/whisper.cpp/releases/tag/v1.9.4)
and the public `ggml-small.bin` model. Build the upstream `whisper-cli` in a durable
private runtime directory using its documented CMake flow. The qualified Intel
Mac build uses Release mode and `GGML_METAL=OFF`. The helper needs only Python's
standard library; the media controller retains its existing pinned runtime.

The helper configuration is a mode-0600 JSON file containing absolute `engine`,
`model` and private `state` paths, actual SHA-256 `engine_sha` and `model_sha`, and
a random private `token` with at least 32 characters. The controller's private
client JSON contains only the same token and the two expected artifact hashes.
Set `X_CURATOR_SPEECH_CONFIG` to that client file in the controller's runtime
configuration. Neither file belongs in Git. Model processes do not receive these
configuration variables or credentials.

The service binds only 127.0.0.1:8768 and accepts authenticated health/audio
requests. An outgoing SSH connection from the speech host forwards the controller's
127.0.0.1:8768 back to this listener. Existing SSH authentication and verified host
keys are required; no incoming login permission on the speech host is needed.
`templates/launchd/` provides macOS user-agent templates. Render `__HOME__`,
`__REVISION__` and `__SSH_DESTINATION__` to reviewed absolute paths and the existing
controller SSH destination, validate with `plutil -lint`, and bootstrap them into
the user's launchd domain. Pin code to the reviewed revision. They run while that
user session and host are active; missing service/tunnel pauses research before
claiming another source and preserves the actionable dependency reason.

The protocol accepts complete mono PCM16 at 16kHz, at most 30 minutes and 58 MiB.
Each receipt binds exact audio bytes, engine and model hashes, segment timestamps
and actual processing times. Actual raw output and stderr stay in private
content-addressed files; timeout/nonzero-exit diagnostics and partial JSON are
retained as failed records, never accepted transcripts. Video captures retain the
structured speech receipt alongside sampled-frame and transcription limitations.
Qualification requires a real complete video, authenticated transport, rejection
of foreign/truncated audio and an unavailable-reader test that spends no source
attempts. This improves reader throughput without claiming that ASR is infallible.

### Complete model input receipts (#197)

New live executions retain private native CLI rollouts. Their versioned controller
envelope preserves unchanged stdout and rollout records, exact prompt and request
hashes, command profile, and the acquired image identities. Admission/readback
requires the matching session, complete original prompt, identical attached image
bytes, matching final response, and no recorded compaction or truncation. Missing
or altered evidence fails closed. Publication and wiki audits bind the prompt's
serialized evidence to the original controller request without depending on later
instruction wording. Older immutable native receipts remain identifiable as older
receipts; they are not retroactively assigned this proof level.

The one-million-character complete source envelope is an application bound, not a
token estimate or provider guarantee. Private qualification used complete research
and review envelopes on the pinned CLI/model; independent semantic rejection still
prevents publication. Inputs that exceed the bound or lose context remain unresolved
and require a separately reviewed segmented-reading path. Session records stay in
the private Codex home and proof envelopes in private corpus receipts, never Git.

The [official non-interactive CLI documentation](https://learn.chatgpt.com/docs/non-interactive-mode)
describes native JSONL execution events; the installed CLI's persistent rollout was
qualified separately. Do not infer absence of compaction from a final answer alone.

### Corrective research retries (#199)

A new research attempt receives the latest rejected proposal and specific findings
only after verifying its controller receipts, separate research/review sessions,
exact proposal/evidence binding, unchanged selected-source revision and original
capture integrity. Damaged or stale feedback is excluded. Feedback is historical,
untrusted context; the researcher must use current capture IDs and independently
check the correction. The new request records the feedback in its own input hash
and model-input proof. A fresh independent approval is still required, and this
mechanism neither grants attempts nor resets acquisition budgets.

### Oversized evidence reading (#201)

When the complete research envelope exceeds the application bound, discovery uses
an explicitly limited selected-post context and an unread-source inventory. After
acquisition closes, the controller freezes a version-three text plan over the original
bundle: every text character belongs to exactly one primary interval. Intervals
prefer paragraph/sentence boundaries without dropping characters and are packed
into at most sixteen 200,000-character groups, with up to 2,000 characters of
separately labeled context on either side. Original media stays attached to its
capture. Plans or complete review/aggregate envelopes exceeding their bounds stay
unresolved; nothing is truncated to force success.
Historical version-one plans retain their 100,000-character width for audit;
version-two page/image partitioning remains unchanged.
Each capture presents its primary text as an ordered line map retaining every
original character and line ending; adjacent boundary context is separate and
cannot support primary citations. Researchers select inclusive line endpoints.
The controller inserts the exact original substring before independent review,
without changing claim prose. Missing, reversed or ambiguous references reject.
Audit reconstructs the same canonical packet from the immutable raw model output.
Source identity and bundle hash are supplied by the controller from the authenticated
view, avoiding model transcription of controller metadata. Canonical packets from
historically correct author identities remain identical; request/view binding and
exact independent approval remain mandatory.
The model sees its plan hash/index; the complete numeric interval ledger is retained in the controller and composition
manifest. Audits reconstruct both primary text and context from that ledger. Models
assess substantive coverage and concrete semantic gaps, not character-count estimates.

Each group gets its own controller execution slot, authentic full-input proof,
research proposal and independent review. Zero-claim intervals require an explicit
reviewed explanation. Slot identity and semantic role are both verified. Request
hashes name native output files so multiple segment calls cannot overwrite them.
An authenticated semantic rejection permits one correction within the same attempt.
The correction author receives the exact rejected proposal and findings as untrusted
feedback; a fresh separate review must approve the corrected packet. Both original
and correction receipts remain in the audited chain. Malformed proofs or verdicts
cannot trigger correction, and a second rejection stops the attempt. Source retry
and acquisition allowances are unchanged.
All approved claims, citations, qualifications and coverage notes are retained;
only claim IDs are namespaced. A final research session writes the title/summary
from that explicitly labeled approved-claim view, and a separate session reviews
its interpretation. Composition sees every approved claim's text, kind, attribution
and limitations, with citation excerpts omitted from this view only. Original
citations remain unchanged in the canonical packet and are reconstructed and verified
through the original segment receipts. The final reviewer sees all approved claim prose once, alongside
the proposed title/summary; approval binds both their hash and the complete claim
view hash. It never pretends the view is the original book.

Publication, readback and wiki ingestion reconstruct and verify the complete chain
against the current original captures, including every interval, byte hash, input
proof, proposal binding and independent session. Missing or altered segments cannot
produce a completed page. The path allows at most sixty-four segment executions plus
two composition executions per source attempt. Segment authors have a 900-second
ceiling; segment review and composition have 600 seconds. Every call remains under
its enclosing phase and persisted attempt deadline.
The standalone worker profile allows four hours, without changing source retry or
HTTP budgets; the shorter intake/wiki supervisor performs no research.
Interrupted attempts retain receipts and consume their normal budget; cross-attempt
segment reuse is intentionally not implemented in this version.

Reading policies are versioned. Publication audit rebuilds the recorded version;
future tuning must add a policy version rather than change an existing policy.

### Physical PDF pages (#207)

New PDF captures retain the original bytes, exact full `pdftotext -layout` text,
physical page intervals (including text-empty pages), and a PNG of every page.
The sealed manifest records original/text/image hashes, page numbers, dimensions,
exact rendering flags and Poppler versions. Rendering is bounded at 512 physical
pages, 1,600 pixels on the long edge, thirty seconds per page, 900 seconds total,
and 512 MiB of retained PNGs. The enclosing source deadline still applies. A failed
page or ambiguous extraction boundary leaves the source unresolved.

Page-aware reading uses version two: whole pages are packed within 100,000 text
characters and 32 attachments, accounting for ordinary acquired images as well.
Every view carries only its assigned page inventory and pixels. Physical positions
are distinct from printed page labels; identical blank-page PNGs may share an
attachment but retain separate page identities and coverage. Empty extracted text
never establishes a blank page. Both author and reviewer inspect every assigned
page, including scanned pages, and explicitly record visual coverage. Missing,
duplicate, foreign or unreadable page records cannot become full source coverage.

The controller derives physical page/character references for text citations from
exact line selectors. A visual citation names one assigned physical page and binds
its original PNG hash. Source and wiki links expose these page references and the
text/visual distinction. New complete input proof version two checks native image
order, making attachment numbers meaningful. Version-one proofs remain readable
for historical inputs but cannot qualify physical PDF-page evidence.

A cached legacy PDF text extraction is re-extracted into a new capture from its
retained fresh original bytes, preserving acquisition time and reuse ancestry.
Earlier captures and their approvals remain unchanged; a text-only historical
publication is never silently upgraded to reviewed page-image coverage. New PDF
work requires fresh independent page review, and no source budget resets occur.

### Public YouTube video acquisition (#223)

Public single-video YouTube URLs use pinned `yt-dlp==2026.8.19` for metadata only.
Only its YouTube extractor is enabled; plugins, JavaScript runtimes, remote
components, cookies and downloader/postprocessor execution are disabled. Every
extractor request, redirect and media chunk crosses the controller's durable
lifetime request counter and public-address-pinned transport. Request bodies,
response bytes and headers remain private, alongside failed-attempt receipts.

The initial qualified profile requires direct format 134 (360p H.264) and 140
(AAC), a non-live video of at most thirty minutes, and an authenticated player
response binding both complete stream URLs and sizes to the requested video ID.
Unsupported profiles remain unresolved. Known media sizes must fit the remaining
request allowance before downloading. Contiguous one-MiB ranges require exact
206 intervals and a stable strong ETag, or a conservatively separated
Last-Modified/Date validator. No range retries or budget resets are implicit.
Acquisition has a five-minute ceiling inside the existing attempt deadline.

The controller merges only retained local streams with deterministic ffmpeg flags,
retaining input/output hashes, tool version and ffprobe results. Ordinary video
reading then samples six frames and transcribes audio; it never claims exhaustive
visual coverage. Research, independent review and wiki publication keep their
existing requirements. Readback verifies video identity, receipt ownership,
range order, complete assemblies and the recorded merge without network access.

A short link ending at YouTube retains its original page bytes as redirect
metadata and creates a mandatory acquisition for the final video URL. Old page
HTML cannot satisfy that obligation or qualify as authenticated video evidence.

Publication verifies the full proof in a read snapshot and records every SQL read
with its original bound parameters. Under a short writer transaction it rechecks
those result sets, the current lease and final page bytes before committing.
Unrelated intake or worker writes do not restart expensive proof verification;
changed approval dependencies trigger at most three retries within the same lease.
Evidence, review and file checks remain mandatory. Worker exceptions retain private
tracebacks and SQLite extended error codes under the corpus's `failures/` directory.

If an attempt failed after preparing a fully reviewed page, an operator can run
`python -m x_curator --state PRIVATE_STATE complete-publication PUBLICATION_ID --reason "diagnosed commit failure"`.
This command verifies the original complete approval against the current source,
requires an unleased retry/needs-action job, and rejects competing publications or
changed evidence/files. A short fenced transaction completes the page and appends
one unique recovery receipt. Original failed attempts, request history and retry
limits stay unchanged; no model or HTTP request occurs. Repeating a successful
completion revalidates the existing page without duplicating its receipt. Missing
files require separate verified restoration; partial reading cannot use this path.

An exhausted wiki-mapping budget can receive one explicit operator allowance with
`python -m x_curator --state PRIVATE_STATE recover-wiki PUBLICATION_ID --reason "qualified catalog repair"`.
The source must remain published and unmapped, with its current mapping allowance
fully consumed and no live mapping run. The command journals one extra attempt,
with at most two lifetime grants per publication. Prior attempts, model receipts
and failure records remain unchanged. It does not invoke a model; a later normal
wiki cycle must still acquire independent approval before accepting any mapping.
