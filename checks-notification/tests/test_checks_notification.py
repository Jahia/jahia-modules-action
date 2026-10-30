"""The script: the email of the person who triggered the run, and what it prints when it posts nothing or when
Slack refuses a call."""

import io
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import checks_notification
from github_api import GitHubApi
from slack import SlackClient, SlackError

ENVIRONMENT = {"GITHUB_REPOSITORY": "Jahia/sitemap", "RUN_ID": "1", "SLACK_TOKEN": "t"}


def build_run(actor):
    """A completed run on a pull request that `actor` triggered, with the fields that the script reads itself."""
    return {
        "id": 1,
        "event": "pull_request",
        "status": "completed",
        "conclusion": "success",
        "triggering_actor": {"login": actor},
        "pull_requests": [{"number": 42}],
    }


class TestTheEmailOfThePerson(unittest.TestCase):
    def test_the_last_commit_linked_to_the_login_as_author_or_committer_gives_the_email(self):
        commits = [
            {"author": {"login": "a"}, "committer": {"login": "a"}, "commit": {"author": {"email": "a1@j.com"}}},
            {"author": None, "committer": {"login": "a"}, "commit": {"committer": {"email": "a2@j.com"}}},
            {"author": {"login": "b"}, "committer": {"login": "b"}, "commit": {"author": {"email": "b@j.com"}}},
        ]
        self.assertEqual(checks_notification._find_email(commits, "a"), "a2@j.com")
        self.assertEqual(checks_notification._find_email(commits, "b"), "b@j.com")
        self.assertEqual(checks_notification._find_email(commits, "c"), "")


class TestTheMain(unittest.TestCase):
    def answer(self, run, commits):
        """GitHub holds `run` and the commits of its pull request, and answers no other read."""
        self.enterContext(mock.patch.dict(os.environ, ENVIRONMENT))
        self.enterContext(mock.patch.object(GitHubApi, "read_run", lambda github, run_id: {"1": run}[run_id]))
        self.enterContext(
            mock.patch.object(GitHubApi, "list_pull_commits", lambda github, number: {42: commits}[number])
        )

    def test_a_run_that_is_no_completed_run_of_a_pull_request_posts_nothing(self):
        """A caller may run the action on every completed run, so the action skips the runs with no result for a
        person, rather than the `if:` of each caller."""
        cases = {
            "a push": {"event": "push"},
            "a run of a fork, which names no pull request": {"pull_requests": []},
            "a cancelled run": {"conclusion": "cancelled"},
            "a skipped run": {"conclusion": "skipped"},
            "a run in progress": {"status": "in_progress", "conclusion": None},
        }
        for case, change in cases.items():
            with self.subTest(case), mock.patch("sys.stdout", new_callable=io.StringIO) as out:
                self.answer(build_run("a") | change, [])
                self.assertEqual(checks_notification.main(), 0)
                self.assertIn("::notice::the run is no completed run of a pull request", out.getvalue())

    def test_a_person_with_no_commit_in_the_pull_request_gets_a_warning_and_no_message(self):
        self.answer(build_run("someone"), [])
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertEqual(checks_notification.main(), 0)
        self.assertIn("::warning::no commit of the pull request belongs to someone", out.getvalue())

    def test_a_person_that_slack_does_not_know_gets_a_warning_and_no_message(self):
        commit = {"author": {"login": "a"}, "committer": None, "commit": {"author": {"email": "a@j.com"}}}
        self.answer(build_run("a"), [commit])
        self.enterContext(mock.patch.object(SlackClient, "find_member", lambda self, email: ""))
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertEqual(checks_notification.main(), 0)
        self.assertIn("::warning::no Slack member has the email of a", out.getvalue())

    def test_a_refusal_of_slack_fails_the_job_with_its_error_code(self):
        commit = {"author": {"login": "a"}, "committer": None, "commit": {"author": {"email": "a@j.com"}}}
        self.answer(build_run("a"), [commit])
        self.enterContext(mock.patch.object(SlackClient, "find_member", side_effect=SlackError("missing_scope")))
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertEqual(checks_notification.main(), 1)
        self.assertIn("::error::Slack refused the call: missing_scope", out.getvalue())


if __name__ == "__main__":
    unittest.main()
