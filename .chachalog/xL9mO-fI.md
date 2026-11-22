---
# Allowed version bumps: patch, minor, major
jahia-modules-action: patch
---

AI bug scoring runs the `jahia-pm-score` tool from the cortex checkout as its working directory, where `mise exec` finds the venv that `ai-agent-setup` filled. Run from the workspace root, the tool found no `cortex` package and the scoring job failed on every run.
