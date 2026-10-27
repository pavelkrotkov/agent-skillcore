# ADR-0002 — External skills as locked dependencies

## Status

Accepted

## Context

Copying upstream repositories or maintaining one installer per skill loses provenance, duplicates content, and makes upgrades hard to review.

## Decision

Manifest entries record URL and path. The lockfile records an exact commit. One cached Git repository is reused for multiple paths, and exact trees are materialized without editing the cache.

## Consequences

Initial bootstrap needs network access, but later runtime use can continue from the cache. Updates are explicit lockfile changes and can be reviewed as Git diffs.
