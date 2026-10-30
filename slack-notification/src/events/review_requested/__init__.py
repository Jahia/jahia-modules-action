"""The request of a review on a pull request, which the requested reviewer, or each member of the requested team,
receives with the context of the review."""

import people
from github_api import GitHubApi
from notification import Inputs, Notification, Recipient, Skip

from events.review_requested import template
from events.review_requested.event import ReviewRequest, Summary


def read(payload: dict, github: GitHubApi, inputs: Inputs) -> Notification:
    """The message of the review that `payload`, the event `pull_request_target`, requests. Another action, and a
    review requested from a bot, raise `Skip`. A team request gives each member but the author and the sender."""
    if payload["action"] != "review_requested":
        raise Skip("the action is no review request")
    request = ReviewRequest.read(payload, github)
    summary, pending = Summary.parse(inputs.summary), not inputs.messages
    members = request.find_members(payload, github)
    return Notification(
        tuple(
            Recipient(
                member, people.find_author_emails(github, member), template.render(request, member, summary, pending)
            )
            for member in members
        )
    )
