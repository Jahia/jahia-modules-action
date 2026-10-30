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

# The conclusions of a run that carry no result for the person who triggered it
_NO_RESULT = {None, "cancelled", "skipped"}


def _find_email(commits: list[dict], login: str) -> str:
    # The profile email of an account is private, so the last commit linked to `login` gives it
    for commit in reversed(commits):
        for role in ("author", "committer"):
            if (commit.get(role) or {}).get("login") == login:
                return commit["commit"][role]["email"]
    return ""


def main() -> int:
    repository = os.environ["GITHUB_REPOSITORY"]
    run = GitHubApi.read_run(repository, os.environ["RUN_ID"])
    # A push to the branch of a pull request names that pull request too, and a run of a fork names none
    if run["event"] != "pull_request" or not run["pull_requests"] or run["conclusion"] in _NO_RESULT:
        print("::notice::the run is no completed run of a pull request, so nothing is posted")
        return 0
    actor = run["triggering_actor"]["login"]
    email = _find_email(GitHubApi.list_pull_commits(repository, run["pull_requests"][0]["number"]), actor)
    if not email:
        print(f"::warning::no commit of the pull request belongs to {actor}, so nothing is posted")
        return 0
    slack = SlackClient(os.environ["SLACK_TOKEN"])
    try:
        member = slack.find_member(email)
        if not member:
            print(f"::warning::no Slack member has the email of {actor}, so nothing is posted")
            return 0
        slack.post(member, ci_checks.render(CiChecks.read(run)))
    except SlackError as fault:
        print(f"::error::Slack refused the call: {fault}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
