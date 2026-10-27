---
name: hermes-cleanup
description: Diagnose disk pressure and reclaim verified unused data on a confirmed Linux host, locally or over SSH, including Docker, caches, obsolete agent runtimes, and disk treemaps. Use for Hermes storage investigations and cleanup, not general Hermes Agent configuration.
license: MIT
---

# Hermes cleanup

Measure first, explain the cause, then remove only authorized, verified unused
material. Read [the Linux runbook](references/linux-runbook.md) for commands
and category-specific checks. Use existing tools; no cleanup daemon is needed.

## Establish the target and baseline

Resolve the user's intended host from existing SSH/configuration context; do
not assume the current computer is Hermes. Verify hostname, OS, user and mounts.
Use noninteractive SSH and privilege checks; never request or expose passwords,
credentials, environment dumps or private keys. If access fails, report the
failure rather than silently investigating another host.

Record filesystem bytes, available space and inode usage, then identify the
largest directories on the pressured filesystem. Check Docker's accounting and
running containers separately. Use a Linux treemap such as Diskonaut when
requested; prefer an existing installation. Install missing tools only within
the authorized scope, using a trusted package source or verified official
release. Report permission barriers without substituting unsafe downloads.

Distinguish allocated disk blocks from apparent sizes, Docker virtual image
sizes, shared layers and hardlinks. Mounts and tmpfs are separate filesystems.
A treemap shows where space lives, not whether it is disposable.

## Decide what can be reclaimed

For each substantial candidate, identify its owner, purpose, size and evidence
of disuse. Separate regenerable caches/installers, obsolete runtime versions,
logs, and application/source data. Check current symlinks, running executables,
services and configuration references before calling a runtime obsolete.

Honor the current request: inspection alone authorizes no deletion. A request
to reclaim caches or Docker reclaimable data covers those categories after
checking what the operation includes. Do not ask again for already authorized
work. If a new destructive category is outside that scope, present concrete
paths, sizes, impact and recovery limits for approval before deleting it.

- Protect current agent binaries, browser installations and runtime packages,
  even under `.cache`; generic cache location does not establish disuse.
- Coordinate with application owners. If another agent is cleaning X-curator,
  leave its state alone. Generated wiki builds, SQLite snapshots and shadow
  trees need application-aware retention checks; preserve the current pointer,
  database, blobs, history and service dependencies.
- Preserve Docker volumes and bind-mounted data unless explicitly approved.
  Stopped containers may hold unique writable-layer data; inspect before pruning.
- Preserve source checkouts, untracked files, sessions, worktrees and backups
  unless their disposal is explicitly authorized and their preservation needs
  have been checked. Age alone is insufficient evidence.
- Never treat a BleachBit preview or broad `--all` result as a safe deletion
  list. Preview selected cleaners first; inspect every affected category.

Use exact inspected paths and narrow commands. Prefer native cache cleaners and
journal retention tools. Explain that removed caches/packages can be rebuilt or
redownloaded; do not promise recovery of deleted unique data. If unique data
needs a backup, agree on its destination and verify the copy before deletion.

## Verify and report

Recheck `df` on the same filesystem and verify the selected targets are gone.
Confirm current runtime links resolve, affected services remain healthy, and
running containers have not unexpectedly stopped or restarted. Report actual
space reclaimed, current free space, remaining candidates and permission
barriers. Concurrent writers or another cleanup can affect `df` deltas; disclose
that rather than claiming all changes as this operation's savings.

Keep diagnostic output in the conversation unless the user selects a report
folder. For moving datasets to an iMac, first establish the exact destination,
capacity and ownership; copy and verify before any authorized source removal.
Do not create a new project workspace, archive or backup layout implicitly.
