# Gmail mechanics

## Search coverage

Resolve display names and IDs through labels/search results. A label informally called `delete-me` might actually be named `delete me`; use the verified name in quoted Gmail queries.

For an outside-label review, a useful starting query is:

```text
-label:"<actual label>" -in:sent -in:drafts -in:trash -in:spam
```

Narrow discovery with `(unsubscribe OR category:promotions)` and a date range, but also inspect a recent general sample: category assignment and the presence of an unsubscribe footer do not prove a message is unwanted. Excluding known useful high-volume streams can help discovery; disclose those exclusions.

Continue using returned page tokens until exhausted or the agreed bound is reached. Respect tool batch limits; a requested result count may be clamped. Deduplicate by message ID. Report the actual coverage rather than calling a sample an entire-mailbox audit.

## Inspect message types

Read MIME text/plain or rendered HTML bodies and relevant `List-Unsubscribe`/`List-Unsubscribe-Post` headers. Distinguish marketing from transactional messages even when they share a From address. Match a newsletter's podcast reminders separately from its written newsletter, delivery progress notices separately from exceptions, and survey requests separately from purchase receipts.

Use a provided unsubscribe mechanism through a supported connector or browser. A one-click header is not necessarily a normal browser page. Prefer a visible footer preference page when the header route fails. Do not improvise authenticated network calls outside supported tools. A mailto opt-out requires an explicitly authorized outbound message; invoking this skill alone does not authorize sends.

## Filters and existing cleanup

Match verified list IDs, dedicated addresses, or distinctive subject patterns. Broad sender/domain rules can catch statements or school logistics. Preview the search matches before saving a rule. When statement preservation is required, inspect existing overlapping labeling/deletion rules as well as the new filter.

Gmail archive removes `INBOX`; it does not delete, unsubscribe, or mark read. `UNREAD` removal is a separate mutation. Keep the user's choices for existing cleanup labels independent from new inbox rules.

## Trash and verification

Prefer the connector's recoverable delete/Trash operation on explicit message IDs. Do not use permanent-delete endpoints. Whole-thread operations can remove useful replies or receipts that were not reviewed.

After mutation, inspect per-message success results and verify the relevant IDs have `TRASH` or no longer match the original non-Trash query. Keep a private ID/action log if recovery is likely to matter. No browser screenshot is needed for connector-only mutations unless the tool or user requires it.
