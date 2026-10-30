"""The skeleton of every message: the header of the event, then the body that the template of the event builds."""

from blocks import build_header
from slack import SlackMessage


def compose(
    color: str, emoji: str, icon: str, title: str, subject: str, body: list[dict], thread: tuple = ()
) -> SlackMessage:
    """The message on a bar of `color`, which opens on the header `title` behind `emoji`, then `body`. The system
    shows `icon`, `title` and `subject`, the thing the message is about, such as a pull request."""
    return SlackMessage(color, f"{icon} {title} · {subject}", [build_header(f"{emoji} {title}"), *body], thread)
