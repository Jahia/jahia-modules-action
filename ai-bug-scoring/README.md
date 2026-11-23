# ai-bug-scoring

Gives each open bug a PM score with system A2, so the PM can rank the bugs that wait for a decision.
A deterministic, LLM-free action selects the bugs whose score field is empty. A headless
[Claude Code](https://code.claude.com) agent records the factors of each bug. A script adds the
points, writes the PM Score issue field and posts one breakdown comment on the bug.

The agent never writes to GitHub. It reads the ticket files that a script fetched, and writes one
factors file per bug. It has no shell, no network and no GitHub token.

## Which bugs, which field

The selection searches the scope (`org:Jahia` by default) for the open issues of type **Bug**, in
repositories that are not archived, and keeps the ones whose **PM Score** organization issue field
is empty. An empty field means "not scored yet", so each bug is scored once. To score a bug again,
empty its field. Each run scores at most `max_bugs` bugs, and the next run takes the rest.

The search cannot filter on an issue field, so the selection reads the field of each found issue,
most recent first, and stops once `max_bugs` bugs are collected: a new bug is scored while its
ticket is fresh, and the oldest bugs wait until the backlog in front of them is scored.

## System A2

The agent records the factors with the rubric of the `jahia-pm-bug-scoring` skill of
[Jahia/cortex](https://github.com/Jahia/cortex), read from the cortex checkout that
`ai-agent-setup` leaves (the `cortex_path` input). The rubric owns the factor definitions and
their thresholds, such as the version cut-off of the old-versions penalty. Its `reach.md` lists the
reach & importance of each repository and feature: very high (+20), high (+15), medium (+5), low (0)
or none (−20). The `jahia-pm-score` tool of the same skill holds the points of each factor and
applies the score — it validates the factors, writes the PM Score issue field and posts the
breakdown comment — so the whole intelligence lives beside the rubric in cortex, and this action
only orchestrates: selection, ticket preparation, the agent runs and the run report.

Example: an editor is blocked (+20) on a feature most customers use (+15), with a painful
workaround (+4). The ticket is a regression (+5), carries the customer label from one customer (+5)
and states the expected behaviour (+6). Its score is 55.

### The field value

- **The field value is the score**: the sum of the points, with no bonus. A data loss of 75 points
  shows 75.
- **A security bug shows −1**, with no comment: security bugs follow the security process, and a
  comment on a public repository would disclose one. The value keeps the bug from being read
  again.
- **A bug with no valid factors gets nothing**: its field stays empty, and the next run tries it
  again.

## The comment

Each scored bug gets one comment that opens with the hidden marker `<!-- ai-bug-scoring -->`. It
shows the field value, the points of each factor and the agent's reason. A new score of the same
bug edits that comment instead of posting a second one. The fetch leaves the comment out of the
text the agent reads.

## Actions

### `ai-bug-scoring/select-bugs`

LLM-free selection, runs on any cheap runner.

| Input | Default | Description |
|---|---|---|
| `github_token` | — | Token able to search the issues of the scope and read their issue fields |
| `org` | `Jahia` | Organization that owns the issue field |
| `search_scope` | `org:Jahia` | Issue-search scope qualifier, e.g. `repo:Jahia/sandbox` |
| `field` | `PM Score` | Name of the organization number issue field that holds the score |
| `max_bugs` | `30` | Most bugs scored in one run |

| Output | Description |
|---|---|
| `bugs` | JSON array of `{key, repository, number, url, field_id}`, sorted by repository and number |
| `has_bugs` | `"true"` when at least one bug is selected |

### `ai-bug-scoring` (this action)

Runs the agent, then scores and writes. Requires [`ai-agent-setup`](../ai-agent-setup) and an
[`mtls-tunnel`](../mtls-tunnel) to the LiteLLM gateway.

| Input | Default | Description |
|---|---|---|
| `bugs` | — | JSON array produced by `select-bugs` |
| `github_token` | — | Token that reads the issues and posts the comments |
| `field_token` | — | Token that writes the PM Score issue field (push access to every selected repository) |
| `model` | `opus` | Claude Code `--model` value |
| `dry_run` | `false` | `true` runs the agent but writes nothing; `false` writes the field and posts the comments |
| `marker` | `<!-- ai-bug-scoring -->` | Hidden marker of the comment |
| `batch_size` | `10` | Tickets per agent run; each run starts with a fresh context |
| `cortex_path` | — | Absolute path of the cortex checkout (from `ai-agent-setup`) that holds the rubric |

| Output | Description |
|---|---|
| `logs_dir` | Directory holding the tickets, the prompts, the agent streams, the factors and `results.json` — upload it as an artifact |

## How it runs

- [`ai-bug-scoring.yml`](../.github/workflows/ai-bug-scoring.yml) is the entry point. It runs by
  `workflow_dispatch` here, and a private repository calls it by `workflow_call` to own the
  schedule. The logs hold the text of private tickets, so the scheduled runs belong to a private
  repository. Each job exposes a `status` output — empty on success, a message on failure — and
  the workflow exposes them as `select_status` and `score_status`, so the caller can report the
  run to github-incident.
- **Dry run** (`dry_run: true`): the agent runs but nothing is written. Each would-be comment is
  stored under `comments/` in the `ai-bug-scoring-logs` artifact and shown in the job summary, with
  a table of every bug and its field value. The logs also go to the Jahia servers, for 30 days.
- **Development iteration**: `gh workflow run ai-bug-scoring.yml --ref <branch> -f max_bugs=5 -f dry_run=true`.
  Dispatching a branch requires the workflow file to exist on `main` too.

## Development

The scripts are a TypeScript package in the style of [`ai-issue-agent`](../ai-issue-agent):
functional, arrow functions, one function per file under [`src/`](src), tests under
[`__tests__/`](__tests__). `npm run all` builds, checks the format, lints, tests and rebuilds the
committed `dist/` bundles, which the runtime executes; CI fails when the bundles do not match the
sources, so run it before pushing.

## Requirements

- Self-hosted Ubuntu runner. The scripts run on the Node of the GitHub Actions runtime: no
  `python3`, and no `gh` beyond what `ai-agent-setup` needs.
- A `workflow_call` caller passes `secrets: inherit`, so the jobs see the org secrets they read.
- Org secrets and variables: `GH_ISSUES_PRS_CHORES` (searches the issues),
  `AI_AGENT_GH_ISSUES_PRS_CHORES` (reads the issues, posts the comments and writes the PM Score
  issue field, so its account needs push access to every repository that holds a scored bug),
  `BASTION_SSH_PRIVATE_KEY_JAHIACI` (the 30-day log upload to the Jahia
  servers),
  `AI_LITELLM_AUTH_TOKEN` (the shared gateway key), `AI_LITELLM_BASE_URL`,
  `AI_LITELLM_ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL`, `CORTEX_TELEMETRY_TOKEN`, and the mTLS
  bastion surface (`INFRAJAHIA_MTLS_CA_URL`, `INFRAJAHIA_MTLS_BASTION`,
  `INFRAJAHIA_MTLS_STEP_ROOT`, `INFRAJAHIA_MTLS_SERVER_CA`).
- The agent job needs `permissions: id-token: write` for the tunnel, and the repository that runs
  the workflow must be allowlisted with the mTLS broker.
- A scored bug costs about $0.10 on Opus, so a first run over 130 bugs costs about $13.
