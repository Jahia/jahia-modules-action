# AI Issue Agent — guard, lock and budget ledger

Mentioning the AI agent account (`jahia-ai` by default) in a fresh issue comment —
`@jahia-ai do something` — asks for an agent session on that issue; assigning the account
changes nothing. Once the guard admits a session it reacts 👍 on the triggering comment:
the sign that what the comment asks is being handled. It also clears the
`🧠 Human needed !` escalation label when the issue carries it — a fresh mention means a
human answered — and the session's own `escalate` puts it back when the issue still
needs a person. This package holds the
deterministic (LLM-free) spine of that duty — the **check-request** guard that decides
whether a session is owed, and the **finalize** closer that settles the session afterwards —
plus the **run** action that executes the agent session itself: pre-fetched issue context,
a barebone prompt (`run/prompt.md`, the substance lives in cortex skills), the Claude Code
CLI under a strict tool allowlist whose one issue-write route is the cortex
`jahia-issue-agent` tool, and a token-free sidecar appending progress to the session's task
comment. The roadmap lives in the AI Issue Agent PRD, in Jahia's internal Cortex harness.

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
{"version":1,"budgetSeconds":7200,"ledgerSeconds":95,"firstRunAt":"2026-10-23T14:00:00.000Z","budgetExhaustedNotedAt":null,"lock":{"runId":42,"runUrl":"https://github.com/Jahia/sandbox/actions/runs/42","lockedAt":"2026-10-23T14:00:00.000Z"},"sessions":[{"runId":42,"runUrl":"https://github.com/Jahia/sandbox/actions/runs/42","trigger":"mentioned","startedAt":"2026-10-23T14:00:00.000Z","endedAt":null,"seconds":null,"outcome":null}]}
-->

🤖 **AI Issue Agent — overall status**

Session #1 in progress — [run](https://github.com/Jahia/sandbox/actions/runs/42)

| Session | Trigger | Started (UTC) | Duration | Outcome |
|---|---|---|---|---|
| [#1](https://github.com/Jahia/sandbox/actions/runs/42) | mentioned | 2026-10-23 14:00 | — | in progress |

**Budget used**: 1m 35s of 2h 00m (cumulative, across all sessions)

_This comment tracks all agent activity on this issue; the agent runtime keeps it up to date. The 2h 00m budget is set in the action configuration and can be changed._
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

## Board hygiene

The **project-hygiene** action runs at the start of every agent session: it attaches the
issue to the delivery board (an organization ProjectsV2, `project_url`), sets `Priority`
to its configured value every time, sets `Status` to what the session is about to do, and
gives `Squad` a default value only when no squad owns the issue yet — an assigned squad is
never overwritten. It is idempotent, and it fails loud with the board's actual fields and
options when the board does not match, so a renamed option is a readable annotation rather
than a silent no-op. The token it needs carries organization project scope — the chores
token the `add-to-project` jobs already use, not the agent account's issue token.

## Steering and STOP

A fresh comment mentioning the agent while a session runs is a **steering instruction**: the
running session polls for such comments between steps and once more before closing, reacts 👍
on each, reads the **entire comment** and does what it asks — redirect the work, take in new
input, or stop. There is no reserved keyword or comment format: a stop request in any phrasing
ends the session cleanly, with the closing task comment stating what was done and what
remains, and the logs artifact holding what the session collected. The ledger bills a stopped
session like any other.

A mid-run mention also reaches the guard, which finds the lock held and silently prevents a
second session — so the comment steers the running session and never starts, nor later
retriggers, another one. A session that never polls is bounded by its own budget and the job
timeout; those are the backstops, not a runner-side kill.

## Profiles and the write path

The session works as one of six SDLC profiles — Product Owner, Engineering Manager, Software
Developer, DevOps, QA, Security Engineer — picked by the model from the triggering comment
and the issue, and named in its opening task comment. The routing table and each profile's
skills live in the cortex `jahia-issue-agent` skill (`references/profiles.md`); the run
action only states the floor.

The permission surface is one list for all profiles, because the profile is only known once
the session runs. The runner is ephemeral, so local operations (file writes, read-only plain
git) are allowed generously; the `disallowed_tools` default is the floor no
profile may cross — merge/ready/review/close, issue writes outside the issue-agent tool,
arbitrary forge writes (`gh api`, releases, workflows, secrets), force/mirror/delete pushes,
`git remote`, and `EnterWorktree`, which would mint a worktree outside `cortex-sources`.
A permission rule matches a command prefix only, so a `git -C <dir>` spelling can never be
allowed, and no git write is allowed in any spelling: commits and pushes run through
`tools/jahia-pr`. Which profile *uses* the write verbs is governed by the skill: only the
Software Developer ships code.

A pull request opens only through cortex's `tools/jahia-pr` — allowed as a tool while raw
`gh pr create` stays denied in both spellings — which commits, runs `pr-lint`, pushes and
opens a **draft**, so draft-only is enforced by construction and merging stays human-gated.
Iteration on an open pull request happens with `jahia-pr push`, which commits the worktree's
changes under a Conventional-Commit title and pushes without force, and with `gh-wrapper pr
edit`/`pr comment`; another person's branch is touched only when the triggering human asked
for it. Pushes authenticate as the agent account: the run action wires git to gh's
credential helper (`gh auth setup-git`) with the same `github_token` the session uses, the
chores token `AI_AGENT_GH_ISSUES_PRS_CHORES`.

Per-profile model and runner defaults are not wired: `model` and `instance_type` are
workflow inputs a consumer can already tune, and profile-based tuning is a rollout
(Phase 7) knob, not a dispatch-time decision — the profile is picked after the runner
exists.
