# AI Issue Agent — guard, lock and budget ledger

Mentioning the AI agent account (`jahia-ai` by default) in a fresh issue comment —
`@jahia-ai do something` — asks for an agent session on that issue; assigning the account
changes nothing. Once the guard admits a session it reacts 👍 on the triggering comment:
the sign that what the comment asks is being handled. It also clears the
`🧠 Human needed !` escalation label when the issue carries it — a fresh mention means a
human answered — and the session's own `escalate` puts it back when the issue still
needs a person. The guard also creates that label in the repository when it is missing,
because `gh-wrapper issue edit --add-label` refuses a missing label. This package holds the
deterministic (LLM-free) spine of that duty — the **check-request** guard that decides
whether a session is owed, and the **finalize** closer that settles the session afterwards —
plus the **run** action that executes the agent session itself: pre-fetched issue context,
a barebone prompt (`run/prompt.md`, the substance lives in cortex skills), the Claude Code
CLI under a strict tool allowlist whose issue writes run through the commands the cortex
`jahia-issue-agent` skill names, and a token-free sidecar appending progress to the
session's task comment. The roadmap lives in the AI Issue Agent PRD, in Jahia's internal
Cortex harness.

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
profile may cross — merge/ready/review/close, issue creation and the raw `gh` issue writes,
arbitrary forge writes (`gh api`, releases, workflows, secrets), force/mirror/delete pushes,
`git remote`, and `EnterWorktree`, which would mint a worktree outside `cortex-sources`. Which
profile *uses* the write verbs is governed by the skill: only the Software Developer ships
code.

An issue write runs through `gh-wrapper issue comment` and `gh-wrapper issue edit`, the
route the cortex `jahia-issue-agent` skill moves to, or through the issue-agent tool, which
stays allowed during that move. No rule binds these writes to the session's issue: the
token's reach bounds them, and the prompt holds the session to its issue. The guard writes
the overall-status comment with the agent account too, so it can be that account's last
comment: `--delete-last` is denied, and `--edit-last` relies on the skill to reach the task
comment alone.

A pull request opens as a **draft**, and merging stays human-gated. Raw `gh pr create` stays
denied. Cortex's `tools/jahia-pr` commits the changes of a worktree under a
Conventional-Commit title. The Cortex skill then runs three writes itself, from the root of
the Cortex checkout:

- `git -C sources/<name>@<slug> push -u origin <branch>`, never with force.
- `gh-wrapper pr create --draft`. The `PreToolUse` hooks of Cortex run in this session, as in
  any Cortex session, and one of them refuses a `gh-wrapper pr create` with no `--draft`.
- `gh-wrapper api --silent -X PATCH repos/<owner>/<repo>/issues/comments/<id> -F body=@<file>`.
  It edits the trail comment: the comment on a Cortex tracking issue that lists the pull
  requests of one piece of work.

The session reads a worktree with `git -C sources/<name>@<slug> diff`, `show` and `status`.
Each read has two allow rules: the bare command, and the command with arguments. A rule with a
`*` in the path and a trailing ` *` does not match the bare command. The path stays relative
and unquoted, because the deny list refuses a quote in a `git -C` command. A range with `..` is
refused too, so the session reads its change with `diff --merge-base origin/<base>`.

A `*` in the middle of a permission rule stands for any text, spaces included. The allow rules
of the push, of the three reads and of the PATCH therefore take the values that vary. The same
`*` would also take a subcommand, an option or a refspec, so the deny list closes each such `*`:

- `git -C * -* push *` denies an option before `push`, such as `-c`, which makes git run a
  program.
- `git -C * * diff`, `git -C * * show` and `git -C * * status`, each in its bare form and with
  ` *`, deny any word between the path and a read. The `*` of the path would otherwise take a
  whole command, such as `push diff <branch>` or `remote add diff <url>`.
- `git * --output*` denies the option that writes the output of a git command to a file at any
  path.
- `git -C * push * -*`, `git -C * push * +*` and `git -C * push *:**` deny an option, a forced
  refspec and a refspec with a colon after `push`, such as `--force` or `HEAD:main`.
- `gh-wrapper api * repos/* -* -*` denies a second option on the PATCH. `?`, `#` and `..` deny
  an endpoint that a query, a fragment or a parent segment moves.
- `..` is denied in a `git -C` command, where it moves the directory out of `sources/`.
- A quote, a backslash, `$` and a backtick are denied in a `git -C` command and in a
  `gh-wrapper api` command. No intended command holds them, and the shell turns them into an
  option that the rules above do not see, such as `'--force'` or `\-\-force`.

The method rules of `gh-wrapper api` (`-X POST`, `-X PUT`, `-X DELETE`, `--method`, `--input`,
`--field`, `--raw-field`) deny the usual spellings of another write. They are no complete
floor: a field with no `-X`, an attached `-XPOST`, a PATCH on another endpoint and a GraphQL
mutation meet no deny rule. The floor is that no allow rule of the session reaches them.

A rule never mixes a `*` with the trailing `:*` form. Claude Code then reads the whole rule as
a literal prefix, which matches only a literal `*`, so a rule that ends on a colon is written
`:**`. The `git -C * push:*` rules of earlier versions never matched for this reason. A rule
matches one backslash with four of them.

Iteration on an open pull request happens with the `git -C` push and with `gh-wrapper pr
edit`/`pr comment`; another person's branch is touched only when the triggering human asked
for it. Pushes authenticate as the agent account: the run action wires git to gh's
credential helper (`gh auth setup-git`) with the same `github_token` the session uses, the
chores token `AI_AGENT_GH_ISSUES_PRS_CHORES`.

Per-profile model and runner defaults are not wired: `model` and `instance_type` are
workflow inputs a consumer can already tune, and profile-based tuning is a rollout
(Phase 7) knob, not a dispatch-time decision — the profile is picked after the runner
exists.
