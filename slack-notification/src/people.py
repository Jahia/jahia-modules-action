"""The email of a GitHub account, which Slack then reads to find the member."""

from github_api import GitHubApi


def find_email(github: GitHubApi, login: str, pull_number: int) -> str:
    """The email of the last commit of the pull request that GitHub links to `login`, as its author or its
    committer, empty when no commit is linked to it."""
    # The profile email of an account is private, so a commit gives it
    for commit in reversed(github.list_pull_commits(pull_number)):
        for role in ("author", "committer"):
            if (commit.get(role) or {}).get("login") == login:
                return commit["commit"][role]["email"]
    return ""
