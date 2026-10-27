# ADR-0003 — Generated runtime plus thin agent adapters

## Status

Accepted

## Context

Codex, Claude Code, and Hermes share portable Agent Skill content but expose it through different discovery/configuration surfaces. Three copied installations would drift.

## Decision

Build one generated runtime and use thin adapters: managed symlinks for Codex/Claude and a generated Hermes `external_dirs` fragment. Native extensions are optional manifest metadata and explicit operations.

## Consequences

Portable content has one provenance and one update path. Hermes configuration still needs a deliberate user merge because Skillfleet does not own unrelated YAML settings.
