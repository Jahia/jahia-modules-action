---
# Allowed version bumps: patch, minor, major
jahia-modules-action: patch
---

An AI PR review that runs out of time no longer disappears without a trace. The agent now gets a wall-clock budget of its own (the calling job's timeout minus a 5-minute reserve) enforced inside the action, so reaching it is a normal step failure instead of a job cancellation: the partial session is still rendered into `review.transcript.log`, the `ai-pr-review-logs` artifact is still uploaded to GitHub and to the Jahia servers, the job summary still gets its row, and the job log carries an explicit `AI review timed out` error naming the knob to raise (`timeout_job`). A cancelled or timed-out run now also replaces the "I'm on it" PR comment with the failure note, instead of leaving it on the PR forever.
