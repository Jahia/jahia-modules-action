"""The reads of GitHub that the notification makes through `gh api`: a run, its jobs, the jobs of an earlier
attempt, the annotations and the log of a job, and the commits of a pull request. A read that fails runs
again, unless a second call cannot change the refusal, and the last refusal raises `GitHubError`."""

import json
import re
import subprocess
import time
from typing import Any

# A read of GitHub fails on a network timeout now and then, and succeeds on the next call
_ATTEMPTS = 3
_RETRY_SECONDS = 5
# A refusal that a second call cannot change, so it raises at once
_FINAL_REFUSAL = re.compile(r"HTTP 4\d\d")
_PAGE = 100


class GitHubError(Exception):
    """A read that `gh` refused, with what `gh` printed."""


class GitHubApi:
    """The reads of one repository, named as `owner/name`."""

    def __init__(self, repo: str) -> None:
        self._repo = repo

    def read_run(self, run_id: str) -> dict:
        return self._read_json(f"repos/{self._repo}/actions/runs/{run_id}")

    def list_jobs(self, run_id: str) -> list[dict]:
        return self._read_json(f"repos/{self._repo}/actions/runs/{run_id}/jobs?per_page={_PAGE}")["jobs"]

    def list_attempt_jobs(self, run_id: str, attempt: int) -> list[dict]:
        """The jobs of one attempt of a run, where `list_jobs` reads its latest attempt."""
        return self._read_json(f"repos/{self._repo}/actions/runs/{run_id}/attempts/{attempt}/jobs?per_page={_PAGE}")[
            "jobs"
        ]

    def list_annotations(self, job_id: str) -> list[dict]:
        """The annotations of a job, which GitHub serves under the check run of the same ID."""
        return self._read_json(f"repos/{self._repo}/check-runs/{job_id}/annotations?per_page={_PAGE}")

    def read_job_log(self, job_id: str) -> str:
        # gh prints the escape sequences of a log only with the flag, and the read of the log strips them
        return self._read(f"repos/{self._repo}/actions/jobs/{job_id}/logs", "--allow-escape-sequences")

    def list_pull_commits(self, number: int) -> list[dict]:
        """The commits of a pull request, oldest first."""
        pages = self._read_json(f"repos/{self._repo}/pulls/{number}/commits?per_page={_PAGE}", "--paginate", "--slurp")
        return [commit for page in pages for commit in page]

    @classmethod
    def _read_json(cls, path: str, *flags: str) -> Any:
        return json.loads(cls._read(path, *flags))

    @staticmethod
    def _read(path: str, *flags: str) -> str:
        error = ""
        for attempt in range(1, _ATTEMPTS + 1):
            done = subprocess.run(
                ["gh", "api", path, *flags], capture_output=True, encoding="utf-8", errors="replace", check=False
            )
            if done.returncode == 0:
                return done.stdout
            error = done.stderr.strip() or done.stdout.strip()
            if _FINAL_REFUSAL.search(error):
                break
            if attempt < _ATTEMPTS:
                time.sleep(_RETRY_SECONDS * attempt)
        raise GitHubError(f"gh api {path} failed: {error or 'no output'}")
