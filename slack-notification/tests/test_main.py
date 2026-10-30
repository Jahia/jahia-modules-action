"""The action: the message of an event that it posts to the person the event concerns, and what it prints when
it posts nothing, when it knows no such event, or when Slack refuses a call."""

import io
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import main
from fakes import FakeGitHub, FakeSlack
from github_api import GitHubError
from notification import Inputs, Notification, Recipient
from slack import SlackError, SlackMessage
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
            code = main._notify(event_name, {"workflow_run": run}, github, slack, Inputs())
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
            code = main._notify("workflow_run", {"workflow_run": build_run("a")}, github, FakeSlack(), Inputs())
        self.assertEqual(code, 1)
        self.assertIn("::error::GitHub refused a read: gh api repos/x failed: HTTP 404", output.getvalue())

    def test_a_refusal_of_slack_fails_the_job_with_its_error_code(self):
        code, output = self.notify(build_run("a"), [COMMIT], FakeSlack(refusal=SlackError("missing_scope")))
        self.assertEqual(code, 1)
        self.assertIn("::error::Slack refused the call: missing_scope", output)


def build_message(*blocks, color="#2eb67d"):
    return SlackMessage(
        color, "fallback", list(blocks) or [{"h": 1}], metadata={"event_type": "e", "event_payload": {}}
    )


class TestTheRecipients(unittest.TestCase):
    def notify(self, notification, slack, inputs=None):
        """The event gives `notification`. The result is the exit code, what the job printed and the content of
        the file of the outputs."""
        event = mock.Mock(read=mock.Mock(return_value=notification))
        with (
            tempfile.TemporaryDirectory() as folder,
            mock.patch.dict(main.EVENTS, {"pull_request": event}),
            mock.patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            outputs = pathlib.Path(folder, "out")
            with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(outputs)}):
                code = main._notify("pull_request", {}, FakeGitHub({}), slack, inputs or Inputs())
            written = outputs.read_text() if outputs.exists() else ""
        return code, output.getvalue(), written

    def test_the_posts_write_the_list_of_their_messages_to_the_outputs(self):
        slack = FakeSlack({"a@j.com": "U1"})
        notification = Notification((Recipient("a", ["a@j.com"], build_message()),))
        self.assertEqual(self.notify(notification, slack), (0, "", 'messages=[["D1", "1.5"]]\n'))

    def test_input_messages_are_each_updated_and_nothing_is_posted(self):
        slack = FakeSlack({"a@j.com": "U1"})
        first, second = build_message({"n": 1}), build_message({"n": 2})
        notification = Notification((Recipient("a", ["a@j.com"], first), Recipient("b", ["b@j.com"], second)))
        code, output, _ = self.notify(notification, slack, Inputs(messages=(("D1", "1.5"), ("D2", "2.5"))))
        self.assertEqual((code, output, slack.posts), (0, "", []))
        self.assertEqual(slack.updates, [("D1", "1.5", first), ("D2", "2.5", second)])

    def test_input_messages_that_differ_in_count_from_the_recipients_state_a_warning(self):
        slack = FakeSlack()
        notification = Notification((Recipient("a", ["a@j.com"], build_message()),))
        code, output, _ = self.notify(notification, slack, Inputs(messages=(("D1", "1.5"), ("D2", "2.5"))))
        self.assertEqual(code, 0)
        self.assertIn("::warning::", output)
        self.assertEqual(len(slack.updates), 1)

    def test_a_recipient_with_no_email_is_named_in_one_warning_and_the_others_still_receive_the_message(self):
        slack = FakeSlack({"c@j.com": "U3"})
        notification = Notification(
            (
                Recipient("a", [], build_message()),
                Recipient("b", [], build_message()),
                Recipient("c", ["c@j.com"], build_message()),
            )
        )
        code, output, _ = self.notify(notification, slack)
        self.assertEqual(code, 0)
        self.assertEqual(output.count("::warning::"), 1)
        self.assertIn("an email of a, b,", output)
        self.assertEqual([member for member, _ in slack.posts], ["U3"])

    def test_a_notification_that_finds_a_message_restyles_its_header_and_its_bar_and_keeps_its_body(self):
        slack = FakeSlack({"a@j.com": "U1"})
        slack.found = ("D1", "1.5", [{"id": "header"}, {"id": "b1"}, {"id": "b2"}])
        find = {"event_type": "review_requested", "event_payload": {"pull": 1}}
        message = build_message({"id": "h2"}, color="#e01e5a")
        notification = Notification((Recipient("a", ["a@j.com"], message, find),))
        code, output, written = self.notify(notification, slack)
        self.assertEqual((code, output, slack.posts), (0, "", []))
        [(channel, ts, update)] = slack.updates
        self.assertEqual((channel, ts), ("D1", "1.5"))
        self.assertEqual(update.blocks, [{"id": "h2"}, {"id": "b1"}, {"id": "b2"}])
        self.assertEqual((update.color, update.metadata), ("#e01e5a", find))
        self.assertEqual(slack.finds, [("U1", find)])
        self.assertEqual(written, "messages=[]\n")

    def test_a_notification_that_finds_no_message_states_a_notice(self):
        slack = FakeSlack({"a@j.com": "U1"})
        find = {"event_type": "review_requested", "event_payload": {}}
        notification = Notification((Recipient("a", ["a@j.com"], build_message(), find),))
        code, output, _ = self.notify(notification, slack)
        self.assertEqual(code, 0)
        self.assertIn("::notice::no message of the request to update", output)
        self.assertEqual((slack.posts, slack.updates), ([], []))

    def test_an_approval_whose_message_is_not_in_the_direct_message_states_a_notice_and_updates_nothing(self):
        slack = FakeSlack({"rev@x.com": "U1"})
        commit = {"commit": {"author": {"email": "rev@x.com"}}}
        github = FakeGitHub({("list_author_commits", "rev"): [commit]})
        payload = {
            "review": {"state": "approved", "user": {"login": "rev"}},
            "pull_request": {"number": 42},
            "repository": {"full_name": "Jahia/sitemap"},
        }
        with mock.patch("sys.stdout", new_callable=io.StringIO) as output:
            code = main._notify("pull_request_review", payload, github, slack, Inputs())
        self.assertEqual(code, 0)
        self.assertIn("::notice::no message of the request to update", output.getvalue())
        self.assertEqual((slack.posts, slack.updates), ([], []))

    def test_a_reviewer_with_no_email_states_a_warning(self):
        notification = Notification((Recipient("a", [], build_message()),))
        code, output, _ = self.notify(notification, FakeSlack())
        self.assertEqual(code, 0)
        self.assertIn("::warning::no commit of the pull request gives an email of a", output)


if __name__ == "__main__":
    unittest.main()
