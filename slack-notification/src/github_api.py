"""The reads of GitHub that the notification makes through `gh api`: a pull request, the jobs of an attempt of a
run, the annotations and the log of a job, the commits of a pull request, the commits of an author in the organization, the check runs
of a commit, the reviews of a pull request, and the members of a team. A read that fails runs again, unless a
second call cannot change the refusal, and the last refusal raises `GitHubError`."""

import json
import re
import subprocess
import time
from typing import Any

# A read of GitHub fails on a network timeout now and then, and succeeds on the next call
_ATTEMPTS = 3
_RETRY_SECONDS = 5
# A refusal that a second call cannot change, so it raises at once
_FINAL_REFUSAL = re.compile(r"HTTP 4\d\d|unknown flag")
_PAGE = 100


class GitHubError(Exception):
    """A read that `gh` refused, with what `gh` printed."""


class GitHubApi:
    """The reads of one repository, named as `owner/name`."""

    def __init__(self, repo: str) -> None:
        self._repo = repo

    def read_pull(self, number: int) -> dict:
        return self._read_json(f"repos/{self._repo}/pulls/{number}")

    def list_jobs(self, run_id: str, attempt: int) -> list[dict]:
        """The jobs of one attempt of a run, from every page."""
        path = f"repos/{self._repo}/actions/runs/{run_id}/attempts/{attempt}/jobs?per_page={_PAGE}"
        return [job for page in self._read_json(path, "--paginate", "--slurp") for job in page["jobs"]]

    def list_annotations(self, job_id: str) -> list[dict]:
        """The annotations of a job, which GitHub serves under the check run of the same ID."""
        return self._read_json(f"repos/{self._repo}/check-runs/{job_id}/annotations?per_page={_PAGE}")

    def read_job_log(self, job_id: str) -> str:
        path = f"repos/{self._repo}/actions/jobs/{job_id}/logs"
        try:
            # gh prints the escape sequences of a log only with the flag, and the read of the log strips them
            return self._read(path, "--allow-escape-sequences")
        except GitHubError as refusal:
            # A gh that predates the flag refuses it, and prints the escape sequences without it
            if "unknown flag" not in str(refusal):
                raise
            return self._read(path)

    def list_pull_commits(self, number: int) -> list[dict]:
        """The commits of a pull request, oldest first."""
        pages = self._read_json(f"repos/{self._repo}/pulls/{number}/commits?per_page={_PAGE}", "--paginate", "--slurp")
        return [commit for page in pages for commit in page]

    def list_author_commits(self, login: str) -> list[dict]:
        """The newest commits of the organization of the repository whose author is `login`, from every repository
        of it that the token reads."""
        # ponytail: the search has a rate limit of its own per minute, which a large team request can reach
        owner = self._repo.split("/")[0]
        path = f"search/commits?q=author:{login}+org:{owner}&sort=author-date&order=desc&per_page=50"
        return self._read_json(path)["items"]

    def count_check_runs(self, sha: str) -> int:
        """The count of the check runs of the commit `sha`, as the tab Checks of a pull request shows it."""
        return self._read_json(f"repos/{self._repo}/commits/{sha}/check-runs?per_page=1")["total_count"]

    def list_pull_reviews(self, number: int) -> list[dict]:
        """The reviews of a pull request, oldest first, from every page."""
        pages = self._read_json(f"repos/{self._repo}/pulls/{number}/reviews?per_page={_PAGE}", "--paginate", "--slurp")
        return [review for page in pages for review in page]

    def list_team_members(self, slug: str) -> list[dict]:
        """The members of a team of the organization that owns the repository, from every page."""
        owner = self._repo.split("/")[0]
        pages = self._read_json(f"orgs/{owner}/teams/{slug}/members?per_page={_PAGE}", "--paginate", "--slurp")
        return [member for page in pages for member in page]

    @classmethod
    def _read_json(cls, path: str, *flags: str) -> Any:
        return json.loads(cls._read(path, *flags))

    @staticmethod
    def _read(path: str, *flags: str) -> str:
        error = ""
        for attempt in range(1, _ATTEMPTS + 1):
            result = subprocess.run(
                ["gh", "api", path, *flags], capture_output=True, encoding="utf-8", errors="replace", check=False
            )
            if result.returncode == 0:
                return result.stdout
            error = result.stderr.strip() or result.stdout.strip()
            if _FINAL_REFUSAL.search(error):
                break
            if attempt < _ATTEMPTS:
                time.sleep(_RETRY_SECONDS * attempt)
        raise GitHubError(f"gh api {path} failed: {error or 'no output'}")
