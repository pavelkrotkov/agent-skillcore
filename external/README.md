# External skills

`skills.yaml` is the human-edited dependency manifest. `skills.lock` records
the exact 40-character commit used by Skillfleet. External repositories are
cached below the configured cache directory and materialized into a disposable
cache area; they are never copied into this repository.

The four Matt Pocock entries share one cached clone. `i-have-adhd` is selected
from its portable `skills/i-have-adhd` directory. Its upstream repository also
contains agent-specific plugin files, but those files are not exposed by this
manifest entry.

The six HumanLayer entries select portable `plugins/<name>/skills/<name>`
directories from `humanlayer/skills` (MIT). Supporting references are included;
the repository-level marketplace and native plugin metadata are not deployed.

The vague “Clean” skill mentioned in the design notes is deliberately not
included because its canonical repository is unidentified. Add it only after
confirming the upstream URL, in-repository path, license, and a locked commit.

Update flow:

```bash
bin/skill-update --check
bin/skill-diff --old external/skills.lock --new external/skills.lock.candidate
bin/skill-update --apply
```

`--apply` changes only the working-tree lockfile. It does not activate the
candidate, merge, or push anything.
