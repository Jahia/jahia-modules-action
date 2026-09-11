---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

Added an AI analysis of integration-test runs: with the new `ai_analysis_enabled` input of the `reusable-integration-tests` workflow (off by default), a Claude Code agent running from the cortex harness analyzes the run's artifacts right after the tests, on every outcome, and writes a short human-readable report to the job summary — why the tests failed, or whether the Jahia logs hold anything unexpected on a green run.

The `ai-incident-triage` action gained a run mode for it (`artifacts_path` input), next to its existing issues mode. The AI steps never fail the job. Opting in requires the calling job to grant `id-token: write` and the repository to be allowlisted with the mTLS broker; see the action's README.
