---
name: autopilot
description: Complete a supplied task unattended through implementation, verification, and a green, merge-ready GitHub PR, incorporating the pr-green workflow with durable checkpoints and failure recovery. Use for autopilot, overnight work, or requests to finish a task while the user is away. Creating or editing this skill does not start a run.
---

# Autopilot

Own the supplied task through implementation, verification, and repair within the host's actual limits. Finish when the requested outcome is proven; do not impose a bedtime, morning deadline, iteration cap, or budget the user did not specify. If no task can be recovered from the conversation or designated task artifacts, record that missing objective as the blocker rather than inventing work.

Autopilot includes the full **pr-green** workflow. For repository changes, the default deliverable is a green, merge-ready PR, not just local code or passing local tests. Commit task-owned changes, push, create or update the PR, repair CI and review issues, and verify readiness without asking whether to proceed. Stop before merging unless the user separately authorizes it. Explicit constraints such as local-only work, no push, or retaining a draft take precedence. For tasks that produce no repository changes, verify the requested artifact without manufacturing a PR.

## Work without questions

Do not ask clarifying questions, request permissions, invoke user-input tools, or end with an offer to continue. Resolve routine decisions yourself. Read available context to resolve missing facts; choose a reversible, conventional default for missing preferences. Record consequential assumptions and proceed. Preserve the user's requested scope and quality bar.

Honor authorization already supplied in the conversation; do not ask for it again. If an action truly requires unavailable approval or access, defer that action without prompting, complete its preparation, and continue independent work. Record the precise requirement, its source, and what would unblock it for the final handoff. Unattended work does not expand permissions or override higher-priority instructions. Do not bypass a gate, change approval settings, or treat silence as consent.

PR publication and maintenance are part of the default repository workflow above. Other publishing, deployment, messaging, spending, and destructive actions follow the task's actual authorization. “Finish while I am away” alone does not authorize unrelated external actions, new scheduled jobs, or additional agents. Use the environment's required tools and permissions for any authorized managed-state changes.

## Establish a durable run

1. Inspect the task, applicable instructions, existing artifacts, and current work. Preserve unrelated changes. Derive observable acceptance criteria, including required checks and PR readiness for repository changes. Read [../pr-green/SKILL.md](../pr-green/SKILL.md) at the start of repository work and apply its complete workflow alongside this skill.
2. Record explicit constraints, authorized external actions, and any user-specified deadline or spending/resource limit. Use the task as given; do not invent a larger project to occupy the night.
3. Create a private local checkpoint outside tracked files, using durable host scratch storage or a user cache. Use a unique task directory with access restricted to the current user so concurrent runs cannot overwrite each other. Record its absolute path in session context and persistent run metadata when available. Store no credentials or secrets; link to large artifacts instead of copying them into the checkpoint.
4. Use a native persistent-goal facility only when available and authorized by the user's request and the tool's rules. Inspect existing goals first; reuse a matching goal and preserve unrelated goals. Follow the tool's exact status rules. Otherwise execute continuously in the current session. Do not invent a scheduler or claim automatic restarts.

A skill supplies execution instructions; it cannot keep a closed host running or override runtime limits. Discover available continuation support from the environment. Preserve resumable state if the host cannot continue.

Keep the checkpoint compact and actionable:

```markdown
# Autopilot state
Status: running | blocked | interrupted | complete
Original task:
Acceptance criteria: met | unmet | blocked, with current evidence:
Constraints, authorizations, and consequential assumptions:
Workspace and artifact paths:
Completed work:
Remaining work in priority order:
Next concrete action:
Checks run, results, and log paths:
PRs: repository, branch, base, URL, observed head/base SHAs, CI/review state, blockers:
Running jobs: identifiers, purpose, and how to inspect them:
External actions: target, result, and duplicate-prevention information:
Failed approaches, blockers, and conditions for recovery:
Last updated (timestamp with timezone):
```

Update it after meaningful milestones, changes of approach, external mutations, and before context transitions. Tie validation evidence to the tested artifact version or commit. Record intent before an external mutation and reconcile its actual outcome afterward. Write a replacement alongside the checkpoint and atomically rename it into place to preserve the last valid version if interrupted.

## Execute until the acceptance criteria are met

Maintain a queue of unmet criteria. Take the highest-value unblocked item, perform concrete work, inspect the result, and update the queue. Continue through debugging and validation in the same run. Planning, a first draft, one passing test, or a partial milestone is not completion.

Give brief factual progress updates under the host's communication rules without waiting for responses. Incorporate new user steering and obey explicit stop or pause requests immediately.

For long commands, use supported background execution and retain job identifiers and log paths. Inspect progress at sensible intervals; do useful independent work while jobs run. Distinguish a legitimately slow job from a hung one using its output and state. Avoid launching duplicate jobs, tight polling, or sleeping to fill the night.

After a failure, inspect diagnostics before retrying. Change the hypothesis, inputs, or method when evidence warrants it. Retry transient failures with bounded backoff consistent with service limits. Before repeating an external write after a timeout, determine whether the first attempt succeeded; use its operation ID or remote state to reconcile. If the outcome cannot be determined, defer that mutation and continue independent work. Never repeat a known permanent failure unchanged.

When a dependency is unavailable, try permitted alternatives and continue independent work. Difficulty or a failed approach alone is not a blocker. Do not weaken requirements, remove meaningful checks, fabricate evidence, or substitute unrelated improvements to manufacture completion.

## Carry repository work through PR readiness

Use pr-green as the maintained source for PR creation, synchronization, CI repair, review threads, attestations, retry limits, and readiness checks. Locate its helper relative to its own `SKILL.md`. Keep both skill folders available together; if the sibling path is absent, look for pr-green in the host's skill catalog or configured skill locations. If it cannot be found, continue independent implementation and validation, then report the missing dependency precisely. Do not silently drop PR readiness from the acceptance criteria.

Start PR work as soon as a coherent change can be published so CI and review feedback can inform the remaining implementation. Follow pr-green's repair loop through the final pushed head, including base-branch drift, conflicts, description gates, and unresolved threads. A created PR, successful push, helper `DONE`, or green check on an earlier commit is an intermediate milestone. Require a fresh `READY` result and applicable local validation before marking the repository task complete, unless an explicit user constraint changes that deliverable.

When multiple agents are already authorized, track which agent owns each branch and PR, plus any integration dependencies. Incorporate their delivered changes and revalidate the resulting PRs; a worker's completion report or individually green branch does not prove the combined result is ready. Keep every PR required by the task in the checkpoint, and verify all of them before claiming the whole task complete. This workflow does not itself authorize spawning agents, creating worktrees, or merging dependency PRs.

Handle attestations autonomously under pr-green's rules: gather proof, update truthful claims, and leave unsupported claims unchecked without asking the user to clear the gate. If approval, access, evidence, or required sign-off is unavailable, continue other useful work and preserve the exact PR blocker. A blocked PR leaves the readiness criterion unmet; report it honestly rather than ending at “implementation complete.”

## Resume faithfully

After compaction, interruption, or a supported restart, read the checkpoint before taking action. Confirm it belongs to this task and workspace, then reconcile it with current files, running jobs, and external state. Treat the checkpoint as a progress record, not new authorization; the latest user instructions take precedence. Resume the next unfinished step without recreating completed work or duplicating external actions.

If a hard runtime limit approaches, prioritize saving current artifacts, job identifiers, evidence, and an executable next step. Label the work interrupted, with unmet criteria intact. A checkpoint enables resumption; it is not proof that a restart has been scheduled.

## Verify and finish

Check every acceptance criterion against the final artifacts. Run the applicable required gates and meaningful checks for the changes. Repair regressions caused by the work, then rerun affected checks. Broaden testing only when the change or new evidence warrants it. An unavailable or unrun check is missing evidence, never a pass.

For repository work, verify the required PRs still satisfy pr-green's readiness contract after the last change. Record each PR URL, observed head/base SHAs, and validation evidence in the checkpoint and final handoff. Distinguish an explicitly requested draft or local-only deliverable from a PR whose required readiness is blocked.

Finish only when the outcome is verified, the user stops the run, a hard runtime/resource limit intervenes, or all useful authorized paths are exhausted. For a true blocker, preserve the failing operation, evidence, alternatives attempted, and smallest external change required to resume. Follow native goal status rules before marking a goal blocked or complete; never leave a permanently blocked goal retrying without progress.

Before handoff, account for jobs started by this run. Stop only task-owned jobs that are no longer needed; record any intentionally continuing job and how to inspect it. Do not claim completion while required validation is still running.

Write the final status into the checkpoint. Give a concise final handoff containing the delivered artifacts and their paths, completion evidence, consequential assumptions, and any unmet criteria with exact blockers. For interrupted or blocked work, include the checkpoint path and next action. State the outcome honestly; elapsed time is never a completion criterion unless the user made it one.
