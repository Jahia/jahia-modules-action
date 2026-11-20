---
# Allowed version bumps: patch, minor, major
jahia-modules-action: patch
---

AI bug scoring now authenticates to the LiteLLM gateway with the shared `AI_LITELLM_AUTH_TOKEN` organization secret. The workflow read `AI_LITELLM_AUTH_TOKEN_USAGE_BUG_SCORING`, a secret that does not exist, so every run failed at the gateway smoke test before the agent started.
