"""Post the result of a completed run on a pull request to the person who triggered the run, in the direct
messages of a Slack app. `action.yml` runs it. `CiChecks` reads the run, and the template `ci_checks` turns it
into the message that the README of the action states.

The environment names the run with `GITHUB_REPOSITORY` and `RUN_ID`, and carries `GH_TOKEN`, which `gh`
reads, and `SLACK_TOKEN`, the bot token of the app.
"""

import os
import sys

import ci_checks
from checks_run import CiChecks
from github_api import GitHubApi
from slack import SlackClient, SlackError


def _find_email(commits: list[dict], login: str) -> str:
    # The profile email of an account is private, so the last commit linked to `login` gives it
    for commit in reversed(commits):
        for role in ("author", "committer"):
            if (commit.get(role) or {}).get("login") == login:
                return commit["commit"][role]["email"]
    return ""


def notify(github: GitHubApi, slack: SlackClient, run_id: str) -> int:
    """Post the message of the run `run_id` of `github` to the person who triggered it, through `slack`, and
    return the exit code of the job: 1 when Slack refuses a call, 0 otherwise."""
    run = github.read_run(run_id)
    if not CiChecks.has_result(run):
        print("::notice::the run is no completed run of a pull request, so nothing is posted")
        return 0
    actor = run["triggering_actor"]["login"]
    email = _find_email(github.list_pull_commits(run["pull_requests"][0]["number"]), actor)
    if not email:
        print(f"::warning::no commit of the pull request belongs to {actor}, so nothing is posted")
        return 0
    try:
        member = slack.find_member(email)
        if not member:
            print(f"::warning::no Slack member has the email of {actor}, so nothing is posted")
            return 0
        slack.post(member, ci_checks.render(CiChecks.read(run, github)))
    except SlackError as fault:
        print(f"::error::Slack refused the call: {fault}")
        return 1
    return 0


def main() -> int:
    github = GitHubApi(os.environ["GITHUB_REPOSITORY"])
    return notify(github, SlackClient(os.environ["SLACK_TOKEN"]), os.environ["RUN_ID"])


if __name__ == "__main__":
    sys.exit(main())
