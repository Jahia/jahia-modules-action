"""A pull request, as its page on GitHub shows it, which every event of a pull request reads."""

from typing import NamedTuple, Self

from github_api import GitHubApi


class PullRequest(NamedTuple):
    """A pull request and its repository. `state` is `open`, `draft`, `merged` or `closed`."""

    repository: str
    repository_url: str
    number: int
    title: str
    url: str
    state: str
    author: str
    author_url: str
    commits: int
    base: str
    head: str

    @property
    def reference(self) -> str:
        return f"{self.repository}#{self.number}"

    @classmethod
    def read(cls, github: GitHubApi, number: int) -> Self:
        """The pull request `number` of `github`."""
        pull = github.read_pull(number)
        # A draft that closes reads as closed, as its page on GitHub shows it
        state = (
            "merged"
            if pull.get("merged_at")
            else "draft"
            if pull.get("draft") and pull["state"] == "open"
            else pull["state"]
        )
        return cls(
            repository=pull["base"]["repo"]["full_name"],
            repository_url=pull["base"]["repo"]["html_url"],
            number=pull["number"],
            title=pull["title"],
            url=pull["html_url"],
            state=state,
            author=pull["user"]["login"],
            author_url=pull["user"]["html_url"],
            commits=pull["commits"],
            base=pull["base"]["ref"],
            head=pull["head"]["ref"],
        )
