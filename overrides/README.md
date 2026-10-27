# Optional external overrides

Prefer a companion first-party skill. Use a patch only for a small,
reviewable local policy change, and use a fork when divergence is substantial.

For a patchable external skill, create:

```text
overrides/<manifest-name>/series
overrides/<manifest-name>/0001-local-policy.patch
```

List patch filenames in `series`, one per line. Skillfleet copies the locked
upstream materialization, applies the series in order, and stops before runtime
activation if any patch fails. Cached upstream repositories are never edited.
