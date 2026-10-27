# agent-skillcore

Public reusable skills and the Skillfleet distribution engine for Codex,
Claude Code and Hermes. Git is authoritative; generated runtime releases and
agent links are disposable deployment state.

This repository starts from a sanitized snapshot with independent Git history.
Personal skills, account preferences, private records and operational receipts
belong in a private companion or protected machine state. Public CI never
fetches a private companion.

## Contents

Nine first-party skills: `amazon-aliexpress-research`, `email-cleanup`,
`github-repo-maintenance`, `hermes-cleanup`, `skillfleet-example`,
`travel-orchestrator`, `volleyball-video-analysis`, `x-curator`, and
`zoom-call-archive`. Fifteen external skill entries are references to reviewed
public repositories, pinned to exact commits in `external/skills.lock`.
External source is not vendored.

## Install

Choose and authorize a checkout folder first. For an existing checkout:

```sh
export AGENT_SKILLFLEET_ROOT=/absolute/approved/agent-skillcore
"$AGENT_SKILLFLEET_ROOT/bin/bootstrap"
"$AGENT_SKILLFLEET_ROOT/bin/skill-doctor"
```

The engine retains the `agent_skillfleet` package, `AGENT_SKILLFLEET_*`
environment variables and `skillfleet` command names for compatibility.
Set `AGENT_SKILLFLEET_RUNTIME`, `AGENT_SKILLFLEET_CACHE` and
`AGENT_SKILLFLEET_STATE` to authorized locations before running. Bootstrap
reports the generated Hermes `skills.external_dirs` fragment; it does not
rewrite an existing Hermes configuration.

## Updates and validation

```sh
bin/skill-validate --source  # offline source and manifest checks
make check                  # canonical local and CI validation
bin/skill-update --check     # produce a candidate; exit 2 means updates exist
bin/skill-diff               # inspect the candidate
bin/skill-update --apply     # update lock only; no deployment or push
bin/skill-sync               # clean main, fast-forward, validate, activate
```

Upstream revisions require review. Native install/update commands never run
without `--allow-native`. Skills contain executable procedures: review their
source, scripts and permissions before use.

## Private companions

A companion owns its personal `skills/`, manifest and lockfile. It can use
this engine's CLI with `--repo /absolute/approved/companion` and list public
skills as ordinary pinned external dependencies. Dependencies are explicit;
Skillfleet does not recursively import another repository's manifest.

Use one combined runtime and one installer for each set of agent skill
directories. Two independent installers sharing those directories can remove
each other's managed links. Public-only users may install this repository
directly; companion users install the combined bundle from their companion.

Private companions must not be checked out in public CI, passed to public
review services, or included in public issue comments, artifacts or logs.

## Development

Add portable bundles under `skills/<name>/SKILL.md`; keep runtime data outside
skill source. Use branches or worktrees in user-approved folders and run
`make check` before publication. CI uses standard GitHub-hosted runners without
private repositories or service credentials. Secret-backed external review
automation is not enabled in the initial public snapshot.

See [architecture](docs/architecture.md), [adding skills](docs/adding-first-party-skills.md),
[external dependencies](external/README.md) and [the public boundary decision](docs/adr/0005-public-core-private-companions.md).

## Licensing

First-party source is MIT licensed; retain file-level notices. External
dependencies remain under their upstream licenses and are referenced, not
relicensed or vendored by this repository.
