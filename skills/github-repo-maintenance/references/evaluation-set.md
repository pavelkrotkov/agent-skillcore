# Evaluation set

Use mocked GitHub responses unless explicitly testing a disposable live
repository.

## Protection

1. **Public default main:** an owned public repository has default branch
   `main` and no managed ruleset. Expect dry-run CREATE and no mutation; with
   `--apply`, expect one active ruleset targeting `~DEFAULT_BRANCH`.
2. **Non-main default:** an owned public repository uses `master` or `develop`
   as its default. Expect the same `~DEFAULT_BRANCH` ruleset without any
   branch-name special case.
3. **Existing managed ruleset:** the repository already has
   `Skillfleet: Protect default branch`. Expect UPDATE of that ruleset rather
   than creation of a duplicate.
4. **Unrelated ruleset:** another ruleset requires status checks or reviews.
   Expect it to remain untouched; the managed ruleset is created or updated
   independently.
5. **Solo PR workflow:** inspect the payload and confirm the pull-request rule
   requires PRs while `required_approving_review_count` is zero.
6. **No admin permission:** the repository is visible but the caller lacks admin
   permission. Expect SKIP and no write.
7. **Visibility scope:** `protect --all` selects public repositories by default.
   `--visibility private` or `all` changes only repository selection.

## Pruning

8. **Already integrated:** an unprotected feature branch has no open PR and its
   tip is an ancestor of the default branch. Expect a candidate in dry-run and
   deletion only with `--apply`.
9. **Squash/rebase merge:** the feature tip is not an ancestor of default, but a
   merged PR to the current default records that exact head SHA and its merge
   result remains reachable from default. Expect a candidate.
10. **Branch reused after merge:** a merged PR exists, but the branch tip changed
    afterward. Expect no candidate.
11. **Default rewritten after merge:** a merged PR records the current branch
    head, but the PR merge result is no longer reachable from the current default
    branch. Expect no candidate.
12. **Open PR:** an otherwise integrated branch is the head of an open PR in the
    repository. Expect no candidate, including during the pre-delete recheck.
13. **Protection race:** a candidate becomes protected after discovery. Expect
    the apply-time recheck to skip it.
14. **Long-lived names:** `develop`, `gh-pages`, and `release/1.x` are
    integrated. Expect them to be kept by default; confirm `--no-default-keeps`
    changes only that naming safeguard, not the other safety rules.
15. **Fork:** an owned fork contains a stale-looking branch. Expect the repository
    to be skipped unless `--include-forks` is explicit.
16. **Audit failure:** the audit log is not writable. Expect `--apply` to stop
    before any deletion.
17. **Race after dry-run:** the branch SHA changes between candidate discovery
    and deletion. Expect no deletion.
