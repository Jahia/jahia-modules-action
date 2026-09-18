---
# Allowed version bumps: patch, minor, major
jahia-modules-action: patch
---

Fixed the AI PR review failing at `Set up job` with `Unrecognized named-value: 'x'`, introduced by `v2.73.1` while fixing the previous expression bug: a template expression had been written inside a shell comment in the action's `run:` block as an illustration, and GitHub expands template expressions in `run:` bodies before the shell ever sees them — so the comment was evaluated and the action failed to load.

A new `Lint - Action expressions` check now validates that every template expression in this repository's action manifests and workflows resolves to a real Actions context. It runs on the branch, which is the point: `delivery-pr-chores.yml` calls the reusable workflows at `@v2`, so a pull request's own checks exercise the last release rather than the branch — the reason both expression bugs reached consumers. `actionlint` cannot cover this on its own, as it only inspects workflow files and never composite `action.yml` manifests.
