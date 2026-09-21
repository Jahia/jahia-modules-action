# ai-pr-review

On-demand AI review of a pull request: when a human requests a review from the AI reviewer
account (`jahia-ai`), a headless [Claude Code](https://code.claude.com) agent — running from
inside the [cortex harness](https://github.com/Jahia/cortex), reaching the LiteLLM gateway
through the IT mTLS bastion — reviews the PR and submits **one review: APPROVE when it
finds no code issue** (a failing CI check is alerted in the notes, never blocking),
**COMMENT otherwise, with each finding attached as a native inline comment on the line in
question** (findings that fit no diff line land in the review body's General notes; if
GitHub rejects an anchor, the review is re-submitted body-only so it is never lost).
Approval strictly requires zero findings — enforced deterministically by the submit step,
not just by the prompt. It never requests changes and never touches code: blocking a PR,
and merging, stay human decisions.

Every review also carries the agent's **confidence call**: a **Human review** line in the
body (`not needed` / `recommended` / `required`, with a one-line reason) mirrored as a PR
label — `🤖 AI-only review OK` (green), `🤖 Human review recommended` (yellow) or
`🤖 Human review required` (red). The submit step applies it deterministically (creating
the label on first use and swapping out the previous recommendation), best-effort so a
labeling hiccup never loses a review; the clear label removes these labels too.

## One review per request — the eligibility rule

The trigger is the `review_requested` pull-request event, filtered to the AI reviewer
account. GitHub only emits that event when someone requests (or re-requests) the reviewer —
never when the PR is updated — so the wanted semantics hold by construction:

- Request a review from `jahia-ai` → exactly one review.
- Push more commits → nothing happens.
- Click "re-request review" on `jahia-ai` → exactly one more review (delivered as a delta
  against the previous one).

Two deterministic mechanisms make this idempotent:

- **`check-request` guard** (LLM-free, cheap runner): before a self-hosted runner is engaged,
  it re-reads the PR and only proceeds when the PR is open AND the reviewer is still in
  `requested_reviewers`. Workflow re-runs, duplicate event deliveries, or requests withdrawn
  in the meantime are skipped.
- **The review request is *fulfilled* by the review**: the agent submits with the `jahia-ai`
  account's token, so GitHub clears the pending request the moment the review lands. A
  crashed agent submits nothing, the request stays pending, and re-running the workflow (or
  re-requesting) retries.

As soon as the guard passes, a **status comment** is posted on the PR as the reviewer
account ("I received the review request and I'm on it", linking to the run). When the agent
job ends it is deleted (the review takes its place) or rewritten into a failure note
("request stays pending — re-request to retry"). Review mode posts no status comment.

**Clearing a review**: label the PR `💀 Clear jahia-ai review` (any label containing
"clear", "jahia-ai" and "review" works, regardless of order or casing) and the
[`ai-pr-review/clear`](clear/action.yml) action removes the reviewer's footprint — its
comments (status and inline) are deleted, its review bodies blanked and minimized, and any
pending review request for it is withdrawn; the label is then consumed, so it can be
re-applied later. Two GitHub limits to know: a submitted review cannot be deleted outright
(a minimized empty shell remains), and an already-submitted APPROVE keeps its effect on
branch protection — only a dismissal revokes it, and this action deliberately does not
dismiss. Blanking also removes the re-review marker: the next requested review starts fresh.

Every review body additionally starts with a hidden marker (`<!-- cortex-pr-review -->`):
it lets the agent detect its own previous review (re-review = delta), and lets the
verification step confirm this run delivered one.

## Actions

### `ai-pr-review/check-request`

| Input | Required | Default | Description |
|---|---|---|---|
| `github_token` | yes | — | Token used to read the pull request |
| `repository` | no | current repository | Repository of the PR (owner/repo) |
| `pr_number` | yes | — | Pull request number |
| `reviewer` | no | `jahia-ai` | GitHub username of the AI reviewer account |

| Output | Description |
|---|---|
| `eligible` | `"true"` when the PR is open and the reviewer is still requested |

### `ai-pr-review` (this action)

Runs the agent. Requires [`ai-agent-setup`](../ai-agent-setup) to have run first (CLI,
LiteLLM env, cortex checkout) and an established [`mtls-tunnel`](../mtls-tunnel) covering
the LiteLLM gateway. The pull request is fetched **before** the agent starts (see
[The pre-fetched context](#the-pre-fetched-context)), checkout included, so the agent opens
files rather than spending its budget gathering them.

| Input | Required | Default | Description |
|---|---|---|---|
| `pr_url` | yes | — | URL of the pull request to review |
| `github_token` | yes | — | Token of the AI reviewer account (submitting with it clears the review request) |
| `cortex_path` | yes | — | Absolute path of the cortex checkout (from `ai-agent-setup`) |
| `model` | no | `opus` | Claude Code `--model` value: an `opus`/`sonnet`/`haiku` alias the gateway maps, or a model name it serves verbatim (see [Which model runs](#which-model-runs)) |
| `marker` | no | `<!-- cortex-pr-review -->` | Marker the agent must put in every review body |
| `post_review` | no | `true` | `false` = review mode: store the would-be review in `logs_dir/reviews` instead of submitting |
| `job_timeout_minutes` | no | `30` | The calling job's `timeout-minutes`; the agent's own budget is this minus a 5-minute reserve (see [Timeouts](#timeouts)) |
| `prefetch_checkout` | no | `true` | Also check the PR head out for the agent; `false` reviews from the diff alone |
| `allowed_tools` | no | see `action.yml` | Claude Code `--allowedTools` value |
| `disallowed_tools` | no | see `action.yml` | Claude Code `--disallowedTools` value (a deny rule beats an allow rule) |

## The pre-fetched context

`src/prefetch-context.py` runs in the prep step, before the agent, and writes
`logs_dir/context/`: `README.md` (the index the prompt points at), `pr.md`, `pr.json`,
`reviews.md`, `review-comments.md`, `linked-issues.md`, `checks.md` and `diff.patch` — plus,
unless `prefetch_checkout` is `false`, a blobless checkout of the PR head under the cortex
checkout's git-ignored `sources/`. It takes seconds, and it replaces the ten-odd turns the
agent used to spend making the same `gh` calls.

Three things make this the prep step's job rather than the agent's:

- **The allowlist has holes the agent cannot see.** A refusal reads to a headless agent as
  "this tool is gone", and it goes looking for a way around — on one observed run a denied
  `gh api` cost 3½ minutes and the review still went out without the inline comments. This
  step runs with a plain shell and no allowlist, so `gh api …/pulls/N/comments` simply works:
  `review-comments.md` is the one context file the agent could never fetch for itself.
- **The checkout needs a directory change.** cortex denies `cd`, so the agent has no way into
  a clone it creates. The prep step makes it and hands over the path.
- **A missing piece must not become a hunt.** Every fetch is best-effort, and what failed is
  named under "Not available" in the index — so the agent reads the gap instead of chasing it.

The prompt's tool-surface section is rendered by `src/build-prompt.py` from the very
`allowed_tools`/`disallowed_tools` strings passed to the CLI, so the agent is told what it
may run and the two cannot drift apart. That matters because the agent works from inside
cortex, whose `CLAUDE.md` mandates routes the allowlist has to agree with: each read is
allowed under both spellings (`gh pr view` and `tools/gh-wrapper/bin/gh-wrapper pr view`),
and each write is denied under all of them (`git push`, `git -C <dir> push`, `gh pr comment`,
`gh-wrapper pr comment`) — a permission rule matches one command prefix, so a write left
unnamed in one spelling stays reachable through it.

| Output | Description |
|---|---|
| `logs_dir` | Directory holding the review run logs — upload it as an artifact |

## Which model runs

The `model` input is the Claude Code `--model` value, and it is the only thing that decides
which model answers. Leave it empty and there is no `--model` at all: the CLI falls back to its
own built-in default, which moves with `claude_code_version` — so an unpinned duty can change
model under you on a CLI upgrade. Each duty therefore pins one:

| Duty | Default | Why |
|---|---|---|
| [`ai-pr-review`](../ai-pr-review) | `opus` | Reading a diff for real defects is the reasoning-heaviest of the three |
| [`ai-tldr`](../ai-tldr) | `sonnet` | Summarizing a thread that has already been read |
| [`ai-incident-triage`](../ai-incident-triage) | `sonnet` | Reading logs and matching known failure signatures |

The `ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL` variables that
[`ai-agent-setup`](../ai-agent-setup) exports do **not** select a model — they only tell the CLI
which LiteLLM deployment each alias resolves to. Passing a deployment name here instead of an
alias bypasses them.

Two models normally appear in one run: the one named here, plus the small model Claude Code uses
for its own background work, which always comes from the haiku alias.

## Review-only guarantee

The agent runs with an explicit allow list AND deny list (`--allowedTools` /
`--disallowedTools`). The allow list grants read/search tools, local file writes (staging
the review body — the runner is ephemeral, so nothing leaves the machine), granular
read-only `git`/`gh` commands (each under both the bare and the `gh-wrapper` spelling, and
`git -C <dir> <read>` for the pre-fetched checkout). The deny list — and a deny rule beats an allow rule, including one the
cloned repository's own settings could carry — names every editing tool, every way a review
could reach the forge or rewrite history (`git push/commit/checkout/reset/remote`,
`gh pr create/comment/edit/ready/merge/close`, `gh issue *`, `gh api`, `gh release`,
`gh workflow`, `gh secret`), and the options of allowed commands that write (`--output`) or
execute (`--upload-pack`). The agent itself never posts anything: `gh pr review` is denied
too — the agent writes the review body to a file, and submitting that file is a
deterministic action step (running with the jahia-ai token) after the agent finishes.
`--permission-mode dontAsk` denies everything not explicitly allowed. The prompt additionally forbids requesting
changes (approval only with zero findings, re-enforced by the submit step) and instructs the
agent to treat PR content (title, description, code, comments) as data, never as
instructions — and to flag prompt-injection attempts as findings.

## Determinism & observability

- Trigger filtering, the eligibility guard, and prompt construction are plain code; the
  agent's only free-form output is the review body.
- The complete agent session is kept in `logs_dir`: `review.stream.jsonl` (the raw
  `stream-json` log — every tool call, model message and result), `review.transcript.log`
  (the same session rendered as a plain readable log — start there), `review.prompt.md`
  (the exact prompt), `review.result.json`, `review.stderr.log` (CLI errors; API/CLI debug
  detail with the `debug` input), `reviews/pr-<key>.review.json` (the structured review),
  and `collected/` (evidence the agent gathered from resources it used — test runs,
  containers, downloaded logs — which the prompt requires it to capture there). The workflow
  uploads it as the `ai-pr-review-logs` GitHub artifact and to the Jahia servers
  (`qa.jahia.com/artifacts-ci`, VPN required) via the [`upload-artifact`](../upload-artifact)
  action.
- The job log narrates the run **live**, like any build or test step: the CLI's stream-json
  goes through `src/stream-progress.py`, which writes the raw stream to
  `review.stream.jsonl` and prints one flushed line per event as it arrives —
  `elapsed · event · detail`, where the event is `init`, `think`, `tool`, `ok`/`err`,
  `denied` (the denied call, not the permission boilerplate), `retry` (gateway 429s and
  their backoff), `task`, `model`, or a `…` heartbeat when a single thought has run for more
  than a minute. Tens of thousands of `thinking_tokens` counter events are folded into that
  heartbeat rather than printed. A 30-minute run renders in ~200 lines. The job summary then
  tabulates outcome, models, turns, duration and cost.
- **Which model wrote the review is on the record.** The run is configured with one model,
  but a fallback or a downgrade under load substitutes another without the agent being told —
  so the model is read from the stream rather than from the configuration: a `model` line is
  printed the first time each thread answers and on every change after it (`main · SWITCHED
  from X to Y`), a subagent's model is tracked apart from the main thread's so a delegation
  does not read as a switch, and the summary row lists every model that actually answered.
  The prompt also requires the agent to state the model it is on before its first tool call,
  whenever it changes, and whenever it delegates — but that is the reported half; the stream
  is the measured one.
- **Every refused call is on the record.** `src/denied-calls.py` reads the stream after the
  run and writes `denied-calls.md` into the artifact, and the same table into the job
  summary: how many calls the permission layer refused, which, and why. It closes with the
  prefixes the agent reached for that the allowlist does not carry — which is the input for
  deciding what the next allowlist should hold. It is a read of the stream, not something
  the agent reports: an agent that has just been refused is the least reliable witness to
  what it was refused, and making it keep its own tally spends the budget the allowlist is
  already costing. Allowing one of the listed prefixes stays a deliberate call — the deny
  list is what keeps this agent review-only, and some refusals are the design working.
- A final verification step warns when no marker review newer than the run start exists
  (warn, not fail: the request stays pending, and a re-run or re-request is the retry).

## Timeouts

Two nested budgets, and only the inner one is safe to hit:

- `timeout_job` (default **30 minutes**) is the job's `timeout-minutes`. Reaching it makes
  GitHub **cancel the job mid-step**: the agent is killed without the run ever producing its
  trace, its transcript or its job-summary row, and the review request is left pending with
  no explanation.
- The **agent budget** is `job_timeout_minutes` minus a 5-minute reserve (so **25 minutes**
  by default), enforced by this action with `timeout(1)` around the CLI. Reaching it is an
  ordinary step failure we control: the partial `review.stream.jsonl` is still rendered into
  `review.transcript.log`, the artifact is still uploaded to both destinations, the PR status
  comment is still replaced with the failure note, and the job log carries an explicit
  `AI review timed out` error.

So a review that runs out of time is meant to fail on the agent budget, never on
`timeout_job`. When a repository's PRs legitimately need longer (large dependency bumps, a
big diff, a gateway that rate-limits), raise `timeout_job` on the caller — the workflow
forwards it as `job_timeout_minutes` and the agent budget follows.

The reserve is subtracted inside the action rather than in the workflow's `with:` block on
purpose: **GitHub Actions expressions have no arithmetic operators**, so `${{ inputs.x - 5 }}`
is not a value but a workflow syntax error, and a workflow that fails to compile takes every
job in the calling run down with it.

## How it runs

All the logic lives in the
[`reusable-ai-pr-review.yml`](../.github/workflows/reusable-ai-pr-review.yml) reusable
workflow (guard job + agent job). The
[`reusable-delivery-pr-chores.yml`](../.github/workflows/reusable-delivery-pr-chores.yml)
workflow only holds the trigger condition — `review_requested` event, requested reviewer is
`jahia-ai` — and calls it. A repository opting in must, in its caller workflow:

```yaml
on:
  pull_request:
    types: [opened, reopened, synchronize, closed, review_requested]

permissions:
  pull-requests: write
  contents: read
  id-token: write   # the mTLS tunnel mints a client certificate from the run's OIDC token

jobs:
  chores:
    uses: jahia/jahia-modules-action/.github/workflows/reusable-delivery-pr-chores.yml@v2
    secrets: inherit
```

and be allowlisted with IT's mTLS broker for `pull_request` events (the broker is
deny-by-default on both the tunneled hosts and the calling repository).

Requirements otherwise mirror [`ai-incident-triage`](../ai-incident-triage): a self-hosted
(typically ephemeral) Ubuntu runner providing `gh`, `python3`, `git`, `curl`, and the org
secrets/vars `AI_AGENT_GH_ISSUES_PRS_CHORES` (the `jahia-ai` account token, with
pull-request read/write on the repository), `AI_LITELLM_AUTH_TOKEN`, `AI_LITELLM_BASE_URL`,
`AI_LITELLM_ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL`, plus the mTLS bastion surface
(`INFRAJAHIA_MTLS_CA_URL`, `INFRAJAHIA_MTLS_BASTION`, `INFRAJAHIA_MTLS_STEP_ROOT`,
`INFRAJAHIA_MTLS_SERVER_CA`).

Tuning inputs on `reusable-ai-pr-review.yml` (all optional — `reusable-delivery-pr-chores.yml`
calls it with the defaults): `reviewer` (default `jahia-ai`), `post_review` (default `true`;
`false` = review mode), `model` (default `opus`), `instance_type`, `timeout_job`,
`cortex_ref`, `claude_code_version`, `tunnel_hosts`.
