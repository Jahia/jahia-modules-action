"""The data of a review request: the pull request, the reviewer, and the counts that the tabs of the pull request
show on GitHub. `ReviewRequest.read` reads them, and `Summary` is the summary that an earlier step wrote."""

from typing import NamedTuple, Self

from github_api import GitHubApi
from notification import Skip
from pull_request import PullRequest

_BULLETS = 3
_BULLET_CHARS = 200
# The states of a review that decide; a comment or a pending review leaves the decision before it standing
_VERDICTS = {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}


class Summary(NamedTuple):
    bullets: tuple[str, ...]

    @classmethod
    def parse(cls, data: object) -> Self | None:
        """The summary in `data`, which is any decoded JSON. A value that is no dict with a list of strings under
        `bullets`, or has no bullet, gives `None`."""
        bullets = data.get("bullets") if isinstance(data, dict) else None
        if not (isinstance(bullets, list) and all(isinstance(text, str) for text in bullets)):
            return None
        # A summary with no bullet says nothing, so it reads as no summary
        if not bullets:
            return None
        return cls(tuple(text[:_BULLET_CHARS] for text in bullets[:_BULLETS]))


class ReviewRequest(NamedTuple):
    """A review requested from `reviewer`, the login of a user or the name of a team, with the counts that the
    tabs of the pull request show: its comments, its check runs, its changed files and its changed lines."""

    pull: PullRequest
    reviewer: str
    comments: int
    checks: int
    files: int
    additions: int
    deletions: int

    @classmethod
    def read(cls, payload: dict, github: GitHubApi) -> Self:
        """The request that `payload` carries. A review requested from a bot raises `Skip`."""
        if "requested_team" in payload:
            reviewer = payload["requested_team"]["slug"]
        else:
            user = payload["requested_reviewer"]
            if user["type"] == "Bot":
                raise Skip("the reviewer is a bot")
            reviewer = user["login"]
        data = github.read_pull(payload["pull_request"]["number"])
        return cls(
            PullRequest.parse(data),
            reviewer,
            # The tab Conversation counts the comments of the pull request and those of its reviews
            data["comments"] + data["review_comments"],
            github.count_check_runs(data["head"]["sha"]),
            data["changed_files"],
            data["additions"],
            data["deletions"],
        )

    def find_members(self, payload: dict, github: GitHubApi) -> list[str]:
        """The logins that receive the request: the requested user, or the members of the requested team without
        the author of the pull request and the sender of the request."""
        if "requested_team" not in payload:
            return [self.reviewer]
        excluded = {self.pull.author, payload["sender"]["login"]}
        members = github.list_team_members(payload["requested_team"]["slug"])
        return [member["login"] for member in members if member["login"] not in excluded]

    def find_verdicts(self, github: GitHubApi) -> dict[str, str]:
        """The state of the latest review of the pull request that decides, for each login that made one."""
        latest = {}
        for review in github.list_pull_reviews(self.pull.number):
            # A deleted account leaves its reviews with no user
            if review["user"] and review["state"] in _VERDICTS:
                latest[review["user"]["login"]] = review["state"]
        return latest
