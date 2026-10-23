# AI Issue Agent — guard, lock and budget ledger

Assigning the AI agent account (`jahia-ai` by default) to an issue, or mentioning it in a
fresh issue comment, asks for an agent session on that issue. This package holds the
deterministic (LLM-free) spine of that duty: the **check-request** guard that decides
whether a session is owed, and the **finalize** closer that settles the session afterwards.
The agent session itself is not here yet — the agent job of
`reusable-ai-issue-agent.yml` is a stub until a later phase (the roadmap lives in the AI
Issue Agent PRD, in Jahia's internal Cortex harness).

## Requirements

- The `AI_AGENT_GH_ISSUES_PRS_CHORES` secret (the AI agent account's token), inherited by
  the reusable workflow — the same secret the AI PR review and AI TL;DR duties already use.
- Events: consumers already forward every `issues` and `issue_comment` event to
  `reusable-delivery-issue-chores.yml` (the caller workflow is synced org-wide); the
  dispatch job there filters cheaply, and this guard re-checks authoritatively.

## The overall-status comment

All state lives on the issue itself, in one comment the guard creates on first touch —
wherever the thread stands at that moment. The comment has three parts: an identity marker
(never changes — it is how every run finds the comment again), a machine-readable state
block (one line of JSON inside an HTML comment, rewritten on every state change), and a
short human-readable summary regenerated from the state on every write.

```markdown
<!-- cortex-issue-agent-status -->
<!-- cortex-issue-agent-state
{"version":1,"budgetSeconds":7200,"ledgerSeconds":95,"firstRunAt":"2026-10-23T14:00:00.000Z","budgetExhaustedNotedAt":null,"lock":{"runId":42,"runUrl":"https://github.com/Jahia/sandbox/actions/runs/42","lockedAt":"2026-10-23T14:00:00.000Z"},"sessions":[{"runId":42,"runUrl":"https://github.com/Jahia/sandbox/actions/runs/42","trigger":"assigned","startedAt":"2026-10-23T14:00:00.000Z","endedAt":null,"seconds":null,"outcome":null}]}
-->

🤖 **AI Issue Agent — overall status**

Session #1 in progress — [run](https://github.com/Jahia/sandbox/actions/runs/42)
Budget used: 1m 35s of 2h 00m
```

Schema (`version: 1`):

| Field | Meaning |
| --- | --- |
| `budgetSeconds` | The issue's total agent-runtime budget. Fixed on first touch; a later change of the action default never resurrects an exhausted issue. |
| `ledgerSeconds` | Cumulative runtime across all sessions. Only ever grows. |
| `firstRunAt` | ISO-8601 timestamp of the first session on this issue. |
| `budgetExhaustedNotedAt` | Set when the one-time exhaustion note was written; later refusals stay silent. |
| `lock` | `null` when free, else `{runId, runUrl, lockedAt}` of the session in flight. |
| `sessions` | One entry per session: `{runId, runUrl, trigger, startedAt, endedAt, seconds, outcome}`. |

## Lock semantics

The **mutual exclusion is the workflow's concurrency group on the guard job** (one guard at
a time per issue); the lock in the comment is that mutex's durable record between runs. A
trigger arriving while the lock is held is **silently prevented** — no agent job, no
comment, no reaction (by design: duplicates must leave no trace). A lock whose `lockedAt`
is older than the agent job's `timeout_job` plus a 10-minute margin belonged to a run that
could not finalize (hard-cancelled job, dead runner): the next guard reclaims it with a
log warning. Finalize releases only its own lock, never a foreign one.

## Ledger semantics

A session's `seconds` run from the agent job's first step (which stamps the epoch) to the
finalize step — runner queue time never bills the budget, environment setup does. This is
the provisional definition; refine deliberately when the agent job stops being a stub.
When `ledgerSeconds >= budgetSeconds`, the guard refuses every further session, notes it
once in the visible summary, and stays silent from then on. There is no reset mechanism:
raising the budget is a deliberate config change, not a runtime feature.
