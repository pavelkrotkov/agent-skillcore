#!/usr/bin/env bash
set -euo pipefail

apply=false
scan_all=false
owner=""
visibility="public"
repos=()
ruleset_name="Skillfleet: Protect default branch"

usage() {
  cat <<'USAGE'
Usage: protect-default-branches.sh [--apply]
       [--all [--owner OWNER] [--visibility public|private|internal|all]
        | --repo OWNER/REPO ...]

Dry-run is the default. Without --all or --repo, target the repository
containing $PWD. --all defaults to public repositories owned by the
authenticated GitHub user.

The managed ruleset targets ~DEFAULT_BRANCH and enforces:
  - no deletion
  - no force-push/non-fast-forward update
  - changes must arrive through a pull request
  - zero required approving reviews

The script creates or updates only the ruleset named:
  Skillfleet: Protect default branch
It does not modify other rulesets.
USAGE
}

while (($#)); do
  case "$1" in
    --apply) apply=true ;;
    --all) scan_all=true ;;
    --owner) shift; (($#)) || { echo "--owner needs a value" >&2; exit 2; }; owner="$1" ;;
    --visibility) shift; (($#)) || { echo "--visibility needs a value" >&2; exit 2; }; visibility="$1" ;;
    --repo) shift; (($#)) || { echo "--repo needs a value" >&2; exit 2; }; repos+=("$1") ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

case "$visibility" in
  public|private|internal|all) ;;
  *) echo "--visibility must be public, private, internal, or all" >&2; exit 2 ;;
esac

command -v gh >/dev/null 2>&1 || { echo "gh CLI is required" >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "gh authentication is required" >&2; exit 1; }

if $scan_all && ((${#repos[@]})); then echo "use either --all or --repo" >&2; exit 2; fi
if [[ -n "$owner" ]] && ! $scan_all; then echo "--owner requires --all" >&2; exit 2; fi
if [[ "$visibility" != public ]] && ! $scan_all; then echo "--visibility requires --all" >&2; exit 2; fi

if $scan_all; then
  [[ -n "$owner" ]] || owner="$(gh api user --jq .login)"
  if [[ "$visibility" == all ]]; then
    while IFS= read -r repo; do repos+=("$repo"); done < <(
      gh repo list "$owner" --limit 1000 --json nameWithOwner,isArchived \
        --jq '.[] | select(.isArchived == false) | .nameWithOwner'
    )
  else
    while IFS= read -r repo; do repos+=("$repo"); done < <(
      gh repo list "$owner" --limit 1000 --visibility "$visibility" --json nameWithOwner,isArchived \
        --jq '.[] | select(.isArchived == false) | .nameWithOwner'
    )
  fi
elif ((${#repos[@]} == 0)); then
  repos+=("$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null || true)")
  [[ -n "${repos[0]}" ]] || { echo "not in a GitHub repository; use --repo or --all" >&2; exit 2; }
fi

payload() {
  cat <<JSON
{
  "name": "$ruleset_name",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [],
  "conditions": {
    "ref_name": {
      "include": ["~DEFAULT_BRANCH"],
      "exclude": []
    }
  },
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {
      "type": "pull_request",
      "parameters": {
        "allowed_merge_methods": ["merge", "squash", "rebase"],
        "dismiss_stale_reviews_on_push": false,
        "required_approving_review_count": 0,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false
      }
    }
  ]
}
JSON
}

planned=0
created=0
updated=0
errors=0

for repo in "${repos[@]}"; do
  meta="$(gh api "repos/$repo" --jq '[.archived, .visibility, (.permissions.admin // false), .default_branch] | @tsv' 2>/dev/null)" || {
    printf 'ERROR\t%s\tmetadata lookup failed\n' "$repo" >&2
    ((errors+=1))
    continue
  }
  IFS=$'\t' read -r archived repo_visibility is_admin default_branch <<<"$meta"
  [[ "$archived" == false ]] || { printf 'SKIP\t%s\tarchived\n' "$repo"; continue; }
  [[ "$is_admin" == true ]] || { printf 'SKIP\t%s\tadmin permission required\n' "$repo"; continue; }

  existing_id="$(gh api "repos/$repo/rulesets" --jq ".[] | select(.name == \"$ruleset_name\") | .id" 2>/dev/null | head -n 1)" || {
    printf 'ERROR\t%s\truleset lookup failed\n' "$repo" >&2
    ((errors+=1))
    continue
  }

  ((planned+=1))
  if [[ -n "$existing_id" ]]; then
    printf 'PLAN\tUPDATE\t%s\tdefault=%s\tvisibility=%s\truleset=%s\n' "$repo" "$default_branch" "$repo_visibility" "$existing_id"
  else
    printf 'PLAN\tCREATE\t%s\tdefault=%s\tvisibility=%s\n' "$repo" "$default_branch" "$repo_visibility"
  fi
  $apply || continue

  if [[ -n "$existing_id" ]]; then
    if payload | gh api -X PUT "repos/$repo/rulesets/$existing_id" --input - >/dev/null; then
      ((updated+=1))
      printf 'UPDATED\t%s\t%s\n' "$repo" "$existing_id"
    else
      printf 'ERROR\t%s\truleset update failed\n' "$repo" >&2
      ((errors+=1))
    fi
  else
    if payload | gh api -X POST "repos/$repo/rulesets" --input - >/dev/null; then
      ((created+=1))
      printf 'CREATED\t%s\n' "$repo"
    else
      printf 'ERROR\t%s\truleset creation failed\n' "$repo" >&2
      ((errors+=1))
    fi
  fi
done

printf 'SUMMARY\trepos=%d\tcreated=%d\tupdated=%d\terrors=%d\tmode=%s\n' \
  "$planned" "$created" "$updated" "$errors" "$($apply && echo apply || echo dry-run)"
((errors == 0))
