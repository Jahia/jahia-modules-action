"""A read of GitHub runs again after a network fault, and raises at once on a refusal that a second call cannot
change, such as an HTTP 4xx. A log reads again without the flag that an older `gh` does not know, and the jobs of
an attempt come from every page."""

import pathlib
import subprocess
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import github_api
from github_api import GitHubApi, GitHubError

TIMEOUT = subprocess.CompletedProcess([], 1, "", "connection timed out")
PULL = ["gh", "api", "repos/Jahia/sitemap/pulls/7"]


class TestARead(unittest.TestCase):
    def serve(self, *results):
        """`gh api` returns the next of `results` for each call, and the test keeps the arguments of each call."""
        self.calls = []
        results = iter(results)

        def run(argv, **_):
            self.calls.append(argv)
            return next(results)

        self.enterContext(mock.patch.object(github_api.subprocess, "run", run))
        return self.enterContext(mock.patch.object(github_api.time, "sleep"))

    def test_a_network_fault_runs_again_and_the_next_result_counts(self):
        sleep = self.serve(TIMEOUT, subprocess.CompletedProcess([], 0, '{"id": 7}', ""))
        self.assertEqual(GitHubApi("Jahia/sitemap").read_pull(7), {"id": 7})
        self.assertEqual(self.calls, [PULL, PULL])
        self.assertEqual(sleep.call_count, 1)

    def test_the_third_fault_raises_what_gh_said(self):
        self.serve(TIMEOUT, TIMEOUT, TIMEOUT)
        with self.assertRaisesRegex(GitHubError, "connection timed out"):
            GitHubApi("Jahia/sitemap").read_pull(7)

    def test_an_http_4xx_raises_at_once(self):
        sleep = self.serve(subprocess.CompletedProcess([], 1, "", "gh: Not Found (HTTP 404)"))
        with self.assertRaisesRegex(GitHubError, "HTTP 404"):
            GitHubApi("Jahia/sitemap").read_pull(7)
        self.assertEqual(sleep.call_count, 0)

    def test_a_gh_that_does_not_know_the_flag_of_a_log_reads_it_without_the_flag(self):
        unknown = subprocess.CompletedProcess([], 1, "", "unknown flag: --allow-escape-sequences")
        sleep = self.serve(unknown, subprocess.CompletedProcess([], 0, "log", ""))
        self.assertEqual(GitHubApi("Jahia/sitemap").read_job_log("9"), "log")
        path = "repos/Jahia/sitemap/actions/jobs/9/logs"
        self.assertEqual(self.calls, [["gh", "api", path, "--allow-escape-sequences"], ["gh", "api", path]])
        self.assertEqual(sleep.call_count, 0)

    def test_the_jobs_of_an_attempt_come_from_every_page(self):
        self.serve(subprocess.CompletedProcess([], 0, '[{"jobs": [{"id": 1}]}, {"jobs": [{"id": 2}]}]', ""))
        self.assertEqual(GitHubApi("Jahia/sitemap").list_jobs("7", 2), [{"id": 1}, {"id": 2}])
        self.assertEqual(
            self.calls[0][2:],
            ["repos/Jahia/sitemap/actions/runs/7/attempts/2/jobs?per_page=100", "--paginate", "--slurp"],
        )

    def test_the_reviews_of_a_pull_request_come_from_every_page(self):
        self.serve(subprocess.CompletedProcess([], 0, '[[{"id": 1}], [{"id": 2}]]', ""))
        self.assertEqual(GitHubApi("Jahia/sitemap").list_pull_reviews(42), [{"id": 1}, {"id": 2}])
        self.assertEqual(
            self.calls[0][2:], ["repos/Jahia/sitemap/pulls/42/reviews?per_page=100", "--paginate", "--slurp"]
        )


if __name__ == "__main__":
    unittest.main()
