---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

Added a secret scan to pull requests, which fails when a commit of the pull request adds a token, a password or a private key.

The scan runs in the PR chores workflow and reads only the commits of the pull request. A repository can allowlist its test values in a `.gitleaks.toml` at its root.
