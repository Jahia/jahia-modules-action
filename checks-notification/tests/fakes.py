"""The repository on GitHub that a test passes in place of `GitHubApi`."""


class FakeGitHub:
    """A repository that answers each read from `answers`, keyed by the name of the read and its arguments, such
    as `("list_jobs", "1")`. Any other read raises `KeyError`."""

    def __init__(self, answers: dict) -> None:
        self._answers = answers

    def __getattr__(self, read: str):
        return lambda *args: self._answers[(read, *args)]
