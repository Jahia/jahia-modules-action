---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

The AI PR review now narrates itself live in the GitHub Actions log, like any build or test step, instead of showing nothing until the agent is done. Each event is printed as it arrives — elapsed time, then what the agent is thinking, which tool it is running, whether the call succeeded, which call a permission rule denied, and when the model gateway is rate-limiting and for how long — plus a heartbeat when a single thought runs longer than a minute. The raw `review.stream.jsonl` is still written verbatim for the artifact, and the post-run trace is no longer replayed since the log already carries it.
