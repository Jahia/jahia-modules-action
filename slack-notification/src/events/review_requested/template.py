"""The message of a review request: the pull request, the counts of its tabs on GitHub, and the summary of the
change. The summary reads as in progress until the AI step answers, and an approval turns the header and the bar."""

from blocks import build_buttons, build_context, build_section, escape
from slack import SlackMessage
from templates import message, pull_request

from events.review_requested.event import ReviewRequest, Summary

_REQUESTED = ("#1D9BD1", ":eye:", "👀", "Review requested")
APPROVED = ("#2EB67D", ":white_check_mark:", "✅", "Approved")
_IN_PROGRESS = "_Summary in progress…_"
_NO_SUMMARY = "_No summary, see the pull request_"


def render(
    request: ReviewRequest, member: str, summary: Summary | None, pending: bool, approved: bool = False
) -> SlackMessage:
    """The message of `request` for `member`, the person who receives it. With `approved`, it opens on the header
    and the bar of the approval of `member`."""
    pull = request.pull
    body = [
        *pull_request.show(pull),
        build_context(_show_counts(request)),
        build_section(f"*What the pull request changes*\n{_show_summary(summary, pending)}"),
        build_buttons(("Review on GitHub", f"{pull.url}/files")),
    ]
    metadata = build_metadata(pull.repository, pull.number, member)
    header = APPROVED if approved else _REQUESTED
    return message.compose(*header, pull.reference, body, metadata=metadata)


def build_metadata(repository: str, number: int, member: str) -> dict:
    """The Slack metadata of the request that `member` receives, which the approval finds the message by."""
    return {
        "event_type": "review_requested",
        "event_payload": {"repository": repository, "number": number, "reviewer": member},
    }


def _show_counts(request: ReviewRequest) -> str:
    # The tabs of the pull request on GitHub, in their order, each count a link to its tab as the run line of
    # ci_checks links its commit
    url = request.pull.url
    return "   |   ".join(
        [
            f"Conversation (<{url}|{request.comments}>)",
            _count("Commit", "Commits", request.pull.commits, f"{url}/commits"),
            _count("Check", "Checks", request.checks, f"{url}/checks"),
            _count("File changed", "Files changed", request.files, f"{url}/files"),
            f"+{request.additions} −{request.deletions}",
        ]
    )


def _count(one: str, many: str, value: int, url: str) -> str:
    return f"{one if value == 1 else many} (<{url}|{value}>)"


def _show_summary(summary: Summary | None, pending: bool) -> str:
    if summary:
        return "\n".join(f"• {escape(bullet)}" for bullet in summary.bullets)
    return _IN_PROGRESS if pending else _NO_SUMMARY
