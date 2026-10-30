---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

Added commit signing to the AI issue agent, so its pull requests merge on branches that require signed commits. The commits carry the name and the email of the agent account. Signing needs the `AI_AGENT_GPG_KEY`, `AI_AGENT_GPG_KEY_ID` and `AI_AGENT_GPG_KEY_PASSPHRASE` organization secrets.
