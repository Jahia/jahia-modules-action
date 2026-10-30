"""The request of a review on a pull request, which the requested reviewer, or each member of the requested team,
receives with the context of the review."""

import people
from github_api import GitHubApi
from notification import Inputs, Notification, Recipient, Skip

from events.review_requested import template
from events.review_requested.event import ReviewRequest, Summary


def read(payload: dict, github: GitHubApi, inputs: Inputs) -> Notification:
    """The message of the review that `payload`, the event `pull_request_target`, requests. Another action, and a
    review requested from a bot, raise `Skip`. A team request gives each member but the author and the sender. An
    update, with `inputs.messages`, reads no email, and a member whose latest review decides gets its header."""
    if payload["action"] != "review_requested":
        raise Skip("the action is no review request")
    request = ReviewRequest.read(payload, github)
    summary, updating = Summary.parse(inputs.summary), bool(inputs.messages)
    members = request.find_members(payload, github)
    # The update runs minutes after the request, so a member may have reviewed in between
    verdicts = request.find_verdicts(github) if updating else {}
    return Notification(
        tuple(
            Recipient(
                member,
                # The update writes to the messages it is given, so it needs no email
                [] if updating else people.find_author_emails(github, member),
                template.render(request, member, summary, not updating, verdicts.get(member)),
            )
            for member in members
        ),
        people.AUTHOR_COMMITS,
    )
