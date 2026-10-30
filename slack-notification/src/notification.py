"""What the event of a folder of `events/` gives to `main.py`: the message and the person who receives it, or
the reason to send nothing."""

from typing import NamedTuple

from slack import SlackMessage


class Notification(NamedTuple):
    """A message for one person: their GitHub login, and the pull request whose commits give their email."""

    login: str
    pull_number: int
    message: SlackMessage


class Skip(Exception):
    """The event carries nothing to send, for the reason that its text states."""
