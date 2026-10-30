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
    """The recipients of one event. `email_source` names the commits that give their emails, which a warning
    states, such as `of the pull request`."""

    recipients: tuple[Recipient, ...]
    email_source: str = "of the pull request"


class Inputs(NamedTuple):
    """What the caller of the action passes: the `channel`, the `ts` and the login of the person of each message
    to update, and the summary that an earlier step wrote."""

    messages: tuple[tuple[str, str, str], ...] = ()
    summary: dict | None = None


class Skip(Exception):
    """The event carries nothing to send, for the reason that its text states."""
