---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

New `ai-pr-review` action (with its `ai-pr-review/check-request` guard) and `reusable-ai-pr-review.yml` reusable workflow, triggered from `reusable-delivery-pr-chores.yml`: when a review is requested from the `jahia-ai` account on a PR, a Claude Code agent (cortex harness, LiteLLM via the mTLS tunnel) reviews it once and submits a single COMMENT review — re-triggered only by re-requesting a review from that account, never by PR updates. Calling workflows must add `review_requested` to their `pull_request` trigger types and grant `id-token: write` to opt in.
