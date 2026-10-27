# Discovery and human attribution

## Annotated sources

Use authorized downloads or existing originals. Retain annotation/OCR text, source timestamp and uncertainty as candidate evidence. Check team level, match, rotation and player continuity against the video: labels can identify another athlete or a different squad. Deduplicate overlapping proposals without discarding provenance. Record whether the candidate inventory covers the entire requested source range; do not call a sampled inventory exhaustive.

## Unannotated sources

Inventory all requested videos, segments and camera cuts. Build full-court contact sheets at a practical coarse interval, inspect rallies, then sample densely around plausible sets and attacks. Ball motion, audio and pose/event detectors can propose events but do not establish identity or a hit outcome. Keep a coverage ledger of scanned time ranges and gaps. Brief contacts may fall between coarse samples; decode more densely there. No sampling can recover moments absent from the recording.

## Review queue

Use an existing review application if available; otherwise build a local static queue with stable event IDs, full-context video, time controls and Yes/No/Unsure tags answering one question: is the attacking player the target? Show enough pre-attack rotation/approach and post-attack landing to identify the person; support expanding context. Keep the original full-court view available. Keyboard shortcuts are useful but require focus guards around typing and video controls.

Save immediately after a change. Browser localStorage is a convenience cache, not the sole durable archive: support JSON download/import with schema version, queue/source revision, reviewer identity (if supplied), timestamps and revision history. A file-backed server may persist atomically to an explicitly selected workspace, but the queue must explain its actual save behavior; don't claim a browser-only page silently writes a folder. Export CSV too; quote cells, escape embedded quotes/newlines, neutralize spreadsheet-formula cells beginning with =,+,-,@ and retain raw values in JSON. On import validate source IDs/hashes and decisions; detect conflicting revisions rather than overwriting newer work. Unknown IDs or duplicate decisions require reconciliation.

Only Yes entries are eligible. No and Unsure remain archived; never infer a Yes from a filename, jersey detector or previous analyst report. A correction to contact time/action type does not revoke confirmed identity. A changed source or conflicting reviewer identity decision needs explicit reconciliation before dependent analysis. Preserve human decisions in a shared canonical file so other agents use the same attribution.

## Suggested sidecar structure

Use JSON with a documented version and these fields (extend rather than silently repurpose):

- Source: id, original path/URL, sha256, stream index, dimensions, duration, native frame PTS/time base, camera segments.
- Candidate: id, source_id, proposed timestamp, discovery method/label, reviewed context bounds.
- Identity review: candidate_id, source_sha256, decision yes/no/unsure, reviewer, updated_at, revision and prior decisions.
- Event analysis: candidate_id, action type, contact time/window, setter/prior contact time/window, evidence frame IDs, outcome/status. Keep these distinct from identity review.
- Export: candidate_id, review revision, requested/actual bounds, source timestamp for every exported frame, crop coordinates per frame in original pixels, output dimensions, timing/delays, hashes and warnings.
- Court: candidate_id, calibration revision/segment, event times, original-image floor anchors, estimated court coordinates, point semantics, evidence and uncertainty; absent estimates are null with a reason.

Do not require personal reviewer names or embed private media/paths in a public code repository. Use synthetic fixtures for development. Derive coverage counts from records and verify eligible IDs exactly, not just total counts.
