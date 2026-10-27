# Native media, target crops and offline reports

## Prerequisites and extraction

Probe installed ffmpeg/ffprobe capabilities and available image/GIF tooling. Do not assume a specific Python imaging library, codec or option exists. Configure staging, TMPDIR and dependency caches under the authorized storage root before processing. Preserve originals until destination size, hash and decoding have been verified; do not delete originals just because a copy command returned success.

For a selected video stream, inspect actual timestamps, for example:

```sh
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,time_base,avg_frame_rate -show_entries frame=best_effort_timestamp_time -of json "$SOURCE"
```

Pass commands as subprocess argument arrays when writing helpers; do not interpolate paths or metadata into a shell. Decode native frames with ffmpeg's supported passthrough timing (`-fps_mode passthrough` on recent versions). Avoid an fps filter, keyframe-only extraction, or assuming index/30 is source time. For frame-index selection use a validated select filter, passthrough mode and a known start number; preserve the selected stream's presentation timestamp mapping. Probe seeking behavior: fast input seeking alone can begin at a keyframe or reset timestamps. Verify actual first/last source frames and bounds. Handle nonzero initial PTS and variable frame rate explicitly.

Keep a full-context MP4 in addition to the requested short target export. Setter touch or next contact may lie outside a four-second attack window; extend context independently and label source evidence outside the GIF range.

## Full-body tracking and GIF construction

Establish target ROI/identity from the human-confirmed clip and continuous source frames. Track feet and maximum hand reach as well as torso. Choose adaptive or padded crop bounds that contain the body through approach, jump and landing. Stabilize jitter without lagging behind fast movement. If target is obscured or outside the source image, preserve context and flag missing evidence; do not hallucinate body parts or replace the target with a nearby player. A smoothing algorithm cannot guarantee containment: check every frame after smoothing.

Crop overlays and detector coordinates must be transformed consistently from original-image coordinates. Run any detector on the target ROI, not a full-team pass presented as target-only analysis. Reject off-target detections and impossible joint jumps. Frame contact sheets should include preparation, takeoff, full reach, landing and recovery, plus any minimum edge-clearance frames. Preserve feet even when this requires zooming out temporarily.

Define the export as a half-open source-time window [start, end). Select frames by presentation time within that window and retain the next frame timestamp or a reliable decoded duration to bound the final dwell. For each selected frame, bound its display interval by the next presentation time and export end; record any gap between requested start and first selected frame. If the final source duration is unavailable, mark timing unresolved rather than inventing a terminal delay.

Create the GIF from every selected native frame unless the user authorizes resampling. Use palette generation/dithering appropriate to the footage. GIF delays use centiseconds: quantize cumulative presentation times, then difference them so rounding does not drift across the animation; preserve original timestamps separately. If duplicate frames are coalesced, document the index mapping and retain a frame-addressable native viewer; when literal frame-by-frame GIFs are requested, disable coalescing and verify decoded frame count. If native cadence cannot be represented (for example frames less than one centisecond apart), disclose that limit and offer a native-video/frame viewer rather than claiming exact GIF timing. Verify decoded pixels, dimensions, frame count, delay sum and contact alignment after encoding. Keep clean media available alongside optional skeleton overlays.

## Standalone HTML

Use local HTML/CSS/JS with embedded data URIs for offline single-file delivery. A folder with linked media is a different deliverable: use it only if agreed. Include a sample selector, clean/overlay view when available, play/pause, previous/next native frame, scrubber, event jumps and GIF download. Synchronize diagrams using the selected frame's saved source timestamp; do not use independent animation timers or assume GIF decoder index means a fixed FPS. Preserve original source time in captions. If an evidence event lies outside the GIF interval, show that evidence timestamp and the nearest GIF frame separately; don't imply simultaneous images.

Keep unknown diagram points absent. Distinguish visible floor anchors, interpolated display positions, last-ground reference regions, receiver zones and actual ball landings with separate labels/styles. Do not animate a fictional ball flight. A static SVG or canvas is sufficient; avoid external CDN dependencies. For large embedded files stream payloads and write a candidate next to the final file on the same filesystem for atomic rename. Back up the current report before replacement. Do not read a multi-hundred-megabyte base64 document repeatedly just to patch captions.

## Verification and recovery

- Compare the exact eligible ID set and decision/source hashes against the canonical human review file. Confirm no excluded/unsure identity slipped into an export.
- Decode every GIF; verify frame count, dimensions, delays, source mapping and file hash. Visually inspect every clip for correct identity, body containment and pose contamination, with denser review around occlusions/edges.
- Verify source and output windows, contact/event jumps, camera changes, timestamp monotonicity and calibration holdouts. Do not infer positions from airborne anatomy.
- Exercise sample switching, stepping, scrubbing, playback, evidence clocks, null events and JSON/CSV/media downloads. Check embedded payload hashes, missing resources and duplicate DOM IDs.
- Open the completed report offline in an available permitted browser and inspect layout and frames. DOM/mock tests establish control behavior only; disclose if real visual inspection was unavailable. Respect tool/browser file-access restrictions rather than circumventing them.
- Read back the published path and hashes. On failure keep the previous report live and repair the candidate. Record replaced reports as superseded so future agents do not reuse mistaken attribution.
