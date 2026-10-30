"""The message of a review request: the counts of its tabs, then the summary, pending, written or failed."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import test_pull_request
from events.review_requested import template
from events.review_requested.event import ReviewRequest, Summary
from test_ci_checks_template import read

PULL = "https://github.com/Jahia/sitemap/pull/42"


def build_request(**changes):
    request = ReviewRequest(test_pull_request.read(), "dev", 0, 18, 26, 1334, 54)
    return request._replace(**changes)


def lines(request=None, member="dev", summary=None, pending=True):
    return read(template.render(request or build_request(), member, summary, pending).blocks)


class TestTheReviewMessage(unittest.TestCase):
    def test_the_pending_message_shows_the_counts_the_pending_summary_and_the_button(self):
        message = template.render(build_request(), "dev", None, True)
        self.assertEqual((message.color, message.fallback), ("#1D9BD1", "👀 Review requested · Jahia/sitemap#42"))
        shown = lines()
        self.assertEqual(shown[0], "header: :eye: Review requested")
        self.assertEqual(
            shown[-3],
            "context: Conversation 0   |   Commits 3   |   Checks 18   |   Files changed 26   |   +1334 −54",
        )
        self.assertEqual(shown[-2], "section: *What the pull request changes*\n_Summary in progress…_")
        self.assertEqual(shown[-1], "actions: Review on GitHub")
        self.assertEqual(message.blocks[-1]["elements"][0]["url"], f"{PULL}/files")

    def test_a_count_of_one_reads_in_the_singular(self):
        pull = build_request().pull._replace(commits=1)
        request = build_request(pull=pull, comments=1, checks=1, files=1)
        self.assertIn(
            "context: Conversation 1   |   Commit 1   |   Check 1   |   File changed 1   |   +1334 −54",
            lines(request),
        )

    def test_the_metadata_names_the_member_who_receives_the_message(self):
        message = template.render(build_request(reviewer="core"), "ann", None, True)
        self.assertEqual(
            message.metadata,
            {
                "event_type": "review_requested",
                "event_payload": {"repository": "Jahia/sitemap", "number": 42, "reviewer": "ann"},
            },
        )

    def test_a_summary_gives_one_bullet_per_line(self):
        shown = "\n".join(lines(summary=Summary(("one", "two")), pending=False))
        self.assertIn("*What the pull request changes*\n• one\n• two", shown)

    def test_a_failed_summary_reads_as_no_summary(self):
        self.assertIn(
            "section: *What the pull request changes*\n_No summary, see the pull request_", lines(pending=False)
        )

    def test_a_parsed_summary_with_no_bullet_reads_as_no_summary(self):
        summary = Summary.parse({"bullets": []})
        self.assertIn(
            "section: *What the pull request changes*\n_No summary, see the pull request_",
            lines(summary=summary, pending=False),
        )

    def test_an_approved_message_opens_on_the_approved_header_on_the_green_bar_and_keeps_the_body(self):
        approved = template.render(build_request(), "dev", None, False, approved=True)
        request = template.render(build_request(), "dev", None, False)
        self.assertEqual((approved.color, approved.fallback), ("#2EB67D", "✅ Approved · Jahia/sitemap#42"))
        self.assertEqual(read(approved.blocks)[0], "header: :white_check_mark: Approved")
        self.assertEqual((approved.blocks[1:], approved.metadata), (request.blocks[1:], request.metadata))

    def test_a_title_with_markup_is_escaped(self):
        pull = build_request().pull._replace(title="a <b> & c")
        self.assertIn("a &lt;b&gt; &amp; c", "\n".join(lines(build_request(pull=pull))))


if __name__ == "__main__":
    unittest.main()
