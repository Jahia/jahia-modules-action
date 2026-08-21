---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

Reduced what a module must declare to call the `reusable-on-code-change` workflow: the ref under test, the Sonar comparison branch, the test artifact prefix, the Jahia test image and the standalone test run are now derived from the caller's context or from `module_id`. A repository with integration tests needs four inputs instead of fourteen.

Five defaults changed and may affect a caller that relied on them: `static_analysis_auditci_level` is now `critical`, `integration_tests_should_skip_testrail` is now `true`, `integration_tests_jahia_image` now points at `ghcr.io/jahia/jahia-ee-dev:8-SNAPSHOT`, the test artifacts are prefixed with the module id instead of `tests`, and the Sonar analysis compares against the pull request's base branch instead of `main`. Pass the input explicitly to keep the previous value.
