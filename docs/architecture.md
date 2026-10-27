# Architecture

## Source, cache, runtime

There are three different states:

| State | Location | Authority | Mutable by normal operation |
|---|---|---|---|
| Checkout | `AGENT_SKILLFLEET_ROOT` / the Git clone | Git and reviewed `main` | only through Git workflows |
| Upstream cache | `AGENT_SKILLFLEET_CACHE` | disposable fetch/materialization cache | yes |
| Runtime | `AGENT_SKILLFLEET_RUNTIME` | generated from checkout + lockfile | yes, by atomic activation |

The default runtime is intentionally outside the checkout. `runtime/current` is a symlink to a release directory. A release snapshots first-party skills into that immutable release and links external skills into locked materialized cache paths. The active first-party runtime therefore remains usable if the source checkout is moved or removed. Activation replaces only the `current` pointer, so a failed dependency fetch or validation leaves the previous release active.

## Manifest and lock

`external/skills.yaml` is policy: name, repository, in-repository path, tracking ref, deployment mode, and optional native operation declarations. `external/skills.lock` is resolution: stable name ordering, repository/path identity, and a full immutable commit SHA. A repository is cached once even when multiple manifest entries use different paths.

No HTML scraping is used. Git resolves refs, checks commits, archives the exact tree, and supplies review diffs.

## Runtime and adapters

The portable layer is a normal Agent Skill bundle. Codex and Claude use managed symlinks under their documented user skill directories. Ownership is recorded by a marker file in each directory and a state directory; Skillfleet removes only symlinks listed by its marker, and preserves unrelated files and links. Broken links belonging to the marker are safe to repair/remove.

Hermes supports `skills.external_dirs` as a read-only discovery configuration. Skillfleet writes a generated fragment under state and reports it; it does not merge arbitrary YAML because doing so safely would require owning the user's full Hermes config. See `adapters/hermes/README.md`.

Native packages remain represented in the manifest but do not get their commands executed by bootstrap or sync unless the user passes `--allow-native`. The command is printed first. Native plugins are an opt-in enhancement, not a prerequisite for portable skills. A native plugin that executes skill code must resolve that code from the active Skillfleet runtime rather than maintaining a second controller copy.

## Candidate flow

```text
clean canonical main
        ↓ fetch + fast-forward only
locked commits and patches
        ↓ shared cache + isolated materialization
candidate release
        ↓ structural, provenance, path, and secret checks
atomic current-pointer activation
        ↓ ownership-aware links and Hermes fragment
filesystem exposure verified
```

Validation is intentionally split into three domains. `skill-validate --source` is the offline deterministic source/CI check and is the default. `skill-validate --runtime` checks the materialized deployment without invoking third-party reference tooling. `skill-validate --reference` is an explicit opt-in and fails clearly when `skills-ref` is unavailable. Merely installing `skills-ref` on `PATH` cannot change source or runtime validation.

Updates use the same candidate path but write the lockfile only with `--apply`; they never activate, merge, or push. CI runs the same `make check` command used before a push; after its pinned dependency installation, all required validation is network-independent.

## Agent documentation verified

These links were checked before implementation:

- [Agent Skills specification](https://agentskills.io/specification): `SKILL.md` frontmatter and optional supporting directories.
- [Codex build-skills guide](https://developers.openai.com/codex/skills/): current Codex skill authoring/discovery documentation.
- [Claude Code skills](https://code.claude.com/docs/en/slash-commands): user directory `~/.claude/skills/`, project skills, symlink-friendly filesystem discovery, and live changes.
- [Hermes external skill directories](https://github.com/mudrii/hermes-agent-docs/blob/main/user-guide/features/skills.md): `skills.external_dirs`, read-only discovery, and local precedence.
- [skills-ref source](https://github.com/agentskills/agentskills): optional reference validator, invoked only by the explicit `--reference` validation mode.
- [GitHub CLI repository creation](https://cli.github.com/manual/gh_repo_create) and [PR creation](https://cli.github.com/manual/gh_pr_create): used for the publication workflow.

Agent behavior can change independently of this repository. `skill-doctor` reports filesystem exposure, not semantic loading.

## Security and trust model

1. Reviewed repository commits and explicit dependency locks define the trust boundary.
2. The lockfile pins upstream content to immutable commits.
3. Resolving a newer upstream commit is not approval; it requires a reviewed PR.
4. External update PRs are never automatically merged.
5. Native installer/update/check commands never run automatically.
6. Runtime generation does not execute skill scripts merely to install a skill.
7. `skill-diff` surfaces `SKILL.md`, script, executable-mode, and new executable changes for review.
8. Cached repositories can be deleted and recreated; they are not canonical.
9. Manifests never contain credentials.
10. Unclear-license sources are referenced only after review, not vendored.
11. Personal skills and account-specific preferences belong in private companions.
12. Public release requires a separate sanitization/generalization pass.

## Exit codes and failure behavior

Commands return `0` on success. Expected operational errors return `1`. `skill-update --check` returns `2` when it finds an update, allowing CI to distinguish “updates exist” from “the check failed.” Sync refuses dirty or non-`main` checkouts and never uses `git reset --hard`. Candidate validation happens before the current pointer changes.
