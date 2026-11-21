"""A pull request reads as its page on GitHub shows it, and its part of a message names its repository, its
title and its state, then a separator."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from fakes import FakeGitHub
from pull_request import PullRequest
from templates import pull_request


def build_pull(**changes):
    """The pull request 42 of `Jahia/sitemap`, as the REST API of GitHub returns it."""
    pull = {
        "number": 42,
        "title": "feat: a <b>",
        "html_url": "https://github.com/Jahia/sitemap/pull/42",
        "state": "open",
        "draft": False,
        "merged_at": None,
        "user": {"login": "dev", "html_url": "https://github.com/dev"},
        "commits": 3,
        "base": {"ref": "main", "repo": {"full_name": "Jahia/sitemap", "html_url": "https://github.com/Jahia/sitemap"}},
        "head": {"ref": "feat/x", "sha": "abc"},
        "comments": 1,
        "review_comments": 2,
        "changed_files": 4,
        "additions": 30,
        "deletions": 5,
    }
    return pull | changes


def read(**changes):
    return PullRequest.read(FakeGitHub({("read_pull", 42): build_pull(**changes)}), 42)


class TestThePullRequest(unittest.TestCase):
    def test_a_pull_request_reads_as_its_page_on_github_shows_it(self):
        pull = read()
        self.assertEqual(
            pull,
            PullRequest(
                "Jahia/sitemap",
                "https://github.com/Jahia/sitemap",
                42,
                "feat: a <b>",
                "https://github.com/Jahia/sitemap/pull/42",
                "open",
                "dev",
                "https://github.com/dev",
                3,
                "main",
                "feat/x",
            ),
        )
        self.assertEqual(pull.reference, "Jahia/sitemap#42")

    def test_a_draft_a_merged_and_a_closed_pull_request_read_their_state(self):
        self.assertEqual(read(draft=True).state, "draft")
        self.assertEqual(read(draft=True, state="closed").state, "closed")
        self.assertEqual(read(state="closed", merged_at="2026-10-30T00:00:00Z").state, "merged")
        self.assertEqual(read(state="closed").state, "closed")


class TestThePartOfAPullRequest(unittest.TestCase):
    def test_the_part_names_the_repository_the_title_and_the_state_then_a_separator(self):
        blocks = pull_request.show(read())
        self.assertEqual(
            blocks[0]["text"]["text"],
            "*<https://github.com/Jahia/sitemap|Jahia/sitemap>*\n"
            "*feat: a &lt;b&gt;* <https://github.com/Jahia/sitemap/pull/42|#42>",
        )
        self.assertEqual(
            blocks[1]["elements"][0]["text"],
            ":large_green_circle: *Open* · <https://github.com/dev|dev> wants to merge 3 commits into `main` from"
            " `feat/x`",
        )
        self.assertEqual(blocks[2], {"type": "divider"})

    def test_the_circle_the_label_and_the_verb_follow_the_state(self):
        for changes, line in (
            ({"draft": True}, ":white_circle: *Draft* · <https://github.com/dev|dev> wants to merge"),
            (
                {"merged_at": "2026-10-30T00:00:00Z"},
                ":large_purple_circle: *Merged* · <https://github.com/dev|dev> merged",
            ),
            ({"state": "closed"}, ":red_circle: *Closed* · <https://github.com/dev|dev> wanted to merge"),
        ):
            with self.subTest(line):
                text = pull_request.show(read(**changes))[1]["elements"][0]["text"]
                self.assertTrue(text.startswith(f"{line} 3 commits"), text)

    def test_one_commit_reads_in_the_singular(self):
        text = pull_request.show(read(commits=1))[1]["elements"][0]["text"]
        self.assertIn("wants to merge 1 commit into", text)


if __name__ == "__main__":
    unittest.main()
