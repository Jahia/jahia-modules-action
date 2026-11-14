---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

Changed the AI review of a pull request so that `jahia-ai` never approves it and posts every review as a comment.

A repository whose branch protection requires an approval now gets it from a person. An approval that `jahia-ai` posted before this release keeps its effect until someone dismisses it.
