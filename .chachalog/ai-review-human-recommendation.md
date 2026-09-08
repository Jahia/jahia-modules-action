---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

The AI PR review now states the agent's confidence call: a **Human review** line in the review body (`not needed` / `recommended` / `required`, with a one-line reason), mirrored deterministically as a PR label (`🤖 AI-only review OK`, `🤖 Human review recommended`, `🤖 Human review required` — created on first use, previous recommendation swapped out). The `💀 Clear jahia-ai review` label also removes these labels.
