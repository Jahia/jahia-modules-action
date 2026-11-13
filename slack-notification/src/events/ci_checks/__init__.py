"""The result of the checks of a pull request, which the person who triggered the run receives once the run
completes."""

import people
from github_api import GitHubApi
from notification import Inputs, Notification, Recipient

from events.ci_checks import template
from events.ci_checks.event import CiChecks


def read(payload: dict, github: GitHubApi, inputs: Inputs) -> Notification:
    """The message of the run that `payload`, the event `workflow_run`, carries, for the person who triggered it.
    A run that is no completed run of a pull request raises `Skip`. The run reads nothing of `inputs`."""
    run = payload["workflow_run"]
    checks = CiChecks.read(run, github)
    login = run["triggering_actor"]["login"]
    emails = people.find_emails(github, login, checks.pull.number)
    return Notification((Recipient(login, emails, template.render(checks)),))
