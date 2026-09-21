---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

The three AI actions now pin the model they run on, instead of taking whatever the installed Claude Code CLI happened to default to — a default that moves with `claude_code_version`, so a CLI upgrade could silently change the model behind a review. A new `model` input, plumbed through `reusable-ai-pr-review.yml`, `reusable-ai-tldr.yml` and `ai-incident-triage.yml`, passes `--model` to the agent: `ai-pr-review` defaults to `opus` (reading a diff for real defects is the reasoning-heaviest of the three), `ai-tldr` and `ai-incident-triage` to `sonnet`. The value is either an alias the LiteLLM gateway maps (`opus`, `sonnet`, `haiku`) or a model name it serves verbatim; empty passes no `--model` at all and restores the previous behaviour. The agent identity stamped on every comment now names the model actually asked for, resolved through the gateway's alias variables — it previously reported the sonnet alias regardless of what ran.
