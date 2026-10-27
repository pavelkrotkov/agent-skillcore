# ADR-0002 — Historical Telegram review delivery

## Status

Historical. The current workflow is defined by SKILL.md and
[chat-approvals.md](../chat-approvals.md). This record does not configure a
route or authorize sending a message.

## Context

Direct Bot API messages do not establish the gateway session context needed
to interpret a reply against its originating review digest.

## Historical decision

When an operator explicitly configures Telegram delivery for the retired
archive workflow, deliver through the job's own continuable gateway session
with `deliver=telegram`, `attach_to_session` and
`platforms.telegram.extra.cron_continuable_surface: in_channel`.
Do not substitute raw Bot API `sendMessage` calls for gateway delivery.
Keep route identifiers, message contents and delivery receipts in private state.

An empty queue produces no digest. Durable review records remain separate from
the delivery surface; a queued message is not evidence of observed delivery.
