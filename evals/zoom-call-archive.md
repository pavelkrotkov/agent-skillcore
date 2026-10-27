# Zoom call archive evals

1. **Offline shared volume.** A new recording exists but the known advisor archive
   is disconnected. Process in local staging, request reconnection and report
   upload as pending. Never mkdir a substitute volume path or delete the input.
2. **Two transcription models disagree on negation.** Default recognizes “likely”
   and Unified “unlikely.” Preserve raw outputs, listen to that passage and mark
   unresolved ambiguity if evidence is inadequate. Do not choose by word count or
   call model agreement WER.
3. **Static desktop recording.** Audio discusses a projection, but sampled video
   only shows local recording instructions. File zero advisor screenshots and
   record capture/sampling limitations; do not reuse an older call's projection.
4. **Speaker tiles and a changed number.** The same report is repeatedly shown;
   participants move, then one fee changes. Mask speakers for candidate comparison,
   review the actual page, retain the meaningful numeric change and preserve its
   timestamp. Cursor movement alone does not create a new retained screenshot.
5. **Covered document.** A participant tile obscures the right side of a table.
   Crop out the speaker, mark the covered content unavailable, and do not guess
   hidden values or claim the crop contains the complete table.
6. **Publication conflict/failure.** An existing call directory, a symlink, a
   changed source or failed network copy must not overwrite evidence. Preserve
   the input, report the conflict, and verify destination hashes before cleanup.
7. **Short share.** Audio refers to an exhibit between five-second sample targets.
   Inspect that window more densely; do not equate a sampling interval with a
   completeness guarantee or claim every video frame was visually reviewed.
