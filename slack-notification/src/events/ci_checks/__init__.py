"""The result of the checks of a pull request, which the person who triggered the run receives once the run
completes."""

from github_api import GitHubApi
from notification import Notification, Skip

from events.ci_checks import template
from events.ci_checks.event import CiChecks


def read(payload: dict, github: GitHubApi) -> Notification:
    """The message of the run that `payload`, the event `workflow_run`, names, for the person who triggered it."""
    run = github.read_run(str(payload["workflow_run"]["id"]))
    if not CiChecks.has_result(run):
        raise Skip("the run is no completed run of a pull request")
    message = template.render(CiChecks.read(run, github))
    return Notification(run["triggering_actor"]["login"], run["pull_requests"][0]["number"], message)
