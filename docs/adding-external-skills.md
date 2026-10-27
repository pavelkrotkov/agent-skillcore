# Adding an external skill

1. Identify the canonical repository and default branch using GitHub or the upstream documentation.
2. Inspect the current tree and choose a path that contains a portable `SKILL.md`.
3. Check the repository license and whether agent-specific plugin files are optional.
4. Add the reference to `external/skills.yaml`; do not copy the repository into this checkout.
5. Resolve and review the candidate lock in a branch.

Example:

```yaml
- name: upstream-code-review
  repo: https://github.com/example/skills.git
  path: skills/code-review
  track:
    branch: main
  deployment:
    codex: shared
    claude: shared
    hermes: shared
```

Then:

```bash
bin/skill-update --check
bin/skill-diff --old external/skills.lock --new external/skills.lock.candidate
bin/skill-update --apply
bin/skill-validate --manifest-only
```

Commit the manifest, lockfile, and any review notes in a PR. The current manifest includes Matt Pocock’s MIT-licensed `skills/engineering/code-review` and `skills/engineering/tdd`, and the MIT-licensed portable `skills/i-have-adhd` entry from `ayghri/i-have-adhd`. The ambiguous “Clean” source is intentionally not included.

If a repository contains native hooks/plugins, select only the portable path unless you have separately reviewed the native package. Native commands must be declared explicitly and require `--allow-native` at runtime.
