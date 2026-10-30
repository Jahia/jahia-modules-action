"""The checks of a completed run of GitHub Actions on a pull request: the count of its jobs, each failed job with
its failed step and its errors, and the jobs that passed only after a retry. `CiChecks.read` reads them through
`GitHubApi`, and the README of the action states where the errors come from."""

import re
from collections import Counter
from datetime import datetime
from enum import StrEnum
from typing import NamedTuple, Self

from github_api import GitHubApi

# The conclusions of a run that carry no result for the person who triggered it
_NO_RESULT = {None, "cancelled", "skipped"}
# The conclusions of a job that count neither as passed nor as failed
_UNCOUNTED = {"skipped", "neutral"}
_LOG_LINES = 10
# The annotation that the runner adds to each failed step, which names no error
_EXIT_CODE = re.compile(r"Process completed with exit code \d+\.?$")
# The timestamp that the runner writes before each line of a log, and the colors of a terminal
_TIMESTAMP = re.compile(r"^\d{4}-\d\d-\d\dT[\d:.]+Z ")
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
# The lines that Maven writes under every failure, and the headings of its lists
_MAVEN_NOISE = re.compile(
    r"^(-> \[Help 1\]|\[Help 1\]|To see the full stack trace|Re-run Maven|For more information about the errors|Please refer to |\w+:$)"
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
    reference: str
    pull_title: str
    pull_url: str
    branch: str
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
    def has_result(run: dict) -> bool:
        """Whether `run` is a completed run of a pull request, the one run that `read` reads."""
        # A push to the branch of a pull request names that pull request too, and a run of a fork names none
        return run["event"] == "pull_request" and bool(run["pull_requests"]) and run["conclusion"] not in _NO_RESULT

    @classmethod
    def read(cls, run: dict) -> Self:
        """The checks of `run`, a completed run on a pull request as `GitHubApi.read_run` returns it."""
        repository = run["repository"]
        name, run_id, attempt, sha = repository["full_name"], str(run["id"]), run["run_attempt"], run["head_sha"]
        number = run["pull_requests"][0]["number"]
        countable = [job for job in GitHubApi.list_jobs(name, run_id) if job["conclusion"] not in _UNCOUNTED]
        failed = [job for job in countable if cls._is_failed(job)]
        blob_url = f"{repository['html_url']}/blob/{sha}"
        errors = cls._collect_errors(name, failed, blob_url) if run["conclusion"] != "success" else {}
        earlier = GitHubApi.list_attempt_jobs(name, run_id, attempt - 1) if attempt > 1 else []
        elapsed = datetime.fromisoformat(run["updated_at"]) - datetime.fromisoformat(run["run_started_at"])
        return cls(
            workflow=run["name"],
            conclusion=run["conclusion"],
            reference=f"{name}#{number}",
            pull_title=run["display_title"],
            pull_url=f"{repository['html_url']}/pull/{number}",
            branch=run["head_branch"],
            commit=sha[:7],
            commit_url=f"{repository['html_url']}/commit/{sha}",
            attempt=attempt,
            duration_seconds=int(elapsed.total_seconds()),
            run_url=run["html_url"],
            passed=len(countable) - len(failed),
            failed=tuple(
                CiJob(job["name"], job["html_url"], cls._find_failed_step(job), cls._merge(errors.get(job["id"], [])))
                for job in failed
            ),
            flaky=cls._find_flaky(countable, earlier),
        )

    @classmethod
    def _collect_errors(cls, repository: str, failed: list[dict], blob_url: str) -> dict[int, list[CiError]]:
        # The errors of each failed job: their annotations, else the end of their logs
        errors = {
            job["id"]: CiError._read_annotations(GitHubApi.list_annotations(repository, str(job["id"])), blob_url)
            for job in failed
        }
        if any(errors.values()):
            return errors
        # A run whose failed jobs write no annotation, such as a Maven build, leaves its errors in their logs
        return {job["id"]: CiError._read_log(GitHubApi.read_job_log(repository, str(job["id"]))) for job in failed}

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
        # A job that timed out or was cancelled failed too, and the run counts it so
        return job["conclusion"] not in _UNCOUNTED and job["conclusion"] != "success"

    @staticmethod
    def _find_failed_step(job: dict) -> str:
        return next((step["name"] for step in job.get("steps", []) if step.get("conclusion") == "failure"), "")

    @staticmethod
    def _merge(errors: list[CiError]) -> tuple[CiError, ...]:
        # Equal errors, such as the subtests of one test, read as one error with its count of occurrences
        return tuple(error._replace(occurrences=count) for error, count in Counter(errors).items())
