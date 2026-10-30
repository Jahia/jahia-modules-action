"""The message of a review request: the pull request, its size, the summary of the change, and the files to start
from. The summary reads as in progress until the AI step answers, and an approval turns the header and the bar."""

from blocks import build_buttons, build_context, build_section, escape
from slack import SlackMessage
from templates import message, pull_request

from events.review_requested.event import ReviewFile, ReviewRequest, Summary

_REQUESTED = ("#1D9BD1", ":eye:", "👀", "Review requested")
APPROVED = ("#2EB67D", ":white_check_mark:", "✅", "Approved")
_SQUARES = 5
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
        build_context(
            f"For <{request.reviewer_url}|{escape(request.reviewer)}> · size {request.size}"
            f" · ~{request.minutes} min to review"
        ),
        build_section(f"*What the pull request changes*\n{_show_summary(summary, pending)}"),
    ]
    if request.files:
        body.append(build_section(f"*Where to start*\n{_show_files(request, summary)}"))
    body.append(build_buttons(("Review on GitHub", f"{pull.url}/files")))
    metadata = build_metadata(pull.repository, pull.number, member)
    header = APPROVED if approved else _REQUESTED
    return message.compose(*header, pull.reference, body, metadata=metadata)


def build_metadata(repository: str, number: int, member: str) -> dict:
    """The Slack metadata of the request that `member` receives, which the approval finds the message by."""
    return {
        "event_type": "review_requested",
        "event_payload": {"repository": repository, "number": number, "reviewer": member},
    }


def _show_summary(summary: Summary | None, pending: bool) -> str:
    if summary:
        return "\n".join(f"• {escape(bullet)}" for bullet in summary.bullets)
    return _IN_PROGRESS if pending else _NO_SUMMARY


def _show_files(request: ReviewRequest, summary: Summary | None) -> str:
    files = request.files
    if summary:
        # The AI orders the files only when each one it names is a file of the request
        known = {file.path: file for file in files}
        if summary.files and all(path in known for path in summary.files):
            files = tuple(known[path] for path in summary.files)
    lines = [_show_file(file) for file in files]
    if request.more:
        lines.append(f"+ {request.more} more files")
    return "\n".join(lines)


def _show_file(file: ReviewFile) -> str:
    total = file.additions + file.deletions
    green = round(_SQUARES * file.additions / total) if total else 0
    squares = ":large_green_square:" * green + ":large_red_square:" * (_SQUARES - green)
    return f"{escape(file.path)}   +{file.additions} −{file.deletions}   {squares}"
