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
   the `.env` no cortex clone carries gets the `CORTEX_TELEMETRY_TOKEN` credential and nothing
   else (cortex reads only credentials there, and its session-start migration wakes the agent to
   move any other key), while the telemetry environment itself — the same block a developer's
   shell gets from cortex's `mise.toml` through `mise activate` — is exported to `$GITHUB_ENV`,
   hardcoded collector included, so every later `claude` step of the job launches under it.
   Leave the input empty and the run reports nothing: the action then exports cortex's standing
   refusal (`CORTEX_TELEMETRY=off`) to `$GITHUB_ENV` instead, so the harness's session-start
   notice does not ask the headless agent a question nobody is there to answer.
6. Installs [mise](https://mise.jdx.dev) and runs `mise install` and `mise run libraries` in
   the cortex checkout. Every cortex tool launches through `mise exec` (cortex ADR-0031),
   including the fail-closed guards cortex runs before every file write — without mise the
   harness refuses every `Write`, and an agent that finished its work cannot deliver its
   result file.
7. Prepares the `cortex-secret-mask` mod of the cortex checkout: exports its path as
   `CORTEX_MASK_MOD_DIR`, adds the folder of `gitleaks` to the `PATH`, and runs the tests of
   the mod. [Credentials in the output of a tool](#credentials-in-the-output-of-a-tool) states
   how each duty uses it.
8. Runs two live checks and fails fast if either breaks: a hello-world round trip through the
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

## Credentials in the output of a tool

The setup prepares the `cortex-secret-mask` mod of the Cortex harness, and exports its path as
`CORTEX_MASK_MOD_DIR`. Each duty passes `${CORTEX_MASK_MOD_DIR:+--plugin-dir "$CORTEX_MASK_MOD_DIR"}`
to `claude -p`, which keeps the path in one word and passes nothing when the variable is unset.
The mod replaces each credential in the output of a tool with a mask such as
`[MASKED: GitHub token]`, before the model reads that output. The job log and the stream file of
the logs artifact then show the mask in the output of each tool.

The mod masks no other text, such as the prompt, the text of the model or the output of a hook.
The mod also refuses a write that puts a mask in a file in place of the real credential. The
`MOD.md` file of the mod, in the Cortex harness, states its patterns and its limits.

A caller sees the mask. A session reads a mask in place of a test password, such as the value of
`SUPER_USER_PASSWORD`. The session edits around the masked lines of a file, and a command that
the session runs still reads the real value.

The mod applies its built-in patterns first. It then runs `gitleaks` on an output of 512 KB or
less. `mise install` installs `gitleaks` from the `mise.toml` file of the Cortex harness, but
not on the `PATH` of the job. The setup adds the folder of `gitleaks` to that `PATH`. Without
`gitleaks`, a credential that has no key and no built-in format reaches the model. A bare GitLab
token is an example.

A warning appears in three cases, and the session runs in each. Each item names the step that
writes it:

- The init event of the stream of a session names no `cortex-secret-mask@inline` plugin. Claude
  Code exits 0 and writes nothing to stderr when it loads no mod, so each duty reads its stream
  after the session. A commit of `cortex_ref` with no `mods/cortex-secret-mask` folder and a
  corrupt manifest of the mod both give this warning. A session that dies before its init event
  gives it too, and its exit code then shows the failure.
- `claude plugin test` fails on the mod during the setup. A hooks module that fails to load still
  leaves the mod in the init event, and only the tests of the mod see it. The job log holds the
  output of the tests.
- mise found no `gitleaks` for that commit during the setup. The mod then applies its built-in
  patterns alone.

The input `debug` of a duty writes the debug log of Claude Code to a file of its logs artifact.
That log holds the output of each command hook and the body of each error of the gateway, and the
mod masks neither. Claude Code writes no request header and no environment variable to it.

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
          claude -p "your prompt" --allowedTools "Read" --permission-mode dontAsk ${CORTEX_MASK_MOD_DIR:+--plugin-dir "$CORTEX_MASK_MOD_DIR"}
```
