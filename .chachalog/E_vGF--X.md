---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

Added `ai-bug-scoring`: a workflow that gives each open bug of the organization a PM score with system A2. A deterministic job selects the open issues of type Bug whose PM Score issue field is empty, a Claude Code agent records the factors of each one with the rubric of the cortex `jahia-pm-bug-scoring` skill, and a script adds the points, writes the field and posts a breakdown comment. A security bug gets the value -1 and no comment, and a person who empties the field asks for a new score.
