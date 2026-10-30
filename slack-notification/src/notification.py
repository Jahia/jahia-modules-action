"""What the event of a folder of `events/` gives to `main.py`: the messages and the people who receive them, or
the reason to send nothing."""

from typing import NamedTuple

from slack import SlackMessage


class Recipient(NamedTuple):
    """A message for one person: their GitHub login, their emails and the message. With `find`, the metadata of an
    earlier message, `main.py` restyles that message instead of posting a new one."""

    login: str
    emails: list[str]
    message: SlackMessage
    find: dict | None = None


class Notification(NamedTuple):
    """The recipients of one event."""

    recipients: tuple[Recipient, ...]


class Inputs(NamedTuple):
    """What the caller of the action passes: the `channel` and `ts` of the messages to update, and the summary
    that an earlier step wrote."""

    messages: tuple[tuple[str, str], ...] = ()
    summary: dict | None = None


class Skip(Exception):
    """The event carries nothing to send, for the reason that its text states."""
