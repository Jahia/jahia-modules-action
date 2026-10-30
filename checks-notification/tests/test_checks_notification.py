"""The script: the email of the person who triggered the run, the message it posts to that person, and what it
prints when it posts nothing or when Slack refuses a call."""

import io
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import checks_notification
from fakes import FakeGitHub, FakeSlack
from slack import SlackError

COMMIT = {"author": {"login": "a"}, "committer": None, "commit": {"author": {"email": "a@j.com"}}}


def build_run(actor):
    """A completed run on a pull request that `actor` triggered, as the REST API of GitHub returns it."""
    return {
        "id": 1,
        "name": "Validate",
        "event": "pull_request",
        "status": "completed",
        "conclusion": "success",
        "triggering_actor": {"login": actor},
        "repository": {"full_name": "Jahia/sitemap", "html_url": "https://github.com/Jahia/sitemap"},
        "pull_requests": [{"number": 42}],
        "head_sha": "ec06bccb1fc1f819899a22fa08223da38b4310a6",
        "head_branch": "feat/x",
        "run_attempt": 1,
        "run_started_at": "2026-10-27T09:29:29Z",
        "updated_at": "2026-10-27T09:30:56Z",
        "display_title": "feat: x",
        "html_url": "https://github.com/Jahia/sitemap/actions/runs/1",
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


class TestTheNotification(unittest.TestCase):
    def notify(self, run, commits, slack):
        """GitHub holds `run`, the commits of its pull request and one job that passed, and answers no other
        read. The result holds the exit code and what the job printed."""
        github = FakeGitHub(
            {
                ("read_run", "1"): run,
                ("list_pull_commits", 42): commits,
                ("list_jobs", "1"): [{"id": 1, "name": "lint", "conclusion": "success", "html_url": "https://j/1"}],
            }
        )
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            code = checks_notification.notify(github, slack, "1")
        return code, out.getvalue()

    def test_the_person_who_triggered_the_run_receives_its_message(self):
        slack = FakeSlack({"a@j.com": "U1"})
        self.assertEqual(self.notify(build_run("a"), [COMMIT], slack), (0, ""))
        [(member, message)] = slack.posts
        self.assertEqual(member, "U1")
        self.assertEqual(message.fallback, "✅ CI checks passed · 1 of 1 jobs · Jahia/sitemap#42")

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
            with self.subTest(case):
                slack = FakeSlack({"a@j.com": "U1"})
                code, printed = self.notify(build_run("a") | change, [COMMIT], slack)
                self.assertEqual(code, 0)
                self.assertIn("::notice::the run is no completed run of a pull request", printed)
                self.assertEqual(slack.posts, [])

    def test_a_person_with_no_commit_in_the_pull_request_gets_a_warning_and_no_message(self):
        slack = FakeSlack({"a@j.com": "U1"})
        code, printed = self.notify(build_run("someone"), [COMMIT], slack)
        self.assertEqual(code, 0)
        self.assertIn("::warning::no commit of the pull request belongs to someone", printed)
        self.assertEqual(slack.posts, [])

    def test_a_person_that_slack_does_not_know_gets_a_warning_and_no_message(self):
        slack = FakeSlack()
        code, printed = self.notify(build_run("a"), [COMMIT], slack)
        self.assertEqual(code, 0)
        self.assertIn("::warning::no Slack member has the email of a", printed)
        self.assertEqual(slack.posts, [])

    def test_a_refusal_of_slack_fails_the_job_with_its_error_code(self):
        code, printed = self.notify(build_run("a"), [COMMIT], FakeSlack(refusal=SlackError("missing_scope")))
        self.assertEqual(code, 1)
        self.assertIn("::error::Slack refused the call: missing_scope", printed)


if __name__ == "__main__":
    unittest.main()
