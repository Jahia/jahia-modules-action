"""Post the Slack message of the GitHub event that triggered the workflow to the person it concerns, in the direct
messages of a Slack app. `action.yml` runs it, and `events/` contains each event with its template.

The environment carries the event as GitHub sets it, in `GITHUB_EVENT_NAME` and `GITHUB_EVENT_PATH`, with
`GITHUB_REPOSITORY`, `GH_TOKEN`, which `gh` reads, and `SLACK_TOKEN`, the bot token of the app.
"""

import json
import os
import pathlib
import sys

import people
from events import EVENTS
from github_api import GitHubApi, GitHubError
from notification import Skip
from slack import SlackClient, SlackError


def _notify(event_name: str, payload: dict, github: GitHubApi, slack: SlackClient) -> int:
    # The exit code of the job is 1 when the action knows no such event, or GitHub or Slack refuses a call
    event = EVENTS.get(event_name)
    if not event:
        print(f"::error::the action sends no message for the event {event_name}")
        return 1
    try:
        notification = event.read(payload, github)
        login = notification.login
        emails = people.find_emails(github, login, notification.pull_number)
    except Skip as reason:
        print(f"::notice::{reason}, so nothing is posted")
        return 0
    except GitHubError as fault:
        print(f"::error::GitHub refused a read: {fault}")
        return 1
    if not emails:
        print(f"::warning::no commit of the pull request gives an email of {login}, so nothing is posted")
        return 0
    try:
        member = next(filter(None, (slack.find_member(email) for email in emails)), "")
        if not member:
            print(f"::warning::no Slack member has an email of {login}, so nothing is posted")
            return 0
        slack.post(member, notification.message)
    except SlackError as fault:
        print(f"::error::Slack refused the call: {fault}")
        return 1
    return 0


def main() -> int:
    payload = json.loads(pathlib.Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    github = GitHubApi(os.environ["GITHUB_REPOSITORY"])
    return _notify(os.environ["GITHUB_EVENT_NAME"], payload, github, SlackClient(os.environ["SLACK_TOKEN"]))


if __name__ == "__main__":
    sys.exit(main())
