"""The repository on GitHub and the workspace of Slack that a test passes in place of `GitHubApi` and
`SlackClient`."""

from github_api import GitHubApi


class FakeSlack:
    """A workspace whose members are `members`, keyed by their email, and which keeps each message it posts.
    `refusal` is the error that a call raises, if any."""

    def __init__(self, members: dict | None = None, refusal: Exception | None = None) -> None:
        self.members = members or {}
        self.refusal = refusal
        self.posts = []

    def find_member(self, email: str) -> str:
        if self.refusal:
            raise self.refusal
        return self.members.get(email, "")

    def post(self, channel: str, message) -> None:
        self.posts.append((channel, message))


class FakeGitHub:
    """A repository that returns each read from `results`, keyed by the name of the read and its arguments, such
    as `("list_jobs", "1", 1)`. A result that is an error is raised, and any other read raises `KeyError`."""

    def __init__(self, results: dict) -> None:
        self._results = results

    def __getattr__(self, name: str):
        if not hasattr(GitHubApi, name):
            raise AttributeError(f"GitHubApi has no read {name}")
        return lambda *args: self._raise_or_return(self._results[(name, *args)])

    @staticmethod
    def _raise_or_return(result):
        # A result that is an error is what the read raises
        if isinstance(result, Exception):
            raise result
        return result
