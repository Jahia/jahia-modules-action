---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

Changed the AI review of a pull request so that `jahia-ai` approves only a clean pull request and comments otherwise.

A review is clean when it has no finding, needs no human review, no earlier thread of `jahia-ai` stays open, and no push landed during the review. A comment of `jahia-ai` also removes its earlier approval of the pull request, so a later push needs a new review.
