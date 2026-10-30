---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

The AI issue agent can now read the change in its worktree with `git diff` and `git show`, run as `git -C sources/<name>@<slug>`. Before, it could only push from there.
