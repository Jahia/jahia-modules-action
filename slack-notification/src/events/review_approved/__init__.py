"""The approval of a review, which turns the message of the review request of its reviewer to approved."""

import people
from github_api import GitHubApi
from notification import Inputs, Notification, Recipient, Skip
from templates import message

from events.review_requested.template import build_metadata


def read(payload: dict, github: GitHubApi, inputs: Inputs) -> Notification:
    """The new header of the request that `payload`, the event `pull_request_review`, approves. A review that is
    no approval raises `Skip`."""
    if payload["review"]["state"] != "approved":
        raise Skip("the review is no approval")
    reviewer = payload["review"]["user"]["login"]
    repository, number = payload["repository"]["full_name"], payload["pull_request"]["number"]
    find = build_metadata(repository, number, reviewer)
    header = message.compose("#2EB67D", ":white_check_mark:", "✅", "Approved", f"{repository}#{number}", [])
    return Notification((Recipient(reviewer, people.find_author_emails(github, reviewer), header, find),))
