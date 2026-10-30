---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

Added an error annotation for each failed Cypress test, which names the test, its failure message and its spec file.

The Slack notification of a failed run lists these failures, at most 9 for each job.
