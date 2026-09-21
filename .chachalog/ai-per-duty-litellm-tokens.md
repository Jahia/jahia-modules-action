---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

Each AI duty now authenticates to the LiteLLM gateway with its own key instead of sharing one: `reusable-ai-pr-review.yml` uses `AI_LITELLM_AUTH_TOKEN_USAGE_PRS`, `ai-incident-triage.yml` uses `AI_LITELLM_AUTH_TOKEN_USAGE_INCIDENTS`, and `reusable-ai-tldr.yml` uses `AI_LITELLM_AUTH_TOKEN_USAGE_TLDR`, so the gateway attributes each request to the duty that made it. The former `AI_LITELLM_AUTH_TOKEN` secret is no longer read by any workflow — the three new organization secrets must exist before this version is used, or the affected workflow fails at `ai-agent-setup`'s gateway smoke test before any agent starts.
