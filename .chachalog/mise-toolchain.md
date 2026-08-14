---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

Added support for `mise.toml`: modules that declare one now get their node **and yarn** versions from it, in static analysis, javascript builds, integration tests, Maven builds, releases and publications. Modules without a `mise.toml` are unaffected.

If your module has a `mise.toml`, the `node_version`, `yarn_version` and `yarn_tests_version` inputs no longer apply and can be removed from your workflow — a warning is logged if you still pass a yarn version. Previously yarn came from whatever the runner happened to ship, or from a `yarnPath` committed inside the module, so the version used could change without notice.
