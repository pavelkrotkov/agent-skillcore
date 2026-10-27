---
name: email-cleanup
description: Audit unwanted email and reduce clutter through source unsubscribes, selective notification settings, or authorized message cleanup. Use for subscription cleanup and spam reviews, rather than daily email summaries or sending replies.
---

# Email cleanup

Reduce unwanted mail while preserving its useful parts. A sender can deliver both promotions and essential messages; judge message types and subscription channels, not just sender names.

## Audit and recommendations

Establish the requested account, label inclusion/exclusion, date range, and action scope. Resolve actual label names rather than assuming a user's spelling matches the mailbox. Carry forward prior approvals and preservation conditions; do not repeat completed source changes.

Use an available mail connector or authenticated API for discovery and message operations. Use browser controls for unsubscribe pages and notification settings that the connector cannot change. For Gmail search and mutation details, read [references/gmail.md](references/gmail.md).

Paginate the requested search. Group recurring mail by subscription/list and message purpose. Screen metadata to find candidates, then inspect full bodies, relevant headers, and source settings before choosing an action. Read beyond generic newsletter templates when a school, financial, service, or travel message may contain deadlines or required steps.

Present parallel recommendations:

1. **Unsubscribe or shut off entirely:** promotional lists, redundant digests, abandoned waitlists, or low-value survey streams.
2. **Reduce or selectively disable:** mixed streams containing useful information alongside promotions, duplicates, or intermediate updates.
3. **Keep:** useful newsletters, statements, receipts, security notices, delivery exceptions, school/counselor logistics, and active correspondence.

Explain what would be suppressed and what would remain. When the user asks for recommendations and confirmation, finish the audit before requesting category approvals. When they directly authorize cleanup, execute the clear targets within that scope; clarify only consequential ambiguities. Approval for this run is not standing permission for future runs.

## Apply the chosen treatment

Prefer a source subscription or notification setting when it has the requested scope. Inspect preference pages for global switches spanning unrelated organizations or channels. Do not disable a whole bank, school, merchant, or delivery stream to remove one promotional subtype.

If useful mail must be retained, check both source preferences and existing filters/cleanup scripts. Keeping a subscription enabled does not protect its messages from a broad labeling or deletion rule. Change existing cleanup rules only within the user's approval; respect an explicit choice to leave them unchanged.

Use a narrow archive rule only when ongoing inbox suppression is wanted and source settings cannot provide it. Describe archive behavior accurately: messages still arrive, remain searchable, and are not unsubscribed. Marking read is a separate choice. Preserve critical exceptions such as statements, cancellations, delivery problems, and payment failures.

For old unwanted messages, deletion may be more appropriate than adding a permanent filter. Apply the user's cutoff; if none is given and it matters, state a reasonable cutoff before acting. Select individual verified promotions/surveys and move them to recoverable Trash. Do not empty Trash or delete whole mixed conversations. Leave future filtering for a later review when the user requests that approach.

For an authorized redundant digest automation, disable only its relevant trigger/function. Verify that it no longer sends and avoid changing unrelated scripts or schedules.

## Verify, recover, and report

An attempted opt-out is not a completed opt-out. Verify a success message, saved preference, or explicit unsubscribed status; reload saved settings when persistence is uncertain. Follow current browser-tool requirements for screenshots and evidence. Avoid persisting tokenized unsubscribe URLs in reusable skill files or public reports.

If a link fails, try a visible alternate footer/preference route or authenticated settings page when available. Stop when the remaining route requires missing access, an email request, or broader suppression than approved. Report the concrete blocker; do not claim success from a redirect to a homepage. Do not bypass approval-review rejections: narrow mixed targets using evidence and complete unaffected work.

Report verified actions, retained message types, and unresolved senders separately. Include search coverage, pagination status, and whether full bodies or only metadata were reviewed. Record message IDs and changed settings in a private action log when useful for recovery. Recover mistaken removals through Trash or label reversal; resubscribe/re-enable source channels when needed.

Regulator complaints are a separate action. If requested, verify current jurisdiction and rules from official sources and collect fresh evidence. An expired link in an old message alone does not establish a present violation. Draft a concrete complaint for review before submitting it.

## Finish and remove temporary files

After verification, remove task-created scratch files and temporary Markdown (`.md`) audits, recommendations, and action reports. Retain enough information to summarize the useful results in the final response, and do not link to files that have been removed. Track exact task-created paths instead of deleting Markdown files by a broad glob. Preserve the skill's `SKILL.md`, references, pre-existing documents, explicitly requested lasting deliverables, and recovery records still needed for unresolved work. Remove remaining temporary records when that work is resolved. Briefly confirm the cleanup in the final response.
