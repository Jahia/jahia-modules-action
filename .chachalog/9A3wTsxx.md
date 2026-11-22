---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

AI bug scoring now applies the scores with the `jahia-pm-score` tool of the cortex checkout: the points tables, the PM Score field write and the breakdown comment live beside the rubric in the `jahia-pm-bug-scoring` skill of Jahia/cortex, and the action keeps the orchestration (selection, ticket preparation, the agent runs, the run report). The agent prompt names the skill. The `cortex_ref` input must point at a cortex that carries the tool, which `main` does from 2026-11-22.
