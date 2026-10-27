# Hermes adapter

Hermes discovers read-only external skill directories through
`skills.external_dirs` in `~/.hermes/config.yaml`. Skillfleet writes the
following generated fragment after a successful assembly:

```yaml
skills:
  external_dirs:
    - /path/to/agent-skillfleet-runtime/current
```

The exact file is under `AGENT_SKILLFLEET_STATE/hermes/external-skills.yaml`.
Review and merge it into the correct Hermes profile configuration manually.
This preserves unrelated settings and avoids an unsafe ad-hoc YAML rewriter.

Hermes local skills take precedence over external directories. That is useful
but means a duplicate name in `~/.hermes/skills/` can shadow a Skillfleet skill;
the managed runtime itself still rejects first-party/external collisions.

References: [Hermes external skill directories](https://github.com/mudrii/hermes-agent-docs/blob/main/user-guide/features/skills.md) and [Hermes skill system](https://hermes-agent.nousresearch.com/docs/guides/work-with-skills/).
