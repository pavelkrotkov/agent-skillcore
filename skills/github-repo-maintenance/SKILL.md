---
name: github-repo-maintenance
description: Safely protect GitHub default branches and prune obsolete remote branches with deterministic rules. Use when enforcing pull-request-only default-branch changes, preventing force-pushes or deletion, or cleaning merged and fully-integrated branch clutter across one repository or an owned repository fleet.
license: MIT
---

# GitHub Repository Maintenance

Use the packaged dispatcher for repository branch lifecycle maintenance. Keep
protection and pruning deterministic; do not ask a model to decide whether a
branch is obsolete or whether a protection rule should be bypassed.

## Prerequisites

- Bash and the GitHub CLI (`gh`).
- `gh` authenticated with repository read access for dry runs.
- Repository admin access to create or update rulesets.
- Contents write access to delete obsolete branches.
- Review the dry run before any interactive `--apply` unless the exact same
  command and repository scope was already reviewed.

## Commands

Use the single dispatcher:

```bash
bash ./scripts/github-repo-maintenance.sh protect --all
bash ./scripts/github-repo-maintenance.sh prune --all
```

The existing `prune-branches.sh` entrypoint remains available for compatibility.

### Protect default branches

`protect` manages exactly one repository ruleset named
`Skillfleet: Protect default branch`. It targets GitHub's
`~DEFAULT_BRANCH` token rather than a literal branch name, so the policy follows
future default-branch renames and also covers repositories whose default branch
is `master` or `develop`.

The managed ruleset is active and enforces:

- no deletion of the default branch;
- no force-push/non-fast-forward update;
- changes must arrive through a pull request;
- zero required approving reviews.

Zero required approvals is deliberate for solo and coding-agent workflows: a PR
is still mandatory, but the repository owner is not forced to obtain another
reviewer merely to merge their own agent-generated change.

The command is dry-run by default. For all owned public repositories:

```bash
bash ./scripts/github-repo-maintenance.sh protect --all
bash ./scripts/github-repo-maintenance.sh protect --all --apply
```

Use `--owner OWNER` to choose another owner and
`--visibility public|private|internal|all` to change the `--all` scope. Use
`--repo OWNER/REPO` one or more times for an explicit repository list.

On apply, the command creates the managed ruleset when absent and updates that
same named ruleset when present. It never deletes, renames, or rewrites unrelated
rulesets. GitHub combines all applicable rulesets, so stricter pre-existing rules
continue to apply.

### Prune obsolete branches

`prune` is dry-run by default and only proposes a branch when all applicable
checks succeed. It never deletes the default branch, a protected branch, a
branch matching a keep pattern, or a branch with an open pull request in the
repository. Forks are skipped by default because a branch in a fork may be the
head of an open pull request in another repository.

A branch is obsolete only when one of these deterministic proofs holds:

1. its current tip is already reachable from the repository's current default
   branch; or
2. a merged pull request targeted the current default branch, the PR's recorded
   head SHA still equals the branch tip, and the PR merge result is still
   reachable from the current default branch.

The second rule covers squash and rebase merges without treating branch age,
naming, inactivity, or model judgment as evidence of obsolescence.

Immediately before deletion, the script rechecks the branch SHA, effective
protected status, and open-PR state. `--apply` also requires a writable audit
log and records the repository, branch, SHA, and reason before issuing DELETE.

Default keep patterns are `develop`, `development`, `staging`, `production`,
`prod`, `gh-pages`, `release/*`, `releases/*`, `support/*`, and
`archive/*`. Add deployment-specific patterns with `--keep GLOB`; use
`--no-default-keeps` only deliberately.

Examples:

```bash
bash ./scripts/github-repo-maintenance.sh prune --repo OWNER/REPO
bash ./scripts/github-repo-maintenance.sh prune --all
bash ./scripts/github-repo-maintenance.sh prune --all --apply
```

Use `--include-forks` only after considering cross-repository PRs,
`--verbose` to show skip reasons, and `--audit-log FILE` to choose the
recovery log location.

## Unattended operation

For either command, first review the identical dry-run command interactively,
then schedule the same scope with `--apply`. A nonzero exit status means at
least one API or mutation error occurred; do not interpret a partial run as
complete maintenance.

## Prune recovery

The default deletion audit log is
`${XDG_STATE_HOME:-$HOME/.local/state}/github-repo-maintenance/deletions.tsv`.
Each planned and successful deletion records the old branch SHA. Restore a
mistaken deletion promptly with:

```bash
gh api -X POST repos/OWNER/REPO/git/refs \
  -f ref='refs/heads/BRANCH' -f sha='RECORDED_SHA'
```

Do not restore from memory or a guessed SHA. Git object retention is not a
backup guarantee, so recover promptly if needed.

See [evaluation-set.md](references/evaluation-set.md) for representative safety
cases.
