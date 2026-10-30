"""The review request that `ReviewRequest.read` reads from the event, the counts of its tabs, and the summary of
the AI."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import events
from events import review_requested
from events.review_requested.event import ReviewRequest, Summary
from fakes import FakeGitHub
from github_api import GitHubError
from notification import Inputs, Skip
from test_pull_request import build_pull

SUMMARY = {"bullets": ["The sitemap lists the drafts"]}


def build_payload(**changes):
    payload = {
        "action": "review_requested",
        "pull_request": {"number": 42},
        "requested_reviewer": {"login": "rev", "type": "User", "html_url": "https://github.com/rev"},
        "sender": {"login": "dev"},
    }
    return payload | changes


def build_github(members=(), extra=None):
    results = {("read_pull", 42): build_pull(), ("count_check_runs", "abc"): 6}
    results |= {("list_team_members", "core"): [{"login": login} for login in members]}
    results |= {("list_author_commits", login): [] for login in ("rev", *members)}
    return FakeGitHub(results | (extra or {}))


class TestTheReviewRequest(unittest.TestCase):
    def test_an_event_is_registered_for_pull_request_target(self):
        self.assertIs(events.EVENTS["pull_request_target"], review_requested)

    def test_another_action_and_a_bot_reviewer_raise_skip(self):
        github = build_github()
        with self.assertRaises(Skip):
            review_requested.read(build_payload(action="opened"), github, Inputs())
        bot = {"login": "bot", "type": "Bot", "html_url": "x"}
        with self.assertRaises(Skip):
            review_requested.read(build_payload(requested_reviewer=bot), github, Inputs())

    def test_a_user_request_gives_one_recipient_with_the_emails_of_the_user(self):
        commit = {"commit": {"author": {"email": "rev@x.com"}}}
        github = build_github(extra={("list_author_commits", "rev"): [commit]})
        recipients = review_requested.read(build_payload(), github, Inputs()).recipients
        self.assertEqual([(r.login, r.emails) for r in recipients], [("rev", ["rev@x.com"])])
        self.assertEqual(recipients[0].message.metadata["event_payload"]["reviewer"], "rev")

    def test_a_team_request_gives_each_member_but_the_author_and_the_sender(self):
        team = {"slug": "core", "name": "Core"}
        payload = build_payload(requested_team=team)
        del payload["requested_reviewer"]
        github = build_github(members=["dev", "sender", "ann", "bob"])
        payload["sender"] = {"login": "sender"}
        recipients = review_requested.read(payload, github, Inputs()).recipients
        self.assertEqual([r.login for r in recipients], ["ann", "bob"])
        self.assertEqual([r.message.metadata["event_payload"]["reviewer"] for r in recipients], ["ann", "bob"])
        self.assertEqual(ReviewRequest.read(payload, github).reviewer, "core")

    def test_the_counts_are_those_of_the_tabs_of_the_pull_request(self):
        request = ReviewRequest.read(build_payload(), build_github())
        self.assertEqual(
            (request.comments, request.checks, request.files, request.additions, request.deletions), (3, 6, 4, 30, 5)
        )


def build_review(login, state):
    return {"user": {"login": login}, "state": state}


class TestTheUpdate(unittest.TestCase):
    """The run that writes the summary into the messages that the first run posted."""

    def read_team(self, reviews, extra=None):
        team = {"slug": "core", "name": "Core"}
        payload = build_payload(requested_team=team)
        del payload["requested_reviewer"]
        extra = {("list_pull_reviews", 42): reviews} | (extra or {})
        github = build_github(["ann", "bob", "cid"], extra)
        messages = tuple(("D1", f"{n}.5", login) for n, login in enumerate(("ann", "bob", "cid")))
        return review_requested.read(payload, github, Inputs(messages, SUMMARY)).recipients

    def test_the_update_reads_no_email_so_a_refused_read_of_the_commits_changes_nothing(self):
        refusal = GitHubError("gh api repos/x/commits failed: HTTP 502")
        extra = {("list_author_commits", login): refusal for login in ("ann", "bob", "cid")}
        recipients = self.read_team([], extra)
        self.assertEqual([(r.login, r.emails) for r in recipients], [("ann", []), ("bob", []), ("cid", [])])

    def test_a_member_whose_latest_review_approves_gets_the_approved_header_and_keeps_the_body(self):
        reviews = [
            build_review("ann", "APPROVED"),
            build_review("bob", "APPROVED"),
            build_review("ann", "COMMENTED"),
            build_review("bob", "CHANGES_REQUESTED"),
            {"user": None, "state": "APPROVED"},
        ]
        ann, bob, cid = (recipient.message for recipient in self.read_team(reviews))
        self.assertEqual((ann.color, bob.color, cid.color), ("#2EB67D", "#1D9BD1", "#1D9BD1"))
        self.assertEqual(ann.blocks[0]["text"]["text"], ":white_check_mark: Approved")
        self.assertIn("• The sitemap lists the drafts", str(ann.blocks))


class TestTheSummary(unittest.TestCase):
    def test_the_bullets_are_kept_and_another_key_is_left_out(self):
        self.assertEqual(Summary.parse({"bullets": ["a", "b"], "files": ["x"]}), Summary(("a", "b")))

    def test_more_than_three_bullets_keep_the_first_three_and_a_long_bullet_is_cut(self):
        summary = Summary.parse({"bullets": ["1", "2", "3", "4"]})
        self.assertEqual(summary.bullets, ("1", "2", "3"))
        self.assertEqual(len(Summary.parse({"bullets": ["x" * 500]}).bullets[0]), 200)

    def test_a_summary_with_no_bullet_gives_none(self):
        self.assertIsNone(Summary.parse({"bullets": []}))

    def test_anything_else_gives_none(self):
        for data in (
            ["a"],
            "text",
            None,
            {"bullets": [1]},
            {"bullets": "a"},
            {"files": ["a"]},
        ):
            with self.subTest(data=data):
                self.assertIsNone(Summary.parse(data))


if __name__ == "__main__":
    unittest.main()
