---
name: pr-green
description: Create or update the current branch's GitHub PR and keep fixing CI, base-branch drift, conflicts, description gates, and review feedback until it is ready to merge. Use for /pr-green, $pr-green, getting a PR green, or making a branch merge-ready. Stops before merging.
---

# PR green

Get the PR ready to merge, continuing all work within the user's authorized scope. Use
the Python helper for mechanics; spend reasoning on fixes and truthful evidence.
Requires Python 3.10+, Git, and authenticated `gh`. Locate `scripts/pr-green` relative
to this SKILL.md; below, `PG` means its absolute path. Run from the target repository.

## Work loop

1. Read repository instructions and any `.agents/pr-green.md`. Inspect the branch,
   diff, PR template, and validation commands. Run `python3 "$PG" status` for a compact
   diagnosis. Commit only task-owned changes; preserve unrelated work.
2. Write a useful PR title and body to temporary files. Preserve existing template
   sections, ticket links, checklists, and human-authored content; update claims to
   match the final diff. Run `python3 "$PG" upsert --title-file TITLE --body-file BODY`.
   Existing PR metadata is edited only when different. For a new PR targeting a
   nondefault branch, add `--base BRANCH`. The helper syncs, pushes, creates/updates,
   and marks the PR ready. Omit title/body flags on later runs to preserve them.
3. Fix all actionable failures in one pass. Run `python3 "$PG" logs` for cached failed
   Actions logs and short excerpts; external checks have links in `status`. Reproduce
   failures, repair the cause, and run appropriate repository checks. Resolve base
   conflicts without discarding either side's intended changes; stage the resolved
   paths and finish the merge, then rerun `upsert`.
4. Assess every unresolved thread (including outdated ones). Push and verify the fix
   before `python3 "$PG" resolve THREAD_ID --expected-head SHA`. Resolve only an
   individually addressed thread. Outdated does not mean addressed. If discussion is
   needed, reply only when messaging is authorized; never dismiss or self-approve a
   review. Read full discussion when the compact excerpt is insufficient.
5. Run `python3 "$PG" wait --seconds 45`. It polls internally with backoff, prints only
   changes, and returns early for actionable failures. Keep the user informed between
   calls. For ACTION, fix and rerun `upsert`; for WAITING, wait again. Recheck after
   every push, metadata change, or review action. Finish only on `READY`, or after
   exhausting work that can proceed despite a precise external blocker.

| Exit | Meaning | Action |
|---|---|---|
| 0 | READY (status/wait), DONE (mutation) | Only READY proves the final gate passed. |
| 1 | ERROR | Repair auth/tool/network/input errors when possible. |
| 2 | ACTION | Fix the reported CI, branch, draft, or thread issue. |
| 3 | BLOCKED | Diagnose rules/approval/access; continue other useful work. |
| 4 | WAITING | CI, GitHub computation, or branch movement needs another observation. |

## Attestations and gates

Handle attestations autonomously: inspect the diff, gather proof, and update only
truthful claims. Never ask the user which boxes to check or for evidence solely to
clear a gate. If evidence, access, or required sign-off is unavailable, leave the
claim unchecked, document the precise blocker in the PR body, report it, and continue
other authorized work. Never mass-check boxes, fabricate evidence, remove a gate,
weaken a test, or change policy to manufacture green.

Tickets, review approvals, deployment approvals, secrets, and merge queues may need
an external actor. Diagnose the actual requirement; do not create unrelated tickets,
send messages, approve deployments, enqueue, enable auto-merge, or merge as an implied
part of this skill. Follow explicit session authorization for those actions.

## Efficiency and stopping

- Batch code and description changes. Reuse saved logs; don't dump full CI output.
- Rerun a demonstrated transient failure once per run/head with
  `python3 "$PG" rerun RUN_ID --expected-head SHA`. The helper persists a retry ledger.
  No automatic retries of arbitrary failed tests. A repeated failure needs diagnosis.
- Default sync merges the remote branch and actual PR base without rewriting history.
  If repository policy requires rebasing, follow that policy with an explicit lease
  and verified remote SHA; the helper never force-pushes. Do not reset/stash someone
  else's work, create worktrees, or spawn agents solely because this skill is running.
- For long CI, continue bounded waits while progress occurs. After 30 minutes without
  any status change, inspect stalled runs and report the specific external blocker.
  After three unsuccessful fixes of the same failure, reassess the root cause and
  scope; stop only if progress requires unavailable access, evidence, or authorization.
- Final response: PR URL, verified head/base, validation result, and remaining blocker
  if any. Say “ready to merge” only for the verified snapshot; never imply it was merged.

Read [references/operations.md](references/operations.md) only for CLI options,
unusual blockers, installation, or details of the readiness contract.
