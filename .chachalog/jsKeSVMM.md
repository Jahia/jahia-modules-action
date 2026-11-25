---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

The AI issue agent can now create an issue and place it on a board when a person asks for it, with `gh-wrapper issue create` and `gh-wrapper project item-add` or `item-edit`. Before, the deny list refused both and the agent answered with a draft body for a person to paste. Raw `gh issue create` stays denied.
