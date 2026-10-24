---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

The AI issue agent works as one of six SDLC profiles (Product Owner, Engineering Manager, Software Developer, DevOps, QA, Security Engineer), named in its opening task comment, and the Software Developer profile ships code: the session can take a worktree, commit, push and open a draft pull request through cortex's `jahia-pr` tool — draft-only by construction and lint-gated, while merge, ready, review, close, force-pushes and raw `gh pr create` stay denied in every spelling. Pushes and pull requests authenticate as the agent account, which the run action wires via `gh auth setup-git`.
