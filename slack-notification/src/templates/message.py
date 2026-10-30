"""The skeleton of every message: the header of the event, then the body and the detail that the template of
the event builds."""

from blocks import build_header
from slack import SlackMessage


def compose(
    color: str,
    emoji: str,
    icon: str,
    title: str,
    subject: str,
    body: list[dict],
    detail: list[dict] | tuple = (),
    thread: tuple = (),
) -> SlackMessage:
    """The message that opens on the header `title` behind `emoji`, then shows `body`, and `detail` on a bar of
    `color`. The system shows `icon`, `title` and `subject`, the thing the message is about, such as a pull
    request."""
    blocks = [build_header(f"{emoji} {title}"), *body]
    return SlackMessage(color, f"{icon} {title} · {subject}", blocks, tuple(detail), thread)
