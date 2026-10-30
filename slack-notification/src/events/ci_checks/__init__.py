"""The result of the checks of a pull request, which the person who triggered the run receives once the run
completes."""

from github_api import GitHubApi
from notification import Notification

from events.ci_checks import template
from events.ci_checks.event import CiChecks


def read(payload: dict, github: GitHubApi) -> Notification:
    """The message of the run that `payload`, the event `workflow_run`, carries, for the person who triggered it.
    A run that is no completed run of a pull request raises `Skip`."""
    run = payload["workflow_run"]
    checks = CiChecks.read(run, github)
    return Notification(run["triggering_actor"]["login"], checks.pull.number, template.render(checks))
