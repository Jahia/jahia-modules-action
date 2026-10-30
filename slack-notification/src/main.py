"""Post the Slack message of the GitHub event that triggered the workflow to the person it concerns, in the direct
messages of a Slack app. `action.yml` runs it, and `events/` holds each event with its template.

The environment carries the event as GitHub sets it, in `GITHUB_EVENT_NAME` and `GITHUB_EVENT_PATH`, with
`GITHUB_REPOSITORY`, `GH_TOKEN`, which `gh` reads, and `SLACK_TOKEN`, the bot token of the app.
"""

import json
import os
import sys

import people
from events import EVENTS
from github_api import GitHubApi, GitHubError
from notification import Skip
from slack import SlackClient, SlackError


def notify(event_name: str, payload: dict, github: GitHubApi, slack: SlackClient) -> int:
    """Post the message of the event `event_name`, whose data is `payload`, and return the exit code of the job:
    1 when the action knows no such event, or GitHub or Slack refuses a call, 0 otherwise."""
    event = EVENTS.get(event_name)
    if not event:
        print(f"::error::the action sends no message for the event {event_name}")
        return 1
    try:
        notification = event.read(payload, github)
        login = notification.login
        email = people.find_email(github, login, notification.pull_number)
    except Skip as reason:
        print(f"::notice::{reason}, so nothing is posted")
        return 0
    except GitHubError as fault:
        print(f"::error::GitHub refused a read: {fault}")
        return 1
    if not email:
        print(f"::warning::no commit of the pull request belongs to {login}, so nothing is posted")
        return 0
    try:
        member = slack.find_member(email)
        if not member:
            print(f"::warning::no Slack member has the email of {login}, so nothing is posted")
            return 0
        slack.post(member, notification.message)
    except SlackError as fault:
        print(f"::error::Slack refused the call: {fault}")
        return 1
    return 0


def main() -> int:
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as file:
        payload = json.load(file)
    github = GitHubApi(os.environ["GITHUB_REPOSITORY"])
    return notify(os.environ["GITHUB_EVENT_NAME"], payload, github, SlackClient(os.environ["SLACK_TOKEN"]))


if __name__ == "__main__":
    sys.exit(main())
