---
# Allowed version bumps: patch, minor, major
jahia-modules-action: patch
---

Fixed the AI PR review failing at `Set up job` with `Unrecognized named-value: 'x'`, introduced by `v2.73.1` while fixing the previous expression bug: a template expression had been written inside a shell comment in the action's `run:` block as an illustration, and GitHub expands template expressions in `run:` bodies before the shell ever sees them — so the comment was evaluated and the action failed to load.
