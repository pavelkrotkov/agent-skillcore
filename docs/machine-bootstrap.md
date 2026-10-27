# Machine bootstrap and synchronization

## First machine or fresh clone

```bash
git clone git@github.com:pavelkrotkov/agent-skillcore.git \
  ~/.local/share/agent-skillfleet
~/.local/share/agent-skillfleet/bin/bootstrap
```

Bootstrap checks Git/Python, creates external cache/runtime/state directories, materializes locked commits, validates a candidate, activates it, installs only managed Codex/Claude links, writes the Hermes fragment, and runs doctor. It is idempotent. `--dry-run` prints the plan without changing directories.

## Subsequent machines

Run the same command after cloning. For a normal clean checkout:

```bash
cd ~/.local/share/agent-skillfleet
bin/skill-sync
```

Sync refuses dirty work, non-`main` branches, non-fast-forward updates, and invalid candidates. It never resets local work. If GitHub is temporarily unavailable, the last activated runtime remains usable; a failed new fetch does not replace it.

## Agent links

Codex links point to `~/.agents/skills/<name>`. Claude links point to `~/.claude/skills/<name>`. Each directory gets `.agent-skillfleet-managed`, and only entries listed there can be removed as stale. A regular file, directory, or unowned symlink causes a safe refusal rather than an overwrite.

Hermes is intentionally manual:

```bash
cat ~/.local/state/agent-skillfleet/hermes/external-skills.yaml
```

Merge the `skills.external_dirs` entry into the appropriate Hermes profile config. The configured path is read-only for discovery. Do not replace a whole `config.yaml` with the fragment.

## Hermes systemd option

Example user-level files are in `adapters/hermes/systemd/`. Copy them to `~/.config/systemd/user/`, edit `AGENT_SKILLFLEET_ROOT` if needed, then explicitly enable them:

```bash
systemctl --user daemon-reload
systemctl --user enable --now agent-skillfleet-sync.timer
```

Skillfleet never installs or enables this timer automatically.
