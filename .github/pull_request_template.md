## Summary

<!-- What changed and why? -->

## Review checklist

- [ ] `make test` passes.
- [ ] `bin/skill-validate --manifest-only` passes.
- [ ] Agent Skills frontmatter and directory names are compliant.
- [ ] macOS/Linux portability was considered.
- [ ] No credentials, personal identifiers, temporary paths, or secrets were added.
- [ ] Destructive actions have safeguards and recovery guidance.
- [ ] External changes include lockfile provenance and an upstream diff review.
- [ ] Native commands/plugins are explicit and not silently executed.
- [ ] ADRs/docs were updated if an invariant changed.
