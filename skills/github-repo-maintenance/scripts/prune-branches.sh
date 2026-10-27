#!/usr/bin/env bash
set -euo pipefail

apply=false
scan_all=false
include_forks=false
verbose=false
owner=""
repos=()
default_keeps=true
default_keep_patterns=(develop development staging production prod gh-pages 'release/*' 'releases/*' 'support/*' 'archive/*')
custom_keep_patterns=()
audit_log="${XDG_STATE_HOME:-$HOME/.local/state}/github-repo-maintenance/deletions.tsv"

usage() {
  cat <<'USAGE'
Usage: prune-branches.sh [--apply] [--all [--owner OWNER] | --repo OWNER/REPO ...]
                         [--include-forks] [--keep GLOB ...]
                         [--no-default-keeps] [--audit-log FILE] [--verbose]

Dry-run is the default. Without --all or --repo, scan the repository containing
$PWD. --all scans non-archived repositories owned by OWNER (default: the
authenticated GitHub user). Forks are skipped unless --include-forks is given.
USAGE
}

while (($#)); do
  case "$1" in
    --apply) apply=true ;;
    --all) scan_all=true ;;
    --owner) shift; (($#)) || { echo "--owner needs a value" >&2; exit 2; }; owner="$1" ;;
    --repo) shift; (($#)) || { echo "--repo needs a value" >&2; exit 2; }; repos+=("$1") ;;
    --include-forks) include_forks=true ;;
    --keep) shift; (($#)) || { echo "--keep needs a glob" >&2; exit 2; }; custom_keep_patterns+=("$1") ;;
    --no-default-keeps) default_keeps=false ;;
    --audit-log) shift; (($#)) || { echo "--audit-log needs a path" >&2; exit 2; }; audit_log="$1" ;;
    --verbose) verbose=true ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

command -v gh >/dev/null 2>&1 || { echo "gh CLI is required" >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "gh authentication is required" >&2; exit 1; }

if $scan_all && ((${#repos[@]})); then echo "use either --all or --repo" >&2; exit 2; fi
if [[ -n "$owner" ]] && ! $scan_all; then echo "--owner requires --all" >&2; exit 2; fi

if $scan_all; then
  [[ -n "$owner" ]] || owner="$(gh api user --jq .login)"
  while IFS= read -r repo; do repos+=("$repo"); done < <(
    gh repo list "$owner" --limit 1000 --json nameWithOwner,isArchived \
      --jq '.[] | select(.isArchived == false) | .nameWithOwner'
  )
elif ((${#repos[@]} == 0)); then
  repos+=("$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null || true)")
  [[ -n "${repos[0]}" ]] || { echo "not in a GitHub repository; use --repo or --all" >&2; exit 2; }
fi

matches_keep() {
  local branch=$1 pattern
  if $default_keeps; then
    for pattern in "${default_keep_patterns[@]}"; do [[ "$branch" == $pattern ]] && return 0; done
  fi
  for pattern in "${custom_keep_patterns[@]}"; do [[ "$branch" == $pattern ]] && return 0; done
  return 1
}

say_skip() { $verbose && printf 'SKIP\t%s\t%s\t%s\n' "$1" "$2" "$3" || true; }

prepare_audit_log() {
  local dir
  dir=$(dirname -- "$audit_log")
  mkdir -p -- "$dir"
  chmod 700 -- "$dir" 2>/dev/null || true
  touch -- "$audit_log"
  chmod 600 -- "$audit_log" 2>/dev/null || true
  [[ -w "$audit_log" ]]
}

fresh_branch_state() {
  local repo=$1 wanted=$2 rows branch sha protected
  rows="$(gh api --paginate "repos/$repo/branches?per_page=100" \
    --jq '.[] | [.name, .commit.sha, .protected] | @tsv' 2>/dev/null)" || return 1
  while IFS=$'\t' read -r branch sha protected; do
    if [[ "$branch" == "$wanted" ]]; then printf '%s\t%s\n' "$sha" "$protected"; return 0; fi
  done <<<"$rows"
  return 0
}

candidates=0
deleted=0
errors=0
repos_scanned=0
$apply && prepare_audit_log || true
if $apply && [[ ! -w "$audit_log" ]]; then echo "audit log is not writable: $audit_log" >&2; exit 1; fi

for repo in "${repos[@]}"; do
  meta="$(gh api "repos/$repo" --jq '[.default_branch, .archived, .fork, (.permissions.push // false)] | @tsv' 2>/dev/null)" || {
    printf 'ERROR\t%s\tmetadata lookup failed\n' "$repo" >&2; ((errors+=1)); continue;
  }
  IFS=$'\t' read -r default_branch archived fork can_push <<<"$meta"
  [[ "$archived" == false ]] || { say_skip "$repo" '-' archived; continue; }
  [[ "$can_push" == true ]] || { say_skip "$repo" '-' no-push-permission; continue; }
  if [[ "$fork" == true ]] && ! $include_forks; then say_skip "$repo" '-' fork; continue; fi

  branch_rows="$(gh api --paginate "repos/$repo/branches?per_page=100" \
    --jq '.[] | [.name, .commit.sha, .protected] | @tsv' 2>/dev/null)" || {
    printf 'ERROR\t%s\tbranch listing failed\n' "$repo" >&2; ((errors+=1)); continue;
  }
  ((repos_scanned+=1))
  [[ -n "$branch_rows" ]] || continue

  default_sha=""
  while IFS=$'\t' read -r branch sha protected; do
    [[ "$branch" == "$default_branch" ]] && { default_sha="$sha"; break; }
  done <<<"$branch_rows"
  if [[ -z "$default_sha" ]]; then
    printf 'ERROR\t%s\tdefault branch %s not found\n' "$repo" "$default_branch" >&2
    ((errors+=1)); continue
  fi

  repo_owner=${repo%%/*}
  while IFS=$'\t' read -r branch sha protected; do
    [[ -n "$branch" ]] || continue
    if [[ "$branch" == "$default_branch" ]]; then say_skip "$repo" "$branch" default; continue; fi
    if [[ "$protected" == true ]]; then say_skip "$repo" "$branch" protected; continue; fi
    if matches_keep "$branch"; then say_skip "$repo" "$branch" keep-pattern; continue; fi

    open_count="$(gh api -X GET "repos/$repo/pulls" -f state=open -f "head=$repo_owner:$branch" \
      -f per_page=1 --jq 'length' 2>/dev/null)" || {
      printf 'ERROR\t%s\t%s\topen-PR lookup failed\n' "$repo" "$branch" >&2; ((errors+=1)); continue;
    }
    if ((open_count > 0)); then say_skip "$repo" "$branch" open-pr; continue; fi

    reason=""
    compare_status="$(gh api "repos/$repo/compare/$sha...$default_sha" --jq .status 2>/dev/null || true)"
    if [[ "$compare_status" == ahead || "$compare_status" == identical ]]; then
      reason="contained-in-default"
    else
      merged_rows="$(gh api --paginate -X GET "repos/$repo/pulls" -f state=closed \
        -f "head=$repo_owner:$branch" -f sort=updated -f direction=desc -f per_page=100 \
        --jq ".[] | select(.merged_at != null and .base.ref == \"$default_branch\" and .head.sha == \"$sha\") | [.number, .merge_commit_sha] | @tsv" 2>/dev/null)" || {
        printf 'ERROR\t%s\t%s\tmerged-PR lookup failed\n' "$repo" "$branch" >&2; ((errors+=1)); continue;
      }
      while IFS=$'\t' read -r merged_pr merge_sha; do
        [[ -n "$merged_pr" && -n "$merge_sha" ]] || continue
        merge_status="$(gh api "repos/$repo/compare/$merge_sha...$default_sha" --jq .status 2>/dev/null || true)"
        if [[ "$merge_status" == ahead || "$merge_status" == identical ]]; then
          reason="merged-pr-$merged_pr-head-match"
          break
        fi
      done <<<"$merged_rows"
    fi
    [[ -n "$reason" ]] || { say_skip "$repo" "$branch" not-proven-obsolete; continue; }

    ((candidates+=1))
    printf 'CANDIDATE\t%s\t%s\t%s\t%s\n' "$repo" "$branch" "$sha" "$reason"
    $apply || continue

    fresh="$(fresh_branch_state "$repo" "$branch")" || {
      printf 'ERROR\t%s\t%s\trecheck failed\n' "$repo" "$branch" >&2; ((errors+=1)); continue;
    }
    [[ -n "$fresh" ]] || { say_skip "$repo" "$branch" disappeared-after-scan; continue; }
    IFS=$'\t' read -r current_sha current_protected <<<"$fresh"
    [[ "$current_sha" == "$sha" ]] || { say_skip "$repo" "$branch" changed-after-scan; continue; }
    [[ "$current_protected" != true ]] || { say_skip "$repo" "$branch" protected-after-scan; continue; }

    open_count="$(gh api -X GET "repos/$repo/pulls" -f state=open -f "head=$repo_owner:$branch" \
      -f per_page=1 --jq 'length' 2>/dev/null)" || {
      printf 'ERROR\t%s\t%s\topen-PR recheck failed\n' "$repo" "$branch" >&2; ((errors+=1)); continue;
    }
    if ((open_count > 0)); then say_skip "$repo" "$branch" open-pr-after-scan; continue; fi

    timestamp=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
    printf 'PLANNED\t%s\t%s\t%s\t%s\t%s\n' "$timestamp" "$repo" "$branch" "$sha" "$reason" >>"$audit_log" || {
      printf 'ERROR\t%s\t%s\taudit write failed\n' "$repo" "$branch" >&2; ((errors+=1)); continue;
    }
    if gh api -X DELETE "repos/$repo/git/refs/heads/$branch" >/dev/null 2>&1; then
      ((deleted+=1))
      printf 'DELETED\t%s\t%s\t%s\t%s\t%s\n' "$timestamp" "$repo" "$branch" "$sha" "$reason" >>"$audit_log"
      printf 'DELETED\t%s\t%s\t%s\t%s\n' "$repo" "$branch" "$sha" "$reason"
    else
      printf 'ERROR\t%s\t%s\tdelete failed\n' "$repo" "$branch" >&2
      ((errors+=1))
    fi
  done <<<"$branch_rows"
done

printf 'SUMMARY\trepos=%d\tcandidates=%d\tdeleted=%d\terrors=%d\tmode=%s\n' \
  "$repos_scanned" "$candidates" "$deleted" "$errors" "$($apply && echo apply || echo dry-run)"
((errors == 0))
