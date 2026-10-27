# ADR-0004 — No automatic upstream deployment

## Status

Accepted

## Context

Skills are executable/procedural instructions. A new upstream commit can change agent behavior even when no conventional program binary changed.

## Decision

Upstream checks produce candidate locks and review diffs. Validation and tests run before a PR. There is no automatic merge and no production activation until the reviewed lock reaches `main` and a machine sync succeeds.

## Consequences

Updates require human or independent-agent review. Fleet behavior changes more slowly, but the change is explainable and reproducible.
