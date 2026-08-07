# claude-code-setup

Provisions a self-hosted runner to run [Claude Code](https://code.claude.com) headlessly:

1. Installs the Claude Code CLI (native installer, no Node.js required).
2. Points it at the Jahia **LiteLLM gateway** by exporting `ANTHROPIC_BASE_URL`,
   `ANTHROPIC_AUTH_TOKEN` and the `ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL` aliases to
   `$GITHUB_ENV` (they apply to all subsequent steps of the job).
3. Clones the [cortex agentic harness](https://github.com/Jahia/cortex) — Claude Code is meant
   to be started **from inside that checkout** so cortex's skills and instructions auto-load.

This action is **use-case agnostic**: incident triage
([`claude-incident-triage`](../claude-incident-triage)) is its first consumer, but any future
Claude-on-runner duty should reuse it as-is.

## Requirements

- A **host** runner (Ubuntu), not a container — pair it with
  [`vpn-tunnel`](../vpn-tunnel) when the agent needs to reach VPN-only resources, and
  `vpn-tunnel` refuses to run inside containers.
- Runners are typically **ephemeral**: everything this action installs disappears after the
  job, and everything it *doesn't* install must come from the runner image. It warns (without
  failing) when `git`, `python3`, `unzip` or `gh` are missing, since the cortex tooling needs them.
- `curl` and outbound access to `claude.ai` (installer) and the LiteLLM gateway.

## Inputs

| Name | Required | Default | Description |
|---|---|---|---|
| `claude_code_version` | no | `stable` | Claude Code version to install (a specific version like `2.1.89`, or `stable` / `latest`) |
| `anthropic_base_url` | yes | — | Base URL of the Anthropic-compatible gateway (LiteLLM) |
| `anthropic_auth_token` | yes | — | Auth token for the gateway |
| `default_opus_model` | no | `''` | Model served by the gateway for the "opus" alias |
| `default_sonnet_model` | no | `''` | Model served by the gateway for the "sonnet" alias |
| `default_haiku_model` | no | `''` | Model served by the gateway for the "haiku" alias |
| `cortex_repository` | no | `Jahia/cortex` | Repository holding the cortex agentic harness |
| `cortex_ref` | no | `main` | Git ref of cortex to check out |
| `cortex_path` | no | `cortex` | Path (relative to the workspace) to clone cortex into |
| `github_token` | yes | — | Token able to clone the cortex repository |

## Outputs

| Name | Description |
|---|---|
| `cortex_path` | Absolute path of the cortex checkout |
| `claude_version` | Version of the Claude Code CLI that was installed |

## Example

```yaml
      - name: Set up Claude Code and the cortex harness
        id: setup
        uses: jahia/jahia-modules-action/claude-code-setup@v2
        with:
          anthropic_base_url: ${{ vars.AI_LITELLM_BASE_URL }}
          anthropic_auth_token: ${{ secrets.AI_LITELLM_AUTH_TOKEN }}
          default_opus_model: ${{ vars.AI_LITELLM_ANTHROPIC_DEFAULT_OPUS_MODEL }}
          default_sonnet_model: ${{ vars.AI_LITELLM_ANTHROPIC_DEFAULT_SONNET_MODEL }}
          default_haiku_model: ${{ vars.AI_LITELLM_ANTHROPIC_DEFAULT_HAIKU_MODEL }}
          github_token: ${{ secrets.GH_ISSUES_PRS_CHORES }}

      - name: Do something with the agent
        shell: bash
        working-directory: ${{ steps.setup.outputs.cortex_path }}
        run: |
          export PATH="$HOME/.local/bin:$PATH"
          claude -p "your prompt" --allowedTools "Read" --permission-mode dontAsk
```
