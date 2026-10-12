---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

The AI PR review now asks the cortex harness whether the pull request under review needs the review itself held to a stricter wording discipline. When it does, the agent's prompt carries the section the harness returns, and a step between the agent and GitHub checks the review body and every inline comment against it: a review that does not meet it is not posted, and the run fails with the request still pending. The rule and the check live in the harness (`tools/ai-review-wording`), so this action needs a cortex ref that carries that tool.
