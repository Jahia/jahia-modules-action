"""The request of a review on a pull request, which the requested reviewer, or each member of the requested team,
receives with the context of the review."""

import people
from github_api import GitHubApi, GitHubError
from notification import Inputs, Notification, Recipient, Skip

from events.review_requested import template
from events.review_requested.event import ReviewRequest, Summary


def read(payload: dict, github: GitHubApi, inputs: Inputs) -> Notification:
    """The message of the review that `payload`, the event `pull_request_target`, requests. Another action, and a
    review requested from a bot, raise `Skip`. A team request gives each member but the author and the sender, and
    an update, with `inputs.messages`, writes to the logins of its messages and reads no email."""
    if payload["action"] != "review_requested":
        raise Skip("the action is no review request")
    request = ReviewRequest.read(payload, github)
    summary, updating = Summary.parse(inputs.summary), bool(inputs.messages)
    # The job of the summary skips a fork, so its message shows no summary at once
    head = payload["pull_request"]["head"]["repo"] or {}
    pending = not updating and head.get("full_name") == payload["repository"]["full_name"]
    if updating:
        # The ts of a Slack message is the time of its post, in seconds
        posted = {login: float(ts) for _, ts, login in inputs.messages}
        members, verdicts = list(posted), request.find_verdicts(github, posted)
    else:
        members, verdicts = request.find_members(payload, github), {}
    recipients = []
    for member in members:
        emails, fault = [], ""
        if not updating:
            try:
                emails = people.find_author_emails(github, member)
            except GitHubError as refusal:
                # A refusal for one member must not cost the others their message
                fault = str(refusal)
        message = template.render(request, member, summary, pending, verdicts.get(member))
        recipients.append(Recipient(member, emails, message, fault=fault))
    return Notification(tuple(recipients), people.AUTHOR_COMMITS)
