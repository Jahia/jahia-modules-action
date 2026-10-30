"""The data of a review request: the pull request, the reviewer, and the size of the change without its lock files
and generated files. `ReviewRequest.read` reads them, and `Summary` is the summary that an earlier step wrote."""

from typing import NamedTuple, Self

from github_api import GitHubApi
from notification import Skip
from pull_request import PullRequest

# The files that no person reviews: they count neither in the size nor in the files to start from
_GENERATED_NAMES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "uv.lock", "poetry.lock", "go.sum"}
_GENERATED_SUFFIXES = (".min.js", ".snap")
# The upper bound of the changed lines of each size, and the last size
_SIZES = ((10, "XS"), (100, "S"), (500, "M"), (1000, "L"))
_LAST_SIZE = "XL"
_MIN_MINUTES = 5
_FILES_SHOWN = 3
_BULLETS = 3
_BULLET_CHARS = 200


class ReviewFile(NamedTuple):
    path: str
    additions: int
    deletions: int


class Summary(NamedTuple):
    """The summary that an AI wrote: the bullets of the change, and the files to start from."""

    bullets: tuple[str, ...]
    files: tuple[str, ...] = ()

    @classmethod
    def parse(cls, data: object) -> Self | None:
        """The summary in `data`, which is any decoded JSON. Anything else than a dict of strings gives `None`."""
        if not isinstance(data, dict):
            return None
        bullets, files = data.get("bullets"), data.get("files", [])
        if not (isinstance(bullets, list) and isinstance(files, list)):
            return None
        if not all(isinstance(text, str) for text in [*bullets, *files]):
            return None
        return cls(tuple(text[:_BULLET_CHARS] for text in bullets[:_BULLETS]), tuple(files))


class ReviewRequest(NamedTuple):
    """A review requested from `reviewer`, a user or a team, at `reviewer_url`. `lines` counts the changed lines,
    `files` the ones with the most changed lines, and `more` the files that `files` leaves out."""

    pull: PullRequest
    reviewer: str
    reviewer_url: str
    lines: int
    files: tuple[ReviewFile, ...]
    more: int

    @property
    def size(self) -> str:
        return next((name for limit, name in _SIZES if self.lines < limit), _LAST_SIZE)

    @property
    def minutes(self) -> int:
        return max(_MIN_MINUTES, round(self.lines / 10))

    @classmethod
    def read(cls, payload: dict, github: GitHubApi) -> Self:
        """The request that `payload` carries. A review requested from a bot raises `Skip`."""
        pull = PullRequest.read(github, payload["pull_request"]["number"])
        if "requested_team" in payload:
            slug = payload["requested_team"]["slug"]
            owner = pull.repository.split("/")[0]
            reviewer, reviewer_url = f"@{owner}/{slug}", f"https://github.com/orgs/{owner}/teams/{slug}"
        else:
            user = payload["requested_reviewer"]
            if user["type"] == "Bot":
                raise Skip("the reviewer is a bot")
            reviewer, reviewer_url = user["login"], user["html_url"]
        changed = [
            ReviewFile(file["filename"], file["additions"], file["deletions"])
            for file in github.list_pull_files(pull.number)
            if not _is_generated(file["filename"])
        ]
        most = sorted(changed, key=lambda file: file.additions + file.deletions, reverse=True)
        lines = sum(file.additions + file.deletions for file in changed)
        return cls(pull, reviewer, reviewer_url, lines, tuple(most[:_FILES_SHOWN]), max(0, len(most) - _FILES_SHOWN))

    def find_members(self, payload: dict, github: GitHubApi) -> list[str]:
        """The logins that receive the request: the requested user, or the members of the requested team without
        the author of the pull request and the sender of the request."""
        if "requested_team" not in payload:
            return [self.reviewer]
        excluded = {self.pull.author, payload["sender"]["login"]}
        members = github.list_team_members(payload["requested_team"]["slug"])
        return [member["login"] for member in members if member["login"] not in excluded]


def _is_generated(path: str) -> bool:
    return path.rsplit("/", 1)[-1] in _GENERATED_NAMES or path.endswith(_GENERATED_SUFFIXES)
