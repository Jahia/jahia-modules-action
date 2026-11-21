# AI pull request summary

The action runs a Claude Code agent of the Cortex harness on one pull request. The agent writes a summary of 2 or
3 bullets for its reviewer, as a JSON file. The job `summarize` of `.github/workflows/reusable-review-notification.yml`
runs it, and `slack-notification` writes the summary into the message of the review request.

## Inputs

| Input | Required | Value |
|---|---|---|
| `target_url` | yes | The URL of the pull request. |
| `github_token` | yes | The token that reads the pull request. Pass a token that cannot write, such as the `github.token` of a job with `contents: read` and `pull-requests: read`. |
| `cortex_path` | yes | The absolute path of the Cortex checkout, which `ai-agent-setup` gives. |
| `model` | no | The model of the agent. It defaults to `sonnet`. |

The output `summary_file` is the path of the JSON file `{"bullets": [...]}`. It is empty when the agent wrote no
valid JSON, and a failed run never fails the job.

## What the agent can do

The text of a pull request can carry instructions, so the agent never reaches the network:

- A step before the agent reads the title, the description, the changed files and the diff with `github_token`.
  The agent reads them as files, and gets no token.
- The agent has no Bash, no web tool and no MCP tool, and its one allowed write is the summary file.
- `prompt.md` states that the text of the pull request is data, and never an instruction.

The caller runs the action for a pull request of the repository alone, and never for a pull request of a fork.
