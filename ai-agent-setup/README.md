# ai-agent-setup

Provisions a self-hosted runner to run [Claude Code](https://code.claude.com) headlessly:

1. Installs the Claude Code CLI (native installer, no Node.js required).
2. Points it at the Jahia **LiteLLM gateway** by exporting `ANTHROPIC_BASE_URL`,
   `ANTHROPIC_AUTH_TOKEN` and the `ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL` aliases to
   `$GITHUB_ENV` (they apply to all subsequent steps of the job). Those three **map, they do
   not choose**: they say which deployment the gateway serves for each alias, while which
   alias a duty asks for is that duty's own `model` input (see
   [ai-pr-review's "Which model runs"](../ai-pr-review/README.md#which-model-runs)). Leave a
   duty's `model` empty and the CLI's own default decides — which moves with
   `claude_code_version`.
3. Verifies the gateway is reachable from the runner (DNS + HTTP), failing fast with DNS
   diagnostics instead of letting the agent retry against an unreachable endpoint.
4. Clones the [cortex agentic harness](https://github.com/Jahia/cortex) — Claude Code is meant
   to be started **from inside that checkout** so cortex's skills and instructions auto-load,
   and pre-trusts that checkout so its `.claude/settings.json` permissions apply.
5. Configures cortex usage telemetry — tokens, cost, model, skills and tools, never prompts or
   outputs. Two layers, because since Claude Code 2.1.282 the exporter reads its configuration
   from the **launch environment** alone, not from project-scoped settings (cortex ADR-0022):
   the `.env` no cortex clone carries gets `CORTEX_STATUSLINE_THEME=default` (a cortex session
   that draws no status line reports nothing either) and the `CORTEX_TELEMETRY_TOKEN`
   credential, while the telemetry environment itself — the same block a developer's shell gets
   from cortex's `mise.toml` through `mise activate` — is exported to `$GITHUB_ENV`, hardcoded
   collector included, so every later `claude` step of the job launches under it. Leave the
   input empty and the run reports nothing: the action then writes cortex's standing refusal
   (`CORTEX_TELEMETRY=off`) instead, so the harness's session-start notice does not ask the
   headless agent a question nobody is there to answer.
6. Installs [mise](https://mise.jdx.dev) and runs `mise install` and `mise run libraries` in
   the cortex checkout. Every cortex tool launches through `mise exec` (cortex ADR-0031),
   including the fail-closed guards cortex runs before every file write — without mise the
   harness refuses every `Write`, and an agent that finished its work cannot deliver its
   result file.
7. Runs two live checks and fails fast if either breaks: a hello-world round trip through the
   gateway (auth, model aliases, network path), then a cortex-awareness question the agent can
   only answer if the harness actually loaded (it must name the `analyze-jahia-ci` skill).

This action is **use-case agnostic**: incident triage
([`ai-incident-triage`](../ai-incident-triage)) is its first consumer, but any future
Claude-on-runner duty should reuse it as-is.

## Requirements

- An Ubuntu runner. Pair it with [`mtls-tunnel`](../mtls-tunnel) when the agent needs to
  reach internal Jahia services (LiteLLM gateway, `qa.jahia.com` artifacts) — the tunnel
  step must run **before** this action so the gateway connectivity check can pass.
- Runners are typically **ephemeral**: everything this action installs disappears after the
  job, and everything it *doesn't* install must come from the runner image. It warns (without
  failing) when `git`, `python3`, `unzip` or `gh` are missing, since the cortex tooling needs them.
- `curl` and outbound access to `claude.ai` (installer) and the LiteLLM gateway.

## Inputs

| Name | Required | Default | Description |
|---|---|---|---|
| `claude_code_version` | no | `stable` | Claude Code version to install (a specific version like `2.1.89`, or `stable` / `latest`) |
| `anthropic_base_url` | yes | — | Base URL of the Anthropic-compatible gateway (LiteLLM) |
| `anthropic_auth_token` | yes | — | Auth token for the gateway. Each duty passes **its own** key — see [Gateway keys are per duty](#gateway-keys-are-per-duty) |
| `default_opus_model` | no | `''` | Model served by the gateway for the "opus" alias |
| `default_sonnet_model` | no | `''` | Model served by the gateway for the "sonnet" alias |
| `default_haiku_model` | no | `''` | Model served by the gateway for the "haiku" alias |
| `cortex_repository` | no | `Jahia/cortex` | Repository holding the cortex agentic harness |
| `cortex_ref` | no | `main` | Git ref of cortex to check out |
| `cortex_path` | no | `cortex` | Path (relative to the workspace) to clone cortex into |
| `cortex_telemetry_token` | no | `''` | Credential cortex sends with its own usage telemetry, written to the checkout's `.env`. Empty means the run reports nothing. The reusable workflows in this repository pass `secrets.CORTEX_TELEMETRY_TOKEN` |
| `github_token` | yes | — | Token able to clone the cortex repository |

## Outputs

| Name | Description |
|---|---|
| `cortex_path` | Absolute path of the cortex checkout |
| `claude_version` | Version of the Claude Code CLI that was installed |

## Gateway keys are per duty

Every duty passes its own gateway key rather than one shared token, so the gateway attributes
each request to the duty that made it:

| Duty | Secret |
|---|---|
| [`ai-pr-review`](../ai-pr-review) | `AI_LITELLM_AUTH_TOKEN_USAGE_PRS` |
| [`ai-incident-triage`](../ai-incident-triage) | `AI_LITELLM_AUTH_TOKEN_USAGE_INCIDENTS` |
| [`ai-tldr`](../ai-tldr) | `AI_LITELLM_AUTH_TOKEN_USAGE_TLDR` |

A new duty gets a new key; it does not borrow one of these. An absent or wrong key fails at the
gateway smoke test below, before any agent starts, so the job says so instead of half-running.

## Example

```yaml
      - name: Set up Claude Code and the cortex harness
        id: setup
        uses: jahia/jahia-modules-action/ai-agent-setup@v2
        with:
          anthropic_base_url: ${{ vars.AI_LITELLM_BASE_URL }}
          anthropic_auth_token: ${{ secrets.AI_LITELLM_AUTH_TOKEN_USAGE_<DUTY> }}
          default_opus_model: ${{ vars.AI_LITELLM_ANTHROPIC_DEFAULT_OPUS_MODEL }}
          default_sonnet_model: ${{ vars.AI_LITELLM_ANTHROPIC_DEFAULT_SONNET_MODEL }}
          default_haiku_model: ${{ vars.AI_LITELLM_ANTHROPIC_DEFAULT_HAIKU_MODEL }}
          cortex_telemetry_token: ${{ secrets.CORTEX_TELEMETRY_TOKEN }}
          github_token: ${{ secrets.GH_ISSUES_PRS_CHORES }}

      - name: Do something with the agent
        shell: bash
        working-directory: ${{ steps.setup.outputs.cortex_path }}
        run: |
          export PATH="$HOME/.local/bin:$PATH"
          claude -p "your prompt" --allowedTools "Read" --permission-mode dontAsk
```
