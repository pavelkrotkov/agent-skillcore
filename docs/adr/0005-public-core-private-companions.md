# ADR-0005 — Public core, private companions

Status: Accepted

`agent-skillcore` owns reusable source, the distribution engine and public CI.
Personal skills and account-specific preferences live in private companions.
The public repository starts with unrelated Git history from an allowlisted,
sanitized snapshot. Private histories, discussions, Actions logs, operational
receipts and live records are not migrated.

A private companion consumes exact reviewed public commits using the existing
manifest/lock mechanism and runs the public engine against its own root. One
combined runtime owns the managed links. Public CI cannot access the companion.

The engine's existing package and environment-variable names remain compatible.
Publishing an additional personal skill requires a separate sanitization pass.
