"""A read of GitHub runs again after a network fault, and raises at once on a refusal that a second call cannot
change, such as an HTTP 4xx."""

import pathlib
import subprocess
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import github_api
from github_api import GitHubApi, GitHubError

TIMEOUT = subprocess.CompletedProcess([], 1, "", "connection timed out")


class TestARead(unittest.TestCase):
    def answer(self, *answers):
        """`gh api` answers each call that reads the run below with the next of `answers`."""
        calls = iter(answers)

        def run(argv, **_):
            self.assertEqual(argv, ["gh", "api", "repos/Jahia/sitemap/actions/runs/7"])
            return next(calls)

        self.enterContext(mock.patch.object(github_api.subprocess, "run", run))
        return self.enterContext(mock.patch.object(github_api.time, "sleep"))

    def test_a_network_fault_runs_again_and_the_next_answer_counts(self):
        slept = self.answer(TIMEOUT, subprocess.CompletedProcess([], 0, '{"id": 7}', ""))
        self.assertEqual(GitHubApi("Jahia/sitemap").read_run("7"), {"id": 7})
        self.assertEqual(slept.call_count, 1)

    def test_the_third_fault_raises_what_gh_said(self):
        self.answer(TIMEOUT, TIMEOUT, TIMEOUT)
        with self.assertRaisesRegex(GitHubError, "connection timed out"):
            GitHubApi("Jahia/sitemap").read_run("7")

    def test_an_http_4xx_raises_at_once(self):
        slept = self.answer(subprocess.CompletedProcess([], 1, "", "gh: Not Found (HTTP 404)"))
        with self.assertRaisesRegex(GitHubError, "HTTP 404"):
            GitHubApi("Jahia/sitemap").read_run("7")
        self.assertEqual(slept.call_count, 0)


if __name__ == "__main__":
    unittest.main()
