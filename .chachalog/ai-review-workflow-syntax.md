---
# Allowed version bumps: patch, minor, major
jahia-modules-action: patch
---

Fixed a workflow syntax error introduced in `v2.73.0` that broke **Delivery - PR Chores** in every repository pinned to `v2`: `reusable-ai-pr-review.yml` computed the agent's timeout with `${{ inputs.timeout_job - 5 }}`, but GitHub Actions expressions have no arithmetic operators, so the workflow failed to compile and the whole run failed before a single job started — including PR title linting, the changelog check and the documentation comment, none of which involve the AI review. The subtraction now happens in shell inside the `ai-pr-review` action, which takes the job's timeout as `job_timeout_minutes` and reserves its margin itself.
