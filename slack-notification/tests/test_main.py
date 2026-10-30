"""The action: the message of an event that it posts to the person the event concerns, and what it prints when
it posts nothing, when it knows no such event, or when Slack refuses a call."""

import io
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import main
from fakes import FakeGitHub, FakeSlack
from github_api import GitHubError
from slack import SlackError
from test_ci_checks_event import build_run as build_ci_run
from test_pull_request import build_pull

COMMIT = {"author": {"login": "a"}, "committer": None, "commit": {"author": {"email": "a@j.com"}}}


def build_run(actor):
    """A passed run on a pull request that `actor` triggered, as the event `workflow_run` carries it."""
    return build_ci_run("success") | {"triggering_actor": {"login": actor}}


class TestTheNotification(unittest.TestCase):
    def notify(self, run, commits, slack, event_name="workflow_run"):
        """GitHub returns `commits` for the pull request of `run`, and one job that passed. `event_name` triggers
        the workflow, whose event carries `run`. The result is the exit code and what the job printed."""
        github = FakeGitHub(
            {
                ("list_pull_commits", 42): commits,
                ("list_jobs", "1", 1): [{"id": 1, "name": "lint", "conclusion": "success", "html_url": "https://j/1"}],
                ("read_pull", 42): build_pull(),
            }
        )
        with mock.patch("sys.stdout", new_callable=io.StringIO) as output:
            code = main._notify(event_name, {"workflow_run": run}, github, slack)
        return code, output.getvalue()

    def test_the_person_who_triggered_the_run_receives_its_message(self):
        slack = FakeSlack({"a@j.com": "U1"})
        self.assertEqual(self.notify(build_run("a"), [COMMIT], slack), (0, ""))
        [(member, message)] = slack.posts
        self.assertEqual(member, "U1")
        self.assertEqual(message.fallback, "✅ CI checks passed · Jahia/sitemap#42")

    def test_the_message_goes_to_the_first_email_of_the_person_that_slack_knows(self):
        newer = COMMIT | {"commit": {"author": {"email": "a@laptop.local"}}}
        slack = FakeSlack({"a@j.com": "U1"})
        self.assertEqual(self.notify(build_run("a"), [COMMIT, newer], slack), (0, ""))
        self.assertEqual(slack.posts[0][0], "U1")

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
                code, output = self.notify(build_run("a") | change, [COMMIT], slack)
                self.assertEqual(code, 0)
                self.assertIn("::notice::the run is no completed run of a pull request", output)
                self.assertEqual(slack.posts, [])

    def test_a_person_with_no_email_in_the_pull_request_gets_a_warning_and_no_message(self):
        slack = FakeSlack({"a@j.com": "U1"})
        code, output = self.notify(build_run("someone"), [COMMIT], slack)
        self.assertEqual(code, 0)
        self.assertIn("::warning::no commit of the pull request gives an email of someone", output)
        self.assertEqual(slack.posts, [])

    def test_a_person_that_slack_does_not_know_gets_a_warning_and_no_message(self):
        slack = FakeSlack()
        code, output = self.notify(build_run("a"), [COMMIT], slack)
        self.assertEqual(code, 0)
        self.assertIn("::warning::no Slack member has an email of a", output)
        self.assertEqual(slack.posts, [])

    def test_an_event_that_the_action_does_not_know_fails_the_job(self):
        slack = FakeSlack({"a@j.com": "U1"})
        code, output = self.notify(build_run("a"), [COMMIT], slack, event_name="push")
        self.assertEqual(code, 1)
        self.assertIn("::error::the action sends no message for the event push", output)
        self.assertEqual(slack.posts, [])

    def test_a_read_of_github_that_fails_fails_the_job_with_what_gh_said(self):
        github = FakeGitHub({("list_jobs", "1", 1): GitHubError("gh api repos/x failed: HTTP 404")})
        with mock.patch("sys.stdout", new_callable=io.StringIO) as output:
            code = main._notify("workflow_run", {"workflow_run": build_run("a")}, github, FakeSlack())
        self.assertEqual(code, 1)
        self.assertIn("::error::GitHub refused a read: gh api repos/x failed: HTTP 404", output.getvalue())

    def test_a_refusal_of_slack_fails_the_job_with_its_error_code(self):
        code, output = self.notify(build_run("a"), [COMMIT], FakeSlack(refusal=SlackError("missing_scope")))
        self.assertEqual(code, 1)
        self.assertIn("::error::Slack refused the call: missing_scope", output)


if __name__ == "__main__":
    unittest.main()
