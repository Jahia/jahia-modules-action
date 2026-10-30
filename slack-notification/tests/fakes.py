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
    """A repository that answers each read from `answers`, keyed by the name of the read and its arguments, such
    as `("list_jobs", "1")`. An answer that is an error is raised, and any other read raises `KeyError`."""

    def __init__(self, answers: dict) -> None:
        self._answers = answers

    def __getattr__(self, read: str):
        if not hasattr(GitHubApi, read):
            raise AttributeError(f"GitHubApi has no read {read}")
        return lambda *args: self._raise_or_return(self._answers[(read, *args)])

    @staticmethod
    def _raise_or_return(answer):
        # An answer that is an error is what the read raises
        if isinstance(answer, Exception):
            raise answer
        return answer
