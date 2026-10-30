"""Post the Slack message of the GitHub event that triggered the workflow to the person it concerns, in the direct
messages of a Slack app. `action.yml` runs it, and `events/` contains each event with its template.

The environment carries the event as GitHub sets it, in `GITHUB_EVENT_NAME` and `GITHUB_EVENT_PATH`, with
`GITHUB_REPOSITORY`, `GH_TOKEN`, which `gh` reads, and `SLACK_TOKEN`, the bot token of the app.
"""

import json
import os
import pathlib
import sys

from events import EVENTS
from github_api import GitHubApi, GitHubError
from notification import Inputs, Notification, Recipient, Skip
from slack import SlackClient, SlackError


def _notify(event_name: str, payload: dict, github: GitHubApi, slack: SlackClient, inputs: Inputs) -> int:
    # The exit code of the job is 1 when the action knows no such event, or GitHub or Slack refuses a call
    event = EVENTS.get(event_name)
    if not event:
        print(f"::error::the action sends no message for the event {event_name}")
        return 1
    try:
        notification = event.read(payload, github, inputs)
    except Skip as reason:
        print(f"::notice::{reason}, so nothing is posted")
        return 0
    except GitHubError as fault:
        print(f"::error::GitHub refused a read: {fault}")
        return 1
    posted = []
    if inputs.messages:
        refused = _update_all(slack, notification.recipients, inputs.messages)
    else:
        refused = _deliver(slack, notification, posted)
    _write_output(posted)
    return 1 if refused else 0


def _update_all(
    slack: SlackClient, recipients: tuple[Recipient, ...], messages: tuple[tuple[str, str, str], ...]
) -> bool:
    # A refusal for one person must not cost the others their summary
    by_login = {recipient.login: recipient for recipient in recipients}
    unknown, refused = [], False
    for channel, ts, login in messages:
        if login not in by_login:
            unknown.append(login)
            continue
        try:
            slack.update(channel, ts, by_login[login].message)
        except SlackError as fault:
            print(f"::error::Slack refused the call for {login}: {fault}")
            refused = True
    if unknown:
        print(f"::warning::the event gives no message for {', '.join(unknown)}, so their message stays as it is")
    return refused


def _deliver(slack: SlackClient, notification: Notification, posted: list[list[str]]) -> bool:
    # A refusal for one person must not cost the others their message
    without_email, without_member, refused = [], [], False
    for recipient in notification.recipients:
        if not recipient.emails:
            without_email.append(recipient.login)
            continue
        try:
            member = next(filter(None, (slack.find_member(email) for email in recipient.emails)), "")
            if not member:
                without_member.append(recipient.login)
            elif recipient.find:
                _restyle(slack, member, recipient)
            else:
                posted.append([*slack.post(member, recipient.message), recipient.login])
        except SlackError as fault:
            print(f"::error::Slack refused the call for {recipient.login}: {fault}")
            refused = True
    if without_email:
        print(
            f"::warning::no commit {notification.email_source} gives an email of {', '.join(without_email)},"
            " so nothing is posted"
        )
    if without_member:
        print(f"::warning::no Slack member has an email of {', '.join(without_member)}, so nothing is posted")
    return refused


def _restyle(slack: SlackClient, member: str, recipient: Recipient) -> None:
    # The new header and bar replace the old ones, and the body the person read stays
    found = slack.find_message(member, recipient.find)
    if not found:
        print("::notice::no message of the request to update")
        return
    channel, ts, blocks = found
    message = recipient.message
    slack.update(channel, ts, message._replace(blocks=[message.blocks[0], *blocks[1:]], metadata=recipient.find))


def _write_output(posted: list[list[str]]) -> None:
    if path := os.environ.get("GITHUB_OUTPUT"):
        with open(path, "a", encoding="utf-8") as output:
            output.write(f"messages={json.dumps(posted)}\n")


def _read_summary(path: str) -> dict | None:
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def main() -> int:
    payload = json.loads(pathlib.Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    github = GitHubApi(os.environ["GITHUB_REPOSITORY"])
    messages = tuple(map(tuple, json.loads(os.environ.get("SLACK_MESSAGES") or "[]")))
    inputs = Inputs(messages, _read_summary(os.environ.get("SUMMARY_FILE", "")))
    return _notify(os.environ["GITHUB_EVENT_NAME"], payload, github, SlackClient(os.environ["SLACK_TOKEN"]), inputs)


if __name__ == "__main__":
    sys.exit(main())
