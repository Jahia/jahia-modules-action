---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

Added a secret scan to pull requests, which fails when one of their commits adds a token, a password or a private key.

The PR chores workflow runs it on the commits of the pull request only. A repository allowlists its test values in a `.gitleaks.toml` at its root, and the file applies once it is merged.
