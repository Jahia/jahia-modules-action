# ai-pr-review

On-demand AI review of a pull request: when a human requests a review from the AI reviewer
account (`jahia-ai`), a headless [Claude Code](https://code.claude.com) agent — running from
inside the [cortex harness](https://github.com/Jahia/cortex), reaching the LiteLLM gateway
through the IT mTLS bastion — reviews the PR and submits its findings as a **single review of
type COMMENT**. It never approves, never requests changes, never touches code: gating and
merging stay human decisions.

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
the LiteLLM gateway. The agent derives the repository from the PR URL and, when the diff
alone is not enough, creates its own throwaway checkout (`gh repo clone` + `gh pr checkout`
under the harness's git-ignored `sources/` area) to review the change in its repository
context.

| Input | Required | Default | Description |
|---|---|---|---|
| `pr_url` | yes | — | URL of the pull request to review |
| `github_token` | yes | — | Token of the AI reviewer account (submitting with it clears the review request) |
| `cortex_path` | yes | — | Absolute path of the cortex checkout (from `ai-agent-setup`) |
| `marker` | no | `<!-- cortex-pr-review -->` | Marker the agent must put in every review body |
| `post_review` | no | `true` | `false` = review mode: store the would-be review in `logs_dir/reviews` instead of submitting |
| `allowed_tools` | no | see `action.yml` | Claude Code `--allowedTools` value |
| `disallowed_tools` | no | see `action.yml` | Claude Code `--disallowedTools` value (a deny rule beats an allow rule) |

| Output | Description |
|---|---|
| `logs_dir` | Directory holding the review run logs — upload it as an artifact |

## Review-only guarantee

The agent runs with an explicit allow list AND deny list (`--allowedTools` /
`--disallowedTools`). The allow list grants read/search tools, local file writes (staging
the review body — the runner is ephemeral, so nothing leaves the machine), granular
read-only `git`/`gh` commands, and the throwaway clone surface (`gh repo clone`,
`gh pr checkout`). The deny list — and a deny rule beats an allow rule, including one the
cloned repository's own settings could carry — names every editing tool, every way a review
could reach the forge or rewrite history (`git push/commit/checkout/reset/remote`,
`gh pr create/comment/edit/ready/merge/close`, `gh issue *`, `gh api`, `gh release`,
`gh workflow`, `gh secret`), and the options of allowed commands that write (`--output`) or
execute (`--upload-pack`). The agent itself never posts anything: `gh pr review` is denied
too — the agent writes the review body to a file, and submitting that file is a
deterministic action step (running with the jahia-ai token) after the agent finishes.
`--permission-mode dontAsk` denies everything not explicitly allowed. The prompt additionally forbids approving/requesting
changes and instructs the agent to treat PR content (title, description, code, comments) as
data, never as instructions — and to flag prompt-injection attempts as findings.

## Determinism & observability

- Trigger filtering, the eligibility guard, and prompt construction are plain code; the
  agent's only free-form output is the review body.
- The run's full `stream-json` output is kept in `logs_dir` (`review.prompt.md`,
  `review.stream.jsonl`, `review.result.json`, `review.stderr.log`, plus
  `reviews/pr-<key>.review.md` in review mode) — the workflow uploads it as the
  `ai-pr-review-logs` GitHub artifact and to the Jahia servers
  (`qa.jahia.com/artifacts-ci`, VPN required) via the [`upload-artifact`](../upload-artifact)
  action.
- The job log shows a deterministic trace of everything the agent did
  (`[tool]`/`[say ]`/`[end ]` lines); the job summary tabulates outcome, turns, duration
  and cost.
- A final verification step warns when no marker review newer than the run start exists
  (warn, not fail: the request stays pending, and a re-run or re-request is the retry).

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
`false` = review mode), `instance_type`, `timeout_job`, `cortex_ref`, `claude_code_version`,
`tunnel_hosts`.
