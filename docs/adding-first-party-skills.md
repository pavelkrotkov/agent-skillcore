# Adding a first-party skill

## Recommended workflow

Keep the deployed checkout on clean `main` and use a worktree:

```bash
ROOT="$HOME/.local/share/agent-skillfleet"
WT="$HOME/worktrees/agent-skillfleet-imessage"
git -C "$ROOT" fetch origin
git -C "$ROOT" worktree add -b skill/imessage-cleanup "$WT" origin/main
cd "$WT"
```

Create `skills/<name>/SKILL.md`. A harmless example is in `skills/skillfleet-example/`.

Suggested session-distillation prompt:

```text
Use the available skill-creation capability to turn the successful workflow
from this session into a reusable Agent Skills skill named <name>.

Write it under skills/<name>/.

The final working procedure is authoritative. Capture failed approaches only
when they are useful as pitfalls or troubleshooting guidance.

Requirements:
- conform to the portable Agent Skills standard;
- keep SKILL.md concise;
- use portable standard frontmatter;
- move detailed platform-specific material into references/;
- put deterministic reusable operations into scripts/ where appropriate;
- include prerequisites, failure modes, verification and recovery;
- do not include credentials, temporary paths, conversation-specific IDs or
  facts unique to this run;
- add representative eval cases for behavior that matters.
```

Codex and Claude can use their own skill-creation capabilities, but Skillfleet does not require a particular command name. Validate from the worktree:

```bash
bin/skill-validate --manifest-only
make test
git diff --check
```

Open a PR with a focused description. Review checklist:

- frontmatter and directory comply with the Agent Skills standard;
- instructions work on macOS and Ubuntu where applicable;
- no personal, account, or machine assumptions leaked in;
- destructive operations have confirmation, backup, and recovery behavior;
- prerequisites and failure modes are explicit;
- scripts are deterministic and tested;
- trigger description is neither too broad nor too narrow;
- no credentials, unsafe downloads, or unexpected native-agent coupling.
