"""The events that the action sends a message for, keyed by the name of the GitHub event that triggers the
workflow. Each folder contains `event.py`, the data the event reads, `template.py`, the message built from it, and
`read` in its `__init__.py`, which takes the payload, GitHub and the `Inputs`, and returns the `Notification` or raises `Skip`."""

from events import ci_checks, review_requested, review_submitted

EVENTS = {
    "workflow_run": ci_checks,
    "pull_request_review": review_submitted,
    "pull_request_target": review_requested,
}
