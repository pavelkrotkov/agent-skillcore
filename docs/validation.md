# Validation contract

## Pre-push and CI

Run the same repository gate locally before every push:

```bash
make check
```

GitHub Actions installs the pinned validation toolchain and invokes only `make check`. The gate aggregates independent failures instead of stopping after the first domain, so unit-test, source/manifest, shell, YAML, and secret-scan failures remain separately visible.

`make test` remains a deliberately narrow unit-test command. `make validate` is a compatibility alias for the complete `make check` gate.

## Validation domains

Source validation is the default and is deterministic/offline after dependencies are installed:

```bash
bin/skill-validate
bin/skill-validate --source
```

Deployment validation is explicit and checks the active materialized runtime without external reference tooling:

```bash
bin/skill-validate --runtime
```

The Agent Skills reference validator is a separate opt-in. It is never activated merely because an executable happens to be on `PATH`:

```bash
bin/skill-validate --reference
```

Reference mode fails if `skills-ref` is not installed. It is advisory/external and is not part of required CI.

## Locked external skills

External source is validated at two boundaries. Skillfleet validates the manifest/lock identity and the materialized skill before activation. The upstream repository owns its own implementation-specific tests and quality policy.

The active `github-project-swarm`, `github-project-reviewer`, and `github-project-adjudicator` skills are developed and validated in [pavelkrotkov/gh-swarm](https://github.com/pavelkrotkov/gh-swarm). `external/skills.lock` pins the exact reviewed public commit that reaches the generated Skillfleet runtime. Swarm-specific tests, exact-head CI, dead-code checks, host qualification, and structural complexity gates therefore live with that source rather than being duplicated in this private control-plane repository.

## Reproducibility policy

CI uses Python 3.12 and the exact package versions in `requirements/ci-constraints.txt`. Lock entries use full immutable commit SHAs; runtime provenance records the source repository, path, and commit for each materialized external skill.

`make shellcheck` remains an explicit optional developer lint target. Unlike the required gate, it fails clearly when ShellCheck is missing; `make check` never changes behavior based on whether ShellCheck happens to be installed.
