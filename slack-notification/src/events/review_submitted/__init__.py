"""A review that decides, which turns the message of the review request of its reviewer to approved, or to
changes requested."""

import people
from github_api import GitHubApi
from notification import Inputs, Notification, Recipient, Skip
from templates import message

from events.review_requested.template import VERDICTS, build_metadata


def read(payload: dict, github: GitHubApi, inputs: Inputs) -> Notification:
    """The new header of the request that `payload`, the event `pull_request_review`, decides. A review that
    neither approves nor requests changes raises `Skip`."""
    # The event writes the state in lower case, and the REST API of the reviews in upper case
    state = payload["review"]["state"].upper()
    if state not in VERDICTS:
        raise Skip("the review neither approves nor requests changes")
    reviewer = payload["review"]["user"]["login"]
    repository, number = payload["repository"]["full_name"], payload["pull_request"]["number"]
    find = build_metadata(repository, number, reviewer)
    header = message.compose(*VERDICTS[state], f"{repository}#{number}", [])
    recipient = Recipient(reviewer, people.find_author_emails(github, reviewer), header, find)
    return Notification((recipient,), people.AUTHOR_COMMITS)
