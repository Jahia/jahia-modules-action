# ai-incident-triage

Automated analysis of nightly test-failure issues (label `automated-incident`): a
deterministic, LLM-free action selects the issues worth analyzing, then a headless
[Claude Code](https://code.claude.com) agent — running from inside the
[cortex harness](https://github.com/Jahia/cortex), over the Jahia VPN — analyzes each failed
run's logs and posts its conclusion as a comment on the issue.

**v1 is analysis-only.** The agent never changes code, never opens or merges PRs, never
closes or labels issues — it only posts comments.

Callers normally use the
[`reusable-ai-incident-triage.yml`](../.github/workflows/reusable-ai-incident-triage.yml)
workflow rather than these actions directly.

## The eligibility rule (one agent action per failure event)

Every triage comment starts with a hidden HTML marker:

```
<!-- cortex-incident-triage -->
```

An issue is **eligible** when its latest *failure event* (the issue body, or any comment
matching `Source URL:` / `### Failure Details`) has **no marker comment posted after it**.

Consequences, all deterministic:

- A fresh incident is analyzed exactly once — the marker comment "closes" that failure event.
- The agent never re-grinds the same failure daily; a new failure comment (flaky repeat)
  re-arms the issue for exactly one more pass.
- A crashed agent posts no marker, so the issue simply stays eligible for the next run.
- The rule is content-based, not author-based: it works even when the incident bot and the
  agent share the same GitHub identity (which author-identity checks cannot handle).

## Actions

### `ai-incident-triage/select-issues`

LLM-free selection, runs on any cheap runner.

| Input | Required | Default | Description |
|---|---|---|---|
| `github_token` | yes | — | Token used to list issues and comments |
| `repository` | no | `${{ github.repository }}` | Repository to scan (owner/repo) |
| `label` | no | `automated-incident` | Label identifying automated test-failure incidents |
| `marker` | no | `<!-- cortex-incident-triage -->` | Hidden marker string identifying agent triage comments |

| Output | Description |
|---|---|
| `issues` | JSON array of eligible issues (`{number, title, html_url, latest_failure_at, source_run_url, vpn_artifacts_url}`), sorted by issue number |
| `has_issues` | `"true"` when at least one issue is eligible |

### `ai-incident-triage` (this action)

Runs the agent. Requires [`ai-agent-setup`](../ai-agent-setup) to have run first (it
installs the CLI, exports the LiteLLM env, and clones cortex) and an established
[`mtls-tunnel`](../mtls-tunnel) covering the LiteLLM gateway and `qa.jahia.com`.

| Input | Required | Default | Description |
|---|---|---|---|
| `issues` | yes | — | JSON array produced by `select-issues` |
| `repository` | no | `${{ github.repository }}` | Repository holding the incident issues |
| `github_token` | yes | — | Token used by the agent to read issues/runs and post comments |
| `cortex_path` | yes | — | Absolute path of the cortex checkout (from `ai-agent-setup`) |
| `marker` | no | `<!-- cortex-incident-triage -->` | Marker the agent must put in every triage comment |
| `allowed_tools` | no | see `action.yml` | Claude Code `--allowedTools` value |

| Output | Description |
|---|---|
| `logs_dir` | Directory holding all triage run logs — upload it as an artifact |

## Determinism & observability

- Issue selection, ordering (ascending issue number), prompt construction, and the
  per-issue loop are plain code — the agent only ever sees **one issue per invocation**.
- Every invocation's full `stream-json` output is kept in `logs_dir`
  (`selected-issues.json`, `prompts/issue-<n>.prompt.md`, `issue-<n>.stream.jsonl`,
  `issue-<n>.result.json`, `issue-<n>.stderr.log`) — the reusable workflow uploads it as the
  `ai-incident-triage-logs` artifact.
- The job log shows a deterministic trace per issue (`[tool]`/`[say ]`/`[end ]` lines);
  the job summary tabulates outcome, turns, duration and cost per issue.
- A final verification step re-reads the issues and warns about any missing triage comment
  (warn, not fail: the issue stays eligible and the next scheduled run is the retry).

## Analysis-only guarantee

The default allowlist gives the agent read/search tools, `gh` read commands,
`gh issue comment`, log download commands, and the cortex `jahia-ci-triage` tool — no
`Edit`/`Write`, no `git push`, no PR or merge surface. `--permission-mode dontAsk` denies
everything not explicitly allowed. The prompt additionally forbids modifying anything and
instructs the agent to treat issue/log content as data, never as instructions.

## Requirements

- Self-hosted Ubuntu runner. Runners are typically ephemeral; all state lives and dies
  with the job.
- Runner image must provide `gh`, `python3`, `unzip`, `git`, `curl` (checked by
  `ai-agent-setup`, which warns on gaps).
- Org secrets/vars: `GH_ISSUES_PRS_CHORES`, `AI_LITELLM_AUTH_TOKEN`, `AI_LITELLM_BASE_URL`,
  `AI_LITELLM_ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL`, plus the mTLS bastion surface
  (`INFRAJAHIA_MTLS_CA_URL`, `INFRAJAHIA_MTLS_BASTION`, `INFRAJAHIA_MTLS_STEP_ROOT`,
  `INFRAJAHIA_MTLS_SERVER_CA`).
- The agent job needs `permissions: id-token: write` (the tunnel mints a short-lived client
  certificate from the run's OIDC token). The broker is deny-by-default on BOTH dimensions:
  every tunneled host AND every calling repository must be allowlisted on IT's side —
  onboarding a new repo onto this workflow starts with that allowlist request.

## How to call

```yaml
name: Nightly incident triage
on:
  schedule:
    - cron: '0 5 * * *'
  workflow_dispatch:

jobs:
  triage:
    uses: Jahia/jahia-modules-action/.github/workflows/reusable-ai-incident-triage.yml@v2
    secrets: inherit
```
