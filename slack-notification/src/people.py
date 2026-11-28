"""The emails of a GitHub account, which Slack then reads to find the member."""

from github_api import GitHubApi

# The address that GitHub gives an account that hides its email, which no Slack member has
_NOREPLY = "@users.noreply.github.com"
# The commits that `find_author_emails` reads, as the warning of a person with no email names them
AUTHOR_COMMITS = "of the organization"


def find_author_emails(github: GitHubApi, login: str) -> list[str]:
    """The emails of the commits of the organization whose author is `login`, the newest first, without the
    address `users.noreply.github.com`."""
    emails = (commit["commit"]["author"]["email"] for commit in github.list_author_commits(login))
    return list(dict.fromkeys(email for email in emails if not email.endswith(_NOREPLY)))


def find_emails(github: GitHubApi, login: str, pull_number: int) -> list[str]:
    """The emails of the commits of the pull request that GitHub links to `login`, as their author or their
    committer, the last commit first, without the address `users.noreply.github.com`."""
    # The profile email of an account is private by default, so the commits give it
    emails = [
        commit["commit"][role]["email"]
        for commit in reversed(github.list_pull_commits(pull_number))
        for role in ("author", "committer")
        if (commit.get(role) or {}).get("login") == login
    ]
    return list(dict.fromkeys(email for email in emails if not email.endswith(_NOREPLY)))
