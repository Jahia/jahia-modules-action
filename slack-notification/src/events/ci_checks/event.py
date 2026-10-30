"""The checks of a completed run of GitHub Actions on a pull request: the count of its jobs, each failed job with
its failed step and its errors, and the jobs that passed only after a retry. `CiChecks.read` reads them through the
`GitHubApi` that the caller passes, and the README of the action states where the errors come from."""

import re
import time
from collections import Counter
from datetime import datetime
from enum import StrEnum
from typing import NamedTuple, Self

from github_api import GitHubApi
from notification import Skip
from pull_request import PullRequest

# The conclusions of a run that carry no result for the person who triggered it
_NO_RESULT = {None, "cancelled", "skipped"}
# The conclusions of a job that count neither as passed nor as failed, such as a job that fail-fast cancels
_UNCOUNTED = {"skipped", "neutral", "cancelled"}
# The lines of a log that the message shows, the last ones before the failure
_LOG_LINES = 3
# GitHub can send the event of a completed run before each of its jobs carries a conclusion
_SETTLE_READS = 6
_SETTLE_SECONDS = 10
# The annotation that the runner adds to each failed step, which names no error
_EXIT_CODE = re.compile(r"Process completed with exit code \d+\.?$")
# The timestamp that the runner writes before each line of a log, and the colors of a terminal
_TIMESTAMP = re.compile(r"^\d{4}-\d\d-\d\dT[\d:.]+Z ")
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
# The lines that Maven writes around a failure: its help, the resume of the build and the headings of its lists
_MAVEN_NOISE = re.compile(
    r"^(-> \[Help 1\]|\[Help 1\]|To see the full stack trace|Re-run Maven|For more information about the errors"
    r"|Please refer to |After correcting the problems|mvn .* -rf :|\w+:$)"
)
# The groups in parentheses that end the header of a unittest failure: its dotted path and its subtest
_TRAILING_GROUPS = re.compile(r"( \([^()]*\))+$")


class CiState(StrEnum):
    """The state of a completed run of the checks, which picks the message."""

    PASSED = "passed"
    UNSTABLE = "unstable"
    FAILED = "failed"


class CiError(NamedTuple):
    """An error of a failed job: the line that names it, its detail, the file and the line it points at with
    their URL, and how many equal errors it stands for."""

    title: str
    detail: str
    file: str = ""
    line: int = 0
    url: str = ""
    occurrences: int = 1

    @classmethod
    def _read_annotations(cls, annotations: list[dict], blob_url: str) -> list[Self]:
        # Each failure of a job, without the exit code of the runner, with the file it points at
        errors = []
        for one in annotations:
            if one["annotation_level"] != "failure" or _EXIT_CODE.search(one["message"].strip()):
                continue
            path, line = one.get("path") or "", one.get("start_line") or 0
            # An annotation that names no file points at `.github`, which is no place of the error
            if path == ".github":
                path, line = "", 0
            url = f"{blob_url}/{path}" + (f"#L{line}" if line else "") if path else ""
            errors.append(cls(_TRAILING_GROUPS.sub("", one.get("title") or ""), one["message"], path, line, url))
        return errors

    @classmethod
    def _read_log(cls, text: str) -> list[Self]:
        # The errors at the end of a log: the `[ERROR]` lines of the summary of Maven, else the last lines.
        lines = [_ANSI.sub("", _TIMESTAMP.sub("", line)).rstrip() for line in text.splitlines()]
        # The steps that run after a failure, such as the cleanup of a checkout, follow its last `##[error]` line
        failures = [index for index, line in enumerate(lines) if line.startswith("##[error]")]
        lines = lines[: failures[-1]] if failures else lines
        # The output of the failed step follows the last group where the runner echoes the script of a step
        starts = [index for index, line in enumerate(lines) if line.startswith("##[group]Run ")]
        if starts:
            ends = [index for index in range(starts[-1], len(lines)) if lines[index] == "##[endgroup]"]
            lines = lines[(ends[0] if ends else starts[-1]) + 1 :]
        lines = [line for line in lines if line and not line.startswith("##[") and not _EXIT_CODE.search(line)]
        # Maven ends on the results of the tests of the module that failed, or on the build failure alone
        marks = [index for index, line in enumerate(lines) if line in ("[INFO] Results:", "[INFO] BUILD FAILURE")]
        results = [index for index in marks if lines[index] == "[INFO] Results:"]
        if marks:
            start = results[-1] if results else marks[-1]
            maven = [line.removeprefix("[ERROR]").strip() for line in lines[start:] if line.startswith("[ERROR]")]
            maven = [line for line in maven if line and not _MAVEN_NOISE.match(line)]
            if maven:
                return [cls("", line) for line in maven]
        return [cls("", "\n".join(lines[-_LOG_LINES:]))] if lines else []


class CiJob(NamedTuple):
    """A job of the run. A failed job carries its failed step and its errors, and a job that passed only after
    a retry carries the step and the attempt that failed."""

    name: str
    url: str
    step: str = ""
    errors: tuple[CiError, ...] = ()
    failed_attempt: int = 0


class CiChecks(NamedTuple):
    """The data of a completed run of the checks, which the README of the action describes. `passed` counts
    the jobs that passed, the flaky ones included."""

    workflow: str
    conclusion: str
    pull: PullRequest
    commit: str
    commit_url: str
    attempt: int
    duration_seconds: int
    run_url: str
    passed: int
    failed: tuple[CiJob, ...] = ()
    flaky: tuple[CiJob, ...] = ()

    @property
    def state(self) -> CiState:
        if self.conclusion != "success":
            return CiState.FAILED
        return CiState.UNSTABLE if self.flaky else CiState.PASSED

    @staticmethod
    def _has_result(run: dict) -> bool:
        # A push to the branch of a pull request names that pull request too, and a run of a fork names none
        return run["event"] == "pull_request" and bool(run["pull_requests"]) and run["conclusion"] not in _NO_RESULT

    @classmethod
    def read(cls, run: dict, github: GitHubApi) -> Self:
        """The checks of `run`, the run that the event `workflow_run` carries, and of the jobs of its attempt. A run
        that is no completed run of a pull request raises `Skip`."""
        if not cls._has_result(run):
            raise Skip("the run is no completed run of a pull request")
        repository = run["repository"]
        run_id, attempt, sha = str(run["id"]), run["run_attempt"], run["head_sha"]
        number = run["pull_requests"][0]["number"]
        jobs = cls._list_settled_jobs(github, run_id, attempt)
        countable = [job for job in jobs if job["conclusion"] not in _UNCOUNTED]
        failed = [job for job in countable if cls._is_failed(job)]
        blob_url = f"{repository['html_url']}/blob/{sha}"
        errors = cls._collect_errors(github, failed, blob_url) if run["conclusion"] != "success" else {}
        earlier = github.list_jobs(run_id, attempt - 1) if attempt > 1 else []
        duration = datetime.fromisoformat(run["updated_at"]) - datetime.fromisoformat(run["run_started_at"])
        return cls(
            workflow=run["name"],
            conclusion=run["conclusion"],
            pull=PullRequest.read(github, number),
            commit=sha[:7],
            commit_url=f"{repository['html_url']}/commit/{sha}",
            attempt=attempt,
            duration_seconds=int(duration.total_seconds()),
            run_url=run["html_url"],
            passed=len(countable) - len(failed),
            failed=tuple(
                CiJob(job["name"], job["html_url"], cls._find_failed_step(job), cls._merge(errors.get(job["id"], [])))
                for job in failed
            ),
            flaky=cls._find_flaky(countable, earlier),
        )

    @staticmethod
    def _list_settled_jobs(github: GitHubApi, run_id: str, attempt: int) -> list[dict]:
        # A job with no conclusion would count as failed, so the jobs are read again until each one carries one
        for _ in range(_SETTLE_READS - 1):
            jobs = github.list_jobs(run_id, attempt)
            pending = [job["name"] for job in jobs if job["conclusion"] is None]
            if not pending:
                return jobs
            print(f"::notice::GitHub serves {', '.join(pending)} with no conclusion yet, so the jobs are read again")
            time.sleep(_SETTLE_SECONDS)
        return github.list_jobs(run_id, attempt)

    @staticmethod
    def _collect_errors(github: GitHubApi, failed: list[dict], blob_url: str) -> dict[int, list[CiError]]:
        # The errors of each failed job: its annotations, else the end of its log, such as in a Maven build
        return {
            job["id"]: CiError._read_annotations(github.list_annotations(str(job["id"])), blob_url)
            or CiError._read_log(github.read_job_log(str(job["id"])))
            for job in failed
        }

    @classmethod
    def _find_flaky(cls, jobs: list[dict], earlier: list[dict]) -> tuple[CiJob, ...]:
        # The jobs that passed in this attempt and failed in the previous one, with the step that failed there
        failed_before = {job["name"]: job for job in earlier if cls._is_failed(job)}
        return tuple(
            CiJob(
                job["name"],
                job["html_url"],
                cls._find_failed_step(failed_before[job["name"]]),
                (),
                failed_before[job["name"]]["run_attempt"],
            )
            for job in jobs
            if job["conclusion"] == "success" and job["name"] in failed_before
        )

    @staticmethod
    def _is_failed(job: dict) -> bool:
        # A job that timed out failed too, and the run counts it so
        return job["conclusion"] not in _UNCOUNTED and job["conclusion"] != "success"

    @staticmethod
    def _find_failed_step(job: dict) -> str:
        return next((step["name"] for step in job.get("steps", []) if step.get("conclusion") == "failure"), "")

    @staticmethod
    def _merge(errors: list[CiError]) -> tuple[CiError, ...]:
        # Equal errors, such as the subtests of one test, read as one error with its count of occurrences
        return tuple(error._replace(occurrences=count) for error, count in Counter(errors).items())
