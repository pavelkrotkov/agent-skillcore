# ADR-0001 — Git as source of truth

## Status

Accepted

## Context

Agent runtime directories are convenient discovery surfaces but are mutable, machine-specific, and easy to edit accidentally. Treating them as development checkouts would create unreviewed forks.

## Decision

The private GitHub repository and reviewed `main` are authoritative. Runtime, cache, state, and agent links are generated/deployed state. Development happens in branches or worktrees and reaches machines through sync.

## Consequences

Machine-local changes are not silently captured. Sync can refuse dirty canonical work. Recovery is a Git checkout or a new generated runtime, not manual runtime editing.
