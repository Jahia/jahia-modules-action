---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

The AI issue agent's commits and pushes now run only through cortex's `jahia-pr` tool — `open` for a new draft pull request, `push` to iterate on one, never with force. The permission lists drop the plain git write verbs and every `git -C <dir>` rule, which a prefix-matched permission list never honored, and `EnterWorktree` joins the deny floor so a worktree opens only through `cortex-sources`.
