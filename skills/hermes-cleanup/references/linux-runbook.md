# Linux runbook

Examples run **on the confirmed Linux target**, not on the controlling Mac.
Discover the actual home and paths; these are inspection commands, not a bulk
cleanup script. Bound scans to relevant filesystems and narrow large output.

## Baseline and attribution

```sh
hostname
id
cat /etc/os-release
findmnt -T /
df -B1 /
df -i /
du -x -h --max-depth=1 "$HOME" 2>/dev/null | sort -h
docker system df -v
docker ps -a --format '{{.Names}} {{.Image}} {{.Status}}'
sudo -n true
```

Use `du -x` for allocated blocks within one filesystem. Inspect root directories
with privileges only if available; permission errors mean coverage is partial.
GNU `du` normally counts multiply linked files once per invocation; independent
treemaps and multiple scans can count them differently. Inspect large files
with `stat` when accounting disagrees. Deleted-open files can explain a large
`df`/`du` gap; use `lsof +L1` if available and discuss the owning service before
restarting it.

Run `diskonaut <inspected-directory>` in an interactive terminal for a treemap;
`ncdu -x <directory>` is an alternative explorer. Check availability first.
Use the distribution package manager when authorized and privileges permit.
For a user-local official binary, verify architecture and published checksum or
signature before installation; stop if provenance cannot be verified.

## Category checks and narrow cleanup

**Docker:** inspect stopped containers, mounts and writable layers before a
prune. `docker system prune -af` removes all stopped containers, unused networks,
images not referenced by a container, and build cache; it is appropriate only
when that full scope is authorized and checked. Prefer a narrower image or
builder prune when stopped containers must remain. Do not add `--volumes`.
Capture running container IDs, start times and health before and after.

**Caches:** measure npm, pip, uv and pre-commit separately. Where authorized,
use `npm cache clean --force`, `python3 -m pip cache purge`, or `uv cache clean`
for the selected tool. Inspect `.npm/_npx` before removing inactive tool copies.
Playwright browsers, Codex runtimes and Skillfleet materializations may live in
cache directories yet be active dependencies; do not bulk-delete `.cache`.

**Old Codex releases:** inspect `~/.codex/packages/*/current`, their `releases/`
siblings, `/proc/*/exe`, service units and launcher references. Current links
alone are insufficient: a running process may use an older version. Preserve
all referenced releases, including required rollback versions. Remove only
individually verified version directories. Restricted process visibility means
absence from `/proc` is not conclusive for other users' installations.

**Downloaded installers:** `.deb` downloads can be removed when installation or
extraction is complete and no launcher, update procedure or recovery policy
requires them. Confirm the program runs from its installed/extracted files.
Delete the download, not the runtime tree; verify the active program afterward.

**Logs and apt:** inspect `journalctl --disk-usage`, rotated-log sizes and apt
archives. With authorization and privileges, a bounded retention policy such as
`sudo -n journalctl --rotate --vacuum-size=200M` removes archived journals while
retaining recent logs; disclose loss of older diagnostics. `sudo -n apt-get
clean` removes downloaded packages. `apt-get -s autoremove` is inspection only;
review its package list before any authorized removal. If sudo is unavailable,
report the remaining bytes and blocked commands; do not work around permissions.

**BleachBit:** install only if requested/authorized. `bleachbit --list-cleaners`
shows available rules; use `bleachbit --preview <selected-cleaners>` to inspect.
Cleaner names and effects vary by release. Generic cache rules can select
needed browser/runtime dependencies, and rotated-log rules may include archived
journals. A preview may report commands with unknown byte savings. Never infer
permission to execute them from the preview total.
