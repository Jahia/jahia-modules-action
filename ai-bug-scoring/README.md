# ai-bug-scoring

Gives each open bug a PM score with system A2, so the PM can rank the bugs that wait for a decision.
A deterministic, LLM-free action selects the bugs whose score field is empty. A headless
[Claude Code](https://code.claude.com) agent records the factors of each bug. A script adds the
points, writes the board fields and posts one breakdown comment on the bug.

The agent never writes to GitHub. It reads the ticket files that a script fetched, and writes one
factors file per bug. It has no shell, no network and no GitHub token.

## Which bugs, which fields

| Board | Filter | Field |
|---|---|---|
| Bugs Triage (org project 13) | `status:"Triage needed" type:Bug` | `PM score (for triage)` |
| Engineering - Delivery (org project 50) | `priority:"For Decision" -status:Done type:Bug` | `PM score (bugs)` |

A bug is selected when its field is empty, so each bug is scored once. A bug that waits on both
boards gets one score in both fields. To score a bug again, empty its field. Each run scores at
most `max_bugs` bugs, and the next run takes the rest.

## System A2

The agent records the factors with [`rubric.md`](rubric.md). [`src/scoring.py`](src/scoring.py)
adds the points:

| Factor | Points |
|---|---|
| Impact: content loss or corruption, erratic in production, site fully broken | 40 · P1 |
| Impact: visitors partly impacted | 30 |
| Impact: editors blocked, developers blocked | 20 |
| Impact: slowed down, not blocked | 4 |
| Impact: cosmetic or wording | 1 |
| Reach: high, medium, low | +15, +5, 0 |
| Workaround: none, painful, unknown, easy | +8, +4, +4, 0 |
| Regression | +5 |
| Customers: the `customer` label, then each customer the ticket names, up to 3 | +5 each |
| Expected behaviour clear | +6 |
| Jahia Cloud | +3 |
| Only versions below 8.2 | −5 |

Example: an editor is blocked (+20) on a feature most customers use (+15), with a painful
workaround (+4). The ticket is a regression (+5), carries the customer label from one customer (+5)
and states the expected behaviour (+6). Its score is 55.

### The board value

- **A P1 case adds 100.** A2 ranks every P1 case first, whatever its points, and the board sorts
  by one number. A P1 case of 75 points shows 175.
- **A security bug shows −1**, with no comment: security bugs follow the security process, and a
  comment on a public repository would disclose one. The value keeps the bug from being read
  again.
- **A bug with no valid factors gets nothing**: its field stays empty, and the next run tries it
  again.

## The comment

Each scored bug gets one comment that opens with the hidden marker `<!-- ai-bug-scoring -->`. It
shows the board value, the points of each factor and the agent's reason. A new score of the same
bug edits that comment instead of posting a second one. The fetch leaves the comment out of the
text the agent reads.

## Actions

### `ai-bug-scoring/select-bugs`

LLM-free selection, runs on any cheap runner.

| Input | Default | Description |
|---|---|---|
| `github_token` | — | Token able to read both organization projects |
| `org` | `Jahia` | Organization that owns both boards |
| `triage_board`, `triage_filter`, `triage_field` | `13`, see above | The triage board |
| `delivery_board`, `delivery_filter`, `delivery_field` | `50`, see above | The delivery board |
| `max_bugs` | `30` | Most bugs scored in one run |

| Output | Description |
|---|---|
| `bugs` | JSON array of `{key, repository, number, url, targets: [{board, project_id, item_id, field_id, field}]}`, sorted by repository and number |
| `has_bugs` | `"true"` when at least one bug is selected |

### `ai-bug-scoring` (this action)

Runs the agent, then scores and writes. Requires [`ai-agent-setup`](../ai-agent-setup) and an
[`mtls-tunnel`](../mtls-tunnel) to the LiteLLM gateway.

| Input | Default | Description |
|---|---|---|
| `bugs` | — | JSON array produced by `select-bugs` |
| `github_token` | — | Token that reads the issues and posts the comments |
| `project_token` | — | Token that writes the score fields of both boards |
| `model` | `opus` | Claude Code `--model` value |
| `write` | `false` | `true` writes the fields and posts the comments; `false` is review mode |
| `marker` | `<!-- ai-bug-scoring -->` | Hidden marker of the comment |
| `batch_size` | `10` | Tickets per agent run; each run starts with a fresh context |

| Output | Description |
|---|---|
| `logs_dir` | Directory holding the tickets, the prompts, the agent streams, the factors and `results.json` — upload it as an artifact |

## How it runs

- [`ai-bug-scoring.yml`](../.github/workflows/ai-bug-scoring.yml) is the entry point. It runs by
  `workflow_dispatch` here, and a private repository calls it by `workflow_call` to own the
  schedule. The logs hold the text of private tickets, so the scheduled runs belong to a private
  repository.
- **Review mode** (`write: false`, the default): nothing is written. Each would-be comment is stored
  under `comments/` in the `ai-bug-scoring-logs` artifact and shown in the job summary, with a table
  of every bug and its board value.
- **Development iteration**: `gh workflow run ai-bug-scoring.yml --ref <branch> -f max_bugs=5`.
  Dispatching a branch requires the workflow file to exist on `main` too.

## Requirements

- Self-hosted Ubuntu runner with `gh` and `python3`.
- Org secrets and variables: `GH_ISSUES_PRS_CHORES` (reads and writes both boards),
  `AI_AGENT_GH_ISSUES_PRS_CHORES` (reads the issues and posts the comments),
  `AI_LITELLM_AUTH_TOKEN_USAGE_BUG_SCORING` (the gateway key of this duty), `AI_LITELLM_BASE_URL`,
  `AI_LITELLM_ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL`, `CORTEX_TELEMETRY_TOKEN`, and the mTLS
  bastion surface (`INFRAJAHIA_MTLS_CA_URL`, `INFRAJAHIA_MTLS_BASTION`,
  `INFRAJAHIA_MTLS_STEP_ROOT`, `INFRAJAHIA_MTLS_SERVER_CA`).
- The agent job needs `permissions: id-token: write` for the tunnel, and the repository that runs
  the workflow must be allowlisted with the mTLS broker.
- A scored bug costs about $0.10 on Opus, so a first run over 130 bugs costs about $13.
