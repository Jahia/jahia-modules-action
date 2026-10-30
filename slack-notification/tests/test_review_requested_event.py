"""The review request that `ReviewRequest.read` reads from the event, its size, and the summary of the AI."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import events
from events import review_requested
from events.review_requested.event import ReviewFile, ReviewRequest, Summary
from fakes import FakeGitHub
from notification import Inputs, Skip
from test_pull_request import build_pull


def build_payload(**changes):
    payload = {
        "action": "review_requested",
        "pull_request": {"number": 42},
        "requested_reviewer": {"login": "rev", "type": "User", "html_url": "https://github.com/rev"},
        "sender": {"login": "dev"},
    }
    return payload | changes


def build_file(name, additions, deletions=0):
    return {"filename": name, "additions": additions, "deletions": deletions}


def build_github(files, members=(), extra=None):
    results = {("read_pull", 42): build_pull(), ("list_pull_files", 42): files}
    results |= {("list_team_members", "core"): [{"login": login} for login in members]}
    results |= {("list_author_commits", login): [] for login in ("rev", *members)}
    return FakeGitHub(results | (extra or {}))


class TestTheReviewRequest(unittest.TestCase):
    def test_an_event_is_registered_for_pull_request_target(self):
        self.assertIs(events.EVENTS["pull_request_target"], review_requested)

    def test_another_action_and_a_bot_reviewer_raise_skip(self):
        github = build_github([])
        with self.assertRaises(Skip):
            review_requested.read(build_payload(action="opened"), github, Inputs())
        bot = {"login": "bot", "type": "Bot", "html_url": "x"}
        with self.assertRaises(Skip):
            review_requested.read(build_payload(requested_reviewer=bot), github, Inputs())

    def test_a_user_request_gives_one_recipient_with_the_emails_of_the_user(self):
        commit = {"commit": {"author": {"email": "rev@x.com"}}}
        github = build_github([build_file("a.py", 3)], extra={("list_author_commits", "rev"): [commit]})
        recipients = review_requested.read(build_payload(), github, Inputs()).recipients
        self.assertEqual([(r.login, r.emails) for r in recipients], [("rev", ["rev@x.com"])])
        self.assertEqual(recipients[0].message.metadata["event_payload"]["reviewer"], "rev")

    def test_a_team_request_gives_each_member_but_the_author_and_the_sender(self):
        team = {"slug": "core", "name": "Core"}
        payload = build_payload(requested_team=team)
        del payload["requested_reviewer"]
        github = build_github([build_file("a.py", 3)], members=["dev", "sender", "ann", "bob"])
        payload["sender"] = {"login": "sender"}
        recipients = review_requested.read(payload, github, Inputs()).recipients
        self.assertEqual([r.login for r in recipients], ["ann", "bob"])
        self.assertEqual([r.message.metadata["event_payload"]["reviewer"] for r in recipients], ["ann", "bob"])
        request = ReviewRequest.read(payload, github)
        self.assertEqual(
            (request.reviewer, request.reviewer_url), ("@Jahia/core", "https://github.com/orgs/Jahia/teams/core")
        )

    def test_the_lines_and_the_files_leave_out_the_lock_files_and_the_generated_files(self):
        files = [
            build_file("package-lock.json", 500),
            build_file("web/yarn.lock", 500),
            build_file("pnpm-lock.yaml", 1),
            build_file("uv.lock", 1),
            build_file("poetry.lock", 1),
            build_file("go.sum", 1),
            build_file("dist/app.min.js", 1),
            build_file("a.snap", 1),
            build_file("src/a.py", 4, 1),
        ]
        request = ReviewRequest.read(build_payload(), build_github(files))
        self.assertEqual((request.lines, request.files, request.more), (5, (ReviewFile("src/a.py", 4, 1),), 0))

    def test_the_files_hold_the_three_with_the_most_changed_lines_and_more_counts_the_others(self):
        files = [build_file(name, count) for name, count in (("a", 1), ("b", 9), ("c", 5), ("d", 7), ("e", 2))]
        request = ReviewRequest.read(build_payload(), build_github(files))
        self.assertEqual(([file.path for file in request.files], request.more), (["b", "d", "c"], 2))

    def test_the_size_and_the_minutes_follow_the_changed_lines(self):
        pull = ReviewRequest.read(build_payload(), build_github([])).pull
        for lines, size, minutes in [
            (0, "XS", 5), (9, "XS", 5), (10, "S", 5), (99, "S", 10),
            (100, "M", 10), (499, "M", 50), (500, "L", 50), (1000, "XL", 100),
        ]:  # fmt: skip
            with self.subTest(lines=lines):
                request = ReviewRequest(pull, "r", "u", lines, (), 0)
                self.assertEqual((request.size, request.minutes), (size, minutes))

    def test_a_pull_request_of_lock_files_alone_gives_no_lines_and_no_files(self):
        github = build_github([build_file("package-lock.json", 900), build_file("uv.lock", 3)])
        request = ReviewRequest.read(build_payload(), github)
        self.assertEqual((request.lines, request.files, request.more, request.size), (0, (), 0, "XS"))


class TestTheSummary(unittest.TestCase):
    def test_a_dict_of_strings_is_kept(self):
        self.assertEqual(Summary.parse({"bullets": ["a", "b"], "files": ["x"]}), Summary(("a", "b"), ("x",)))

    def test_more_than_three_bullets_keep_the_first_three_and_a_long_bullet_is_cut(self):
        summary = Summary.parse({"bullets": ["1", "2", "3", "4"], "files": []})
        self.assertEqual(summary.bullets, ("1", "2", "3"))
        self.assertEqual(len(Summary.parse({"bullets": ["x" * 500], "files": []}).bullets[0]), 200)

    def test_anything_else_gives_none(self):
        for data in (
            ["a"],
            "text",
            None,
            {"bullets": [1], "files": []},
            {"bullets": "a"},
            {"bullets": [], "files": [2]},
        ):
            with self.subTest(data=data):
                self.assertIsNone(Summary.parse(data))


if __name__ == "__main__":
    unittest.main()
