# Updating external skills

An upstream `main` change is only a candidate. The normal sequence is:

```bash
bin/skill-update --check
bin/skill-diff --old external/skills.lock --new external/skills.lock.candidate
bin/skill-update --apply
bin/skill-validate --manifest-only
git diff -- external/skills.lock
```

`--check` resolves current tracked refs, writes an ignored review candidate, materializes and validates it, and returns `2` if anything changed. `--apply` repeats the candidate validation and writes only `external/skills.lock`; it does not deploy, merge, push, or execute native commands. `--dry-run` reports what the upstream ref resolves to without changing the lockfile or runtime.

Review `bin/skill-diff` output and the upstream Git diff. Pay special attention to:

- changes to `SKILL.md` instructions or trigger descriptions;
- new scripts, binaries, executable mode changes, or downloads;
- secrets, environment-variable assumptions, and destructive actions;
- license changes and native plugin coupling;
- changes affecting several manifest entries from the same repository.

Commit the lockfile on a branch and open a PR. The scheduled workflow does this mechanically but never auto-merges it. The fleet receives the new revision only after the PR is merged and a later `bin/skill-sync` completes.
