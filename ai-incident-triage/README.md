# ai-incident-triage

A headless [Claude Code](https://code.claude.com) agent — running from inside the
[cortex harness](https://github.com/Jahia/cortex), reaching internal services over the IT
mTLS bastion — that analyzes Jahia integration-test runs with cortex's `analyze-jahia-ci`
skill and `jahia-ci-triage` tool. The same action works in two modes, chosen by its inputs:

- **Issues mode** (`issues` set): automated analysis of nightly test-failure issues (label
  `automated-incident`). A deterministic, LLM-free action selects the issues worth analyzing,
  then the agent fetches each failed run's logs and posts its conclusion as a comment on the
  issue. This is the centralized nightly run described in most of this document.
- **Run mode** (`artifacts_path` set): analysis of the integration-tests run that **just
  finished in the same job**, from its artifacts on disk — on every outcome. On a failed run
  it answers *why the tests failed*; on a green run it scans the Jahia logs for anything
  unexpected (a startup or provisioning `ERROR`, a failed provisioning op, a stale module
  version, an OOM). The report is written to the **job summary**, readable from the run page.
  Nothing is posted anywhere. See [Run mode](#run-mode-analyze-the-run-that-just-finished).

**v1 is analysis-only.** The agent never changes code, never opens or merges PRs, never
closes or labels issues — in issues mode it only posts comments, in run mode it only writes
the job summary.

The whole organization is triaged by ONE workflow running in this repository —
[`ai-incident-triage.yml`](../.github/workflows/ai-incident-triage.yml) — which searches all
repositories in scope for `automated-incident` issues and analyzes every eligible one in a
single run. Individual repositories do not call anything: opting a repo in is a matter of the
search scope and IT's mTLS allowlist. Processing all incidents together also lets the agent
spot a shared root cause impacting several repositories at once (each per-issue prompt embeds
a snapshot of the full selection).

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
| `search_scope` | no | `org:Jahia` | Issue-search scope qualifier (e.g. `org:Jahia`, `repo:Jahia/sandbox`) |
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
| `issues` | issues mode | `''` | JSON array produced by `select-issues`; setting it selects issues mode |
| `artifacts_path` | run mode | `''` | Folder exported by the integration-tests action (holds `results/`); setting it selects run mode |
| `module_id` | no | `''` | Run mode: id of the tested module, named in the report |
| `tests_outcome` | no | `''` | Run mode: outcome of the tests step as GitHub saw it (`steps.<id>.outcome`) |
| `github_token` | yes | — | Token used by the agent to read issues/runs and, in issues mode, post comments |
| `cortex_path` | yes | — | Absolute path of the cortex checkout (from `ai-agent-setup`) |
| `marker` | no | `<!-- cortex-incident-triage -->` | Issues mode: marker the agent must put in every triage comment |
| `post_comments` | no | `true` | Issues mode: post the comments (`false` = review mode) |
| `allowed_tools` | no | see `action.yml` | Claude Code `--allowedTools` value |

| Output | Description |
|---|---|
| `logs_dir` | Directory holding all agent run logs — upload it as an artifact |
| `report_file` | Run mode: path of the markdown report the agent wrote (also appended to the job summary) |

## Run mode: analyze the run that just finished

The [`reusable-integration-tests.yml`](../.github/workflows/reusable-integration-tests.yml)
workflow calls this action right after the `integration-tests` step, before the Test Report,
when the caller sets **`ai_analysis_enabled: true`** (off by default). It runs on **every
outcome**: after a failure the report says why the tests failed; after a success it says
whether the Jahia logs hold anything unexpected, or confirms they are clean.

Everything the agent needs is already on the runner — the `tests/artifacts` folder the
integration-tests action exported (Cypress results, `jahia*.log`, every container log and the
timestamped `all-containers.log`) and the module checkout for the provisioning cross-check — so
the agent fetches nothing and has no write surface at all: `gh issue comment` and `gh run
rerun` are explicitly disallowed in this mode, and the only file it writes is the report.

The report (`analysis/run-analysis.md` in `logs_dir`) is appended to the **job summary**, so
it is read from the run page in the GitHub UI, next to the Test Report. The full agent trace is
uploaded as the `<artifact_prefix>-<run_number>-ai-analysis` artifact. The three AI steps are
`continue-on-error`: a gateway outage or an agent crash never turns a green test run red.

Opting a module in:

```yaml
jobs:
  integration-tests:
    uses: Jahia/jahia-modules-action/.github/workflows/reusable-integration-tests.yml@v2
    secrets: inherit
    permissions:
      id-token: write        # the mTLS tunnel mints its client certificate from the run's OIDC token
      contents: read
      checks: write          # the Test Report step
      pull-requests: write
    with:
      ai_analysis_enabled: true
      # ...the usual inputs
```

The calling repository must be allowlisted with the mTLS broker (deny-by-default, on IT's
side), and the org secrets/vars listed under [Requirements](#requirements) must be visible
to it. `ai_cortex_ref`, `ai_claude_code_version` and `ai_tunnel_hosts` are exposed for
development iteration.

## Determinism & observability

- Issue selection, deterministic ordering (by repository, then issue number), and prompt
  construction are plain code. The agent runs **once over the whole selection** — deliberate,
  so it can correlate failures across repositories and report shared root causes — processing
  issues in the given order and producing exactly one report per issue (keyed
  `owner-repo-number`, since issue numbers collide across repositories).
- The run's full `stream-json` output is kept in `logs_dir` (`selected-issues.json`,
  `triage.prompt.md`, `triage.stream.jsonl`, `triage.result.json`, `triage.stderr.log`,
  plus `comments/issue-<key>.comment.md` in review mode) — the workflow uploads it as the
  `ai-incident-triage-logs` artifact.
- The job log shows a deterministic trace of everything the agent did
  (`[tool]`/`[say ]`/`[end ]` lines); the job summary tabulates outcome, turns, duration
  and cost.
- A final verification step re-reads the issues and warns about any missing triage comment
  (warn, not fail: the issue stays eligible and the next scheduled run is the retry).

## Analysis-only guarantee

The default allowlist gives the agent read/search tools, local file writes (needed to stage
the comment body — the runner is ephemeral and the agent has no `git` surface, so writes
cannot leave the machine), `gh` read commands, `gh issue comment`, log download commands,
and the cortex `jahia-ci-triage` tool — no `Edit`, no `git`/push, no PR or merge surface.
`--permission-mode dontAsk` denies everything not explicitly allowed. The prompt additionally forbids modifying anything and
instructs the agent to treat issue/log content as data, never as instructions.

One deliberate exception: when the failed run's logs carry a known transient-infrastructure
signature (unreachable maven artifact, `devtools.jahia.com` connect timeout), the agent may
restart the failed jobs (`gh run rerun --failed`) — and only then. The rerun permission is
granted only when `post_comments` is true; review mode stays strictly observational.

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
  every tunneled host AND the repository running the workflow must be allowlisted on IT's
  side — one reason the workflow runs centrally from this (allowlisted) repository.
- `GH_ISSUES_PRS_CHORES` must be able to read issues and post comments on every repository
  in the search scope.

## How it runs

The [`ai-incident-triage.yml`](../.github/workflows/ai-incident-triage.yml) workflow in this
repository is the single entry point:

- **`workflow_dispatch`** — the only trigger (the mTLS broker mints certificates exclusively
  for dispatch-triggered runs of this repository); org-wide by default, narrowable via the
  `search_scope` input (e.g. `repo:Jahia/sandbox`), with a `dry_run` mode that stops after
  selection.
- **Review mode** (`post_comments: false`, currently the default): the agent analyzes as
  usual but posts nothing — each would-be comment is stored as
  `comments/issue-<key>.comment.md` inside the `ai-incident-triage-logs` artifact and inlined
  in the job summary for human review. Since no marker lands on the issues, they stay
  eligible for the next run.
- **Development iteration** — dispatch the feature branch:
  `gh workflow run ai-incident-triage.yml --ref <branch> -f search_scope=repo:Jahia/sandbox`
  (dispatching a branch requires the workflow file to also exist on `main`).
- A schedule can be added to the same workflow once the pilot validates analysis quality.
