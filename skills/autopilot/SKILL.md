---
name: autopilot
description: Complete a supplied task during a long unattended run, making decisions without questions, checkpointing progress, recovering from failures, and verifying completion. Use when the user asks for autopilot, overnight work, persistent autonomous work until a goal is achieved, or to finish a task while they are away. Creating or editing this skill does not start an overnight run.
---

# Autopilot

The human supplies the task and leaves. Own the work through implementation, verification, and repair. Continue for as many hours as needed within the host's actual limits. Finish when the requested outcome is proven; do not impose a bedtime, morning deadline, iteration cap, or budget the user did not specify.

## Work without questions

Do not ask clarifying questions, request permissions, invoke user-input tools, or end with an offer to continue. Resolve routine decisions yourself. Read available context to resolve missing facts; choose a reversible, conventional default for missing preferences. Record consequential assumptions and proceed. Preserve the user's requested scope and quality bar.

Honor authorization already supplied in the conversation; do not ask for it again. If an action truly requires unavailable approval or access, defer that action without prompting, complete its preparation, and continue independent work. Record the precise requirement, its source, and what would unblock it for the final handoff. Unattended work does not expand permissions or override higher-priority instructions. Do not bypass a gate, change approval settings, or treat silence as consent.

## Establish a durable run

1. Inspect the task, applicable instructions, existing artifacts, and current work. Preserve unrelated changes. Derive observable acceptance criteria, including required checks, from the requested outcome.
2. Record explicit constraints, authorized external actions, and any user-specified deadline or spending/resource limit. Use the task as given; do not invent a larger project to occupy the night.
3. Create a private local checkpoint outside tracked files, using the host's approved scratch location or a user cache. Use a unique task directory so concurrent runs cannot overwrite each other. Record its absolute path in session context and persistent run metadata when available. Store no credentials or secrets.
4. Use a native persistent-goal facility only when available and authorized by the user's request and the tool's rules. Inspect existing goals first; reuse a matching goal and preserve unrelated goals. Follow the tool's exact status rules. Otherwise execute continuously in the current session. Do not invent a scheduler or claim automatic restarts.

A skill supplies execution instructions; it cannot keep a closed host running or override runtime limits. Discover available continuation support from the environment. Preserve resumable state if the host cannot continue.

Keep the checkpoint compact and actionable:

```markdown
# Autopilot state
Status: running | blocked | interrupted | complete
Original task:
Acceptance criteria and current evidence:
Constraints, authorizations, and consequential assumptions:
Workspace and artifact paths:
Completed work:
Remaining work in priority order:
Next concrete action:
Checks run, results, and log paths:
Running jobs: identifiers, purpose, and how to inspect them:
External actions: target, result, and duplicate-prevention information:
Failed approaches, blockers, and conditions for recovery:
Last updated:
```

Update it after meaningful milestones, changes of approach, external mutations, and before context transitions. Record intent before an external mutation and reconcile its actual outcome afterward. Preserve the last valid checkpoint while writing its replacement.

## Execute until the acceptance criteria are met

Maintain a queue of unmet criteria. Take the highest-value unblocked item, perform concrete work, inspect the result, and update the queue. Continue through debugging and validation in the same run. Planning, a first draft, one passing test, or a partial milestone is not completion.

Give brief factual progress updates under the host's communication rules without waiting for responses. Incorporate new user steering and obey explicit stop or pause requests immediately.

For long commands, use supported background execution and retain job identifiers and log paths. Inspect progress at sensible intervals; do useful independent work while jobs run. Distinguish a legitimately slow job from a hung one using its output and state. Avoid launching duplicate jobs, tight polling, or sleeping to fill the night.

After a failure, inspect diagnostics before retrying. Change the hypothesis, inputs, or method when evidence warrants it. Retry transient failures with bounded backoff consistent with service limits. Before repeating an external write after a timeout, determine whether the first attempt succeeded. Never repeat a known permanent failure unchanged.

When a dependency is unavailable, try permitted alternatives and continue independent work. Difficulty or a failed approach alone is not a blocker. Do not weaken requirements, remove meaningful checks, fabricate evidence, or substitute unrelated improvements to manufacture completion.

## Resume faithfully

After compaction, interruption, or a supported restart, read the checkpoint before taking action. Reconcile it with current files, running jobs, and external state. Resume the next unfinished step without recreating completed work or duplicating external actions. Preserve the original task and all subsequent user corrections.

If a hard runtime limit approaches, prioritize saving current artifacts, job identifiers, evidence, and an executable next step. Label the work interrupted, with unmet criteria intact. A checkpoint enables resumption; it is not proof that a restart has been scheduled.

## Verify and finish

Check every acceptance criterion against the final artifacts. Run the applicable required gates and meaningful checks for the changes. Repair regressions caused by the work, then rerun affected checks. Broaden testing only when the change or new evidence warrants it. An unavailable or unrun check is missing evidence, never a pass.

Handle PR attestations autonomously: inspect the diff, gather available proof, and update only truthful claims. Leave unsupported claims unchecked, record the precise missing evidence or sign-off, and continue other authorized work.

Finish only when the outcome is verified, the user stops the run, a hard runtime/resource limit intervenes, or all useful authorized paths are exhausted. For a true blocker, preserve the failing operation, evidence, alternatives attempted, and smallest external change required to resume. Follow native goal status rules before marking a goal blocked or complete; never leave a permanently blocked goal retrying without progress.

Write the final status into the checkpoint. Give a concise final handoff containing the delivered artifacts and their paths, completion evidence, consequential assumptions, and any unmet criteria with exact blockers. For interrupted or blocked work, include the checkpoint path and next action. State the outcome honestly; elapsed time is never a completion criterion unless the user made it one.
