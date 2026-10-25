---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

The AI issue agent may now comment on and edit an issue through cortex's `gh-wrapper` (`issue comment`, `issue edit`), the route the cortex `jahia-issue-agent` skill moves to, and the `jahia-issue-agent` tool stays allowed during that move. The raw `gh issue comment` and `gh issue edit` stay denied. The guard now creates the `🧠 Human needed !` escalation label in a repository that lacks it.
