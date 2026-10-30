"""The checks that `CiChecks.read` reads from a completed run: the count of its jobs, the errors of each failed
job, and the jobs that passed only after a retry."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from events.ci_checks.event import CiChecks, CiError, CiJob
from fakes import FakeGitHub
from test_pull_request import build_pull

REPO = "Jahia/sitemap"
BLOB = "https://github.com/Jahia/sitemap/blob/ec06bccb1fc1f819899a22fa08223da38b4310a6"


def build_run(conclusion, attempt=1):
    """A completed run of `Validate` on a pull request, as the REST API of GitHub returns it."""
    return {
        "id": 1,
        "name": "Validate",
        "event": "pull_request",
        "conclusion": conclusion,
        "repository": {"full_name": REPO, "html_url": "https://github.com/Jahia/sitemap"},
        "pull_requests": [{"number": 42}],
        "head_sha": "ec06bccb1fc1f819899a22fa08223da38b4310a6",
        "head_branch": "feat/x",
        "run_attempt": attempt,
        "run_started_at": "2026-10-27T09:29:29Z",
        "updated_at": "2026-10-27T09:30:56Z",
        "display_title": "feat: x",
        "html_url": "https://github.com/Jahia/sitemap/actions/runs/1",
    }


def build_job(job_id, name, conclusion, failed_step="", attempt=1):
    steps = [{"name": failed_step, "conclusion": "failure"}] if failed_step else []
    return {
        "id": job_id,
        "name": name,
        "conclusion": conclusion,
        "html_url": f"https://j/{job_id}",
        "steps": steps,
        "run_attempt": attempt,
    }


def build_annotation(message, title="", path=".github", line=None):
    return {"annotation_level": "failure", "title": title, "message": message, "path": path, "start_line": line}


class RunOnGitHub(unittest.TestCase):
    def read(self, run, jobs, annotations=None, logs=None, earlier=None):
        """GitHub returns these jobs for the attempt of the run, the annotations and the log of each job by its
        ID, and the jobs of the previous attempt."""
        attempt = run["run_attempt"]
        github = FakeGitHub(
            {
                ("read_pull", 42): build_pull(),
                ("list_jobs", "1", attempt): jobs,
                ("list_jobs", "1", attempt - 1): earlier or [],
                **{("list_annotations", str(key)): value for key, value in (annotations or {}).items()},
                **{("read_job_log", str(key)): value for key, value in (logs or {}).items()},
            }
        )
        return CiChecks.read(run, github)


class TestTheChecksOfARun(RunOnGitHub):
    def test_a_failed_run_counts_its_jobs_and_merges_the_equal_errors_of_each_failed_job(self):
        jobs = [
            build_job(1, "lint 0/6", "success"),
            build_job(2, "lint 2/6", "failure", "Run the checks"),
            build_job(3, "skip", "skipped"),
        ]
        annotation = build_annotation("KeyError: 'K'", "test_x", "t.py", 87)
        checks = self.read(build_run("failure"), jobs, annotations={2: [annotation, annotation]})
        self.assertEqual(
            (checks.pull.reference, checks.commit, checks.attempt, checks.duration_seconds, checks.passed),
            ("Jahia/sitemap#42", "ec06bcc", 1, 87, 1),
        )
        error = CiError("test_x", "KeyError: 'K'", "t.py", 87, f"{BLOB}/t.py#L87", 2)
        self.assertEqual(checks.failed, (CiJob("lint 2/6", "https://j/2", "Run the checks", (error,)),))
        self.assertEqual((checks.state, checks.flaky), ("failed", ()))

    def test_a_job_that_timed_out_counts_as_failed_and_gives_its_annotations(self):
        jobs = [build_job(7, "slow", "timed_out"), build_job(8, "lint", "success")]
        timeout = build_annotation("The job exceeded the maximum time.")
        checks = self.read(build_run("failure"), jobs, annotations={7: [timeout]})
        self.assertEqual(checks.failed, (CiJob("slow", "https://j/7", "", (CiError("", timeout["message"]),)),))

    def test_a_cancelled_job_counts_neither_as_passed_nor_as_failed(self):
        jobs = [build_job(1, "a", "failure"), build_job(2, "b", "cancelled"), build_job(3, "c", "success")]
        checks = self.read(build_run("failure"), jobs, annotations={1: [build_annotation("boom")]})
        self.assertEqual((checks.passed, [job.name for job in checks.failed]), (1, ["a"]))

    def test_a_job_that_failed_in_the_previous_attempt_and_passed_in_this_one_is_flaky(self):
        jobs = [build_job(1, "lint 0/6", "success"), build_job(2, "lint 2/6", "success", attempt=2)]
        earlier = [build_job(11, "lint 0/6", "success"), build_job(12, "lint 2/6", "failure", "Run the checks")]
        checks = self.read(build_run("success", attempt=2), jobs, earlier=earlier)
        self.assertEqual(checks.flaky, (CiJob("lint 2/6", "https://j/2", "Run the checks", (), 1),))
        self.assertEqual(checks.state, "unstable")

    def test_a_new_attempt_with_no_job_that_failed_before_stays_passed(self):
        jobs = [build_job(1, "lint", "success", attempt=2)]
        checks = self.read(build_run("success", attempt=2), jobs, earlier=[build_job(11, "lint", "success")])
        self.assertEqual(checks.state, "passed")


class TestTheErrorsOfAFailedJob(RunOnGitHub):
    def read_errors(self, annotations, log=None):
        """The errors of the one failed job of a run, whose annotations and log GitHub returns."""
        logs = {2: log} if log is not None else None
        jobs = [build_job(1, "lint", "success"), build_job(2, "build", "failure")]
        return self.read(build_run("failure"), jobs, annotations={2: annotations}, logs=logs).failed[0].errors

    def test_the_annotations_keep_each_failure_with_its_file_but_the_exit_code_and_the_trailing_groups(self):
        annotations = [
            {"annotation_level": "warning", "title": "", "message": "Node.js 20 is deprecated.", "path": ".github"},
            build_annotation("Process completed with exit code 1."),
            build_annotation(
                "KeyError: 'K'",
                "src [19/26] ERROR test_x (notification.test_y.TestZ.test_x) (value='off')",
                "src/tests/test_y.py",
                84,
            ),
            build_annotation("a bare failure", line=1) | {"title": None},
        ]
        self.assertEqual(
            self.read_errors(annotations),
            (
                CiError(
                    "src [19/26] ERROR test_x",
                    "KeyError: 'K'",
                    "src/tests/test_y.py",
                    84,
                    f"{BLOB}/src/tests/test_y.py#L84",
                ),
                CiError("", "a bare failure"),
            ),
        )

    def test_the_log_gives_the_errors_of_a_failed_job_with_no_annotation_beside_a_job_with_annotations(self):
        jobs = [build_job(1, "lint", "failure"), build_job(2, "build", "failure")]
        log = "[INFO] BUILD FAILURE\n[ERROR] Failed to execute goal x"
        annotations = {1: [build_annotation("KeyError: 'K'")], 2: []}
        checks = self.read(build_run("failure"), jobs, annotations=annotations, logs={2: log})
        self.assertEqual(
            [job.errors for job in checks.failed],
            [(CiError("", "KeyError: 'K'"),), (CiError("", "Failed to execute goal x"),)],
        )

    def test_a_log_keeps_the_output_of_the_failed_step_alone(self):
        lines = [
            "Current runner version: '2.329.0'",
            "##[group]Run make",
            "make",
            "shell: /usr/bin/bash -e {0}",
            "##[endgroup]",
            "make: *** [all] Error 2",
            "##[error]Process completed with exit code 2.",
        ]
        self.assertEqual(self.read_errors([], "\n".join(lines)), (CiError("", "make: *** [all] Error 2"),))

    def test_a_failed_step_with_no_output_gives_no_error(self):
        lines = [
            "Complete job name: lint",
            '##[group]Run test "$RESULT" = success',
            'test "$RESULT" = success',
            "env:",
            "  RESULT: failure",
            "##[endgroup]",
            "##[error]Process completed with exit code 1.",
        ]
        self.assertEqual(self.read_errors([], "\n".join(lines)), ())

    def test_a_maven_log_gives_the_error_lines_of_its_last_results(self):
        lines = [
            "2026-10-27T09:29:29.1234567Z [INFO] Results:",
            "2026-10-27T09:29:29.1234567Z [INFO] Tests run: 3, Failures: 0",
            "2026-10-27T09:29:30.1234567Z [INFO] Results:",
            "2026-10-27T09:29:30.1234567Z [ERROR] Failures: ",
            "2026-10-27T09:29:30.1234567Z [ERROR]   FooTest.bar:42 expected:<1> but was:<2>",
            "2026-10-27T09:29:30.1234567Z [ERROR] Tests run: 12, Failures: 1, Errors: 0, Skipped: 0",
            "2026-10-27T09:29:31.1234567Z [INFO] \x1b[1;31mBUILD FAILURE\x1b[m",
            "2026-10-27T09:29:31.1234567Z [ERROR] Failed to execute goal surefire:test on project foo",
            "2026-10-27T09:29:31.1234567Z [ERROR] ",
            "2026-10-27T09:29:31.1234567Z [ERROR] To see the full stack trace of the errors, re-run Maven with the -e switch.",
            "2026-10-27T09:29:31.1234567Z [ERROR] -> [Help 1]",
            "2026-10-27T09:29:31.1234567Z ##[error]Process completed with exit code 1.",
        ]
        self.assertEqual(
            self.read_errors([], "\n".join(lines)),
            (
                CiError("", "FooTest.bar:42 expected:<1> but was:<2>"),
                CiError("", "Tests run: 12, Failures: 1, Errors: 0, Skipped: 0"),
                CiError("", "Failed to execute goal surefire:test on project foo"),
            ),
        )

    def test_another_log_gives_its_last_three_lines_without_the_lines_of_the_runner(self):
        lines = [f"2026-10-27T09:29:29.1234567Z line {n}" for n in range(15)]
        log = "\n".join(["##[group]Run make", *lines, "##[error]Process completed with exit code 2."])
        self.assertEqual(self.read_errors([], log), (CiError("", "\n".join(f"line {n}" for n in range(12, 15))),))

    def test_a_log_ends_at_its_last_error_before_the_steps_that_clean_up(self):
        lines = [
            "##[group]Run make",
            "make: *** [all] Error 2",
            "##[error]Process completed with exit code 2.",
            "Post job cleanup.",
            "[command]/usr/bin/git version",
            "Cleaning up orphan processes",
        ]
        log = "\n".join(lines)
        self.assertEqual(self.read_errors([], log), (CiError("", "make: *** [all] Error 2"),))

    def test_a_maven_log_drops_the_lines_that_resume_the_build(self):
        lines = [
            "[INFO] BUILD FAILURE",
            "[ERROR] Failed to execute goal surefire:test on project foo",
            "[ERROR] After correcting the problems, you can resume the build with the command",
            "[ERROR]   mvn <args> -rf :foo",
        ]
        self.assertEqual(
            self.read_errors([], "\n".join(lines)),
            (CiError("", "Failed to execute goal surefire:test on project foo"),),
        )

    def test_an_empty_log_gives_no_error(self):
        self.assertEqual(self.read_errors([], ""), ())


if __name__ == "__main__":
    unittest.main()
