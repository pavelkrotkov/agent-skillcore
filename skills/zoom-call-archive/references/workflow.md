# Commands and recovery

Use absolute paths in agent-facing outputs and quote shell variables. Replace
example paths with the source/destination discovered in the current session.
Do not put private content or paths in a public PR or skill bundle.

## Probe, extract and transcribe

```bash
ffprobe -v error -show_format -show_streams -of json "$VIDEO"
# For a single AAC audio track; retain the original video separately.
ffmpeg -v error -n -i "$VIDEO" -map 0:a:0 -vn -c:a copy "$AUDIO"
"$MACPARAKEET" transcribe --help
MACPARAKEET_TELEMETRY=0 "$MACPARAKEET" transcribe "$AUDIO" \
  --engine parakeet --parakeet-model v3 --mode raw \
  --speaker-detection off --no-history --database "$WORK/history.sqlite" \
  --format json --output-dir "$WORK/default"
MACPARAKEET_TELEMETRY=0 "$MACPARAKEET" transcribe "$AUDIO" \
  --engine parakeet --parakeet-model unified --mode raw \
  --speaker-detection off --no-history --database "$WORK/history.sqlite" \
  --format json --output-dir "$WORK/unified"
```

Locate the installed CLI using executable discovery or the app bundle. Treat
CLI help as authoritative if flags/schema changed. Run models sequentially to
avoid device-memory contention. Sandbox failures can involve app-owned logs;
use the normal environment permission flow, not private-directory workarounds.
Failing speaker-model prerequisites do not justify invented diarization.

Extract JSON text from recognized segments and their `startMs`/`endMs`, checking
the actual schema first. Preserve `engineVariant`, `durationMs`, status and raw
JSON. Generate 30-second comparison windows from word timestamps when available;
otherwise use segment timestamps and disclose coarse alignment. Spot-check names,
negation, dates, percentages, fees and policy/product names. A shorter output may
mean fewer fillers or omitted words; word count alone cannot determine accuracy.

## Screenshare review

Run the helper with `python3 "$SKILL/scripts/archive_call.py"`; `--help` documents
each command. Sampling and dedupe require Pillow. Extraction/publication do not.

```bash
python3 "$SKILL/scripts/archive_call.py" sample "$VIDEO" "$WORK/samples"
python3 "$SKILL/scripts/archive_call.py" dedupe "$WORK/samples"
# Optional region uses ORIGINAL VIDEO coordinates: x,y,width,height.
python3 "$SKILL/scripts/archive_call.py" dedupe "$WORK/samples" \
  --region 200,120,1200,800 --report "$WORK/content-review"
python3 "$SKILL/scripts/archive_call.py" extract "$VIDEO" \
  "$CALL/screenshares/001_report.png" --seconds 180 --crop 200,120,1200,800
```

Inspect `sample.json` to verify coverage. Targets are 0, 5, 10 seconds etc.; the
selected frame is the first decoded frame at/after each target. Thumbnail
difference is a conservative candidate filter, not semantic deduplication.
The 0.6/255 default compares grayscale images globally against every retained
candidate; the region option reduces speaker noise. The `all-samples/` sheets retain every target for mandatory visual review: a small
changed number can fall below the candidate threshold. Never delete raw source
frames based only on this threshold. Check the final crop at readable resolution.

If sharing layout changes, review full frames too. A region suitable for one
layout can omit new content in another. If sampling or dedupe fails, use a fresh
work directory and retain the source; do not reuse a partial sample directory.
Five-second sampling can miss shorter displays. Increase density around spoken
references/visible transitions or use a separately validated scene-change pass
when stronger coverage is required. Do not claim frame-by-frame visual review.

## Publication

```bash
python3 "$SKILL/scripts/archive_call.py" publish "$CALL" "$EXISTING_ADVISOR/calls/$CALL_NAME"
```

Parent existence is necessary but does not prove a share is mounted. Check the
known archive index/mount first. Source and destination cannot overlap. Symlinked
content and destination ancestors are refused. Publication uses a sibling lock,
an exclusive destination mkdir and exclusive file creation. It refuses an
existing target, including one created concurrently by a non-cooperating writer.
The directory is visible while copying; only a valid final `publication.json`
receipt marks completion. That receipt records SHA-256 and size for every source
file, excluding the receipt itself.

New directories and files use normal mkdir/open permissions, the caller's umask
and inherited destination ACLs. Inspect the effective share policy and intended
collaborator access before claiming the folder is shared; do not broaden access
with chmod without authorization. No owner-only temporary-directory mode is
silently carried into the published folder.

If copying fails, the source stays intact and the incomplete destination stays
for inspection without a valid completion receipt. The command releases its own
lock. Never treat a partial receipt or directory existence as success. A retry
requires inspecting that exact incomplete destination; do not automatically
replace or delete it. If a lock remains after process death, verify no publisher
is active before removing that exact lock. Hash the original recording at both
locations before any separately authorized cleanup. Shared files can become
unavailable later; completion means they were copied and verified at the recorded
time, not a guarantee of future mount availability.
