"""The message of a review request: pending, with a summary, and with none."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import test_pull_request
from events.review_requested import template
from events.review_requested.event import ReviewFile, ReviewRequest, Summary
from test_ci_checks_template import read

PULL = "https://github.com/Jahia/sitemap/pull/42"
SQUARES = ":large_green_square:" * 3 + ":large_red_square:" * 2


def build_request(**changes):
    request = ReviewRequest(
        test_pull_request.read(),
        "dev",
        "https://github.com/dev",
        50,
        (ReviewFile("src/a.py", 30, 20), ReviewFile("b.py", 0, 4)),
        3,
    )
    return request._replace(**changes)


def lines(request=None, member="dev", summary=None, pending=True):
    return read(template.render(request or build_request(), member, summary, pending).blocks)


class TestTheReviewMessage(unittest.TestCase):
    def test_the_pending_message_shows_the_context_the_files_and_the_button(self):
        message = template.render(build_request(), "dev", None, True)
        self.assertEqual((message.color, message.fallback), ("#1D9BD1", "👀 Review requested · Jahia/sitemap#42"))
        shown = lines()
        self.assertEqual(shown[0], "header: :eye: Review requested")
        self.assertIn("context: For <https://github.com/dev|dev> · size S · ~5 min to review", shown)
        self.assertIn("section: *What the pull request changes*\n_Summary in progress…_", shown)
        self.assertIn(
            f"section: *Where to start*\nsrc/a.py   +30 −20   {SQUARES}\n"
            f"b.py   +0 −4   {':large_red_square:' * 5}\n+ 3 more files",
            shown,
        )
        self.assertEqual(shown[-1], "actions: Review on GitHub")
        self.assertEqual(message.blocks[-1]["elements"][0]["url"], f"{PULL}/files")

    def test_a_team_request_names_the_team_and_the_metadata_names_the_member(self):
        request = build_request(reviewer="@Jahia/core", reviewer_url="https://github.com/orgs/Jahia/teams/core")
        message = template.render(request, "ann", None, True)
        self.assertIn(
            "context: For <https://github.com/orgs/Jahia/teams/core|@Jahia/core> · size S · ~5 min to review",
            lines(request),
        )
        self.assertEqual(
            message.metadata,
            {
                "event_type": "review_requested",
                "event_payload": {"repository": "Jahia/sitemap", "number": 42, "reviewer": "ann"},
            },
        )

    def test_a_summary_gives_one_bullet_per_line_and_orders_the_files(self):
        summary = Summary(("one", "two"), ("b.py", "src/a.py"))
        shown = "\n".join(lines(summary=summary, pending=False))
        self.assertIn("*What the pull request changes*\n• one\n• two", shown)
        self.assertLess(shown.index("b.py   +0"), shown.index("src/a.py   +30"))

    def test_a_summary_that_names_an_unknown_file_leaves_the_order_alone(self):
        shown = "\n".join(lines(summary=Summary(("one",), ("zzz",))))
        self.assertLess(shown.index("src/a.py"), shown.index("b.py"))

    def test_a_failed_summary_reads_as_no_summary(self):
        self.assertIn(
            "section: *What the pull request changes*\n_No summary, see the pull request_", lines(pending=False)
        )

    def test_a_request_with_no_file_has_no_where_to_start_section(self):
        shown = "\n".join(lines(build_request(lines=0, files=(), more=0)))
        self.assertNotIn("Where to start", shown)
        self.assertIn("size XS", shown)

    def test_a_title_with_markup_is_escaped(self):
        pull = build_request().pull._replace(title="a <b> & c")
        self.assertIn("a &lt;b&gt; &amp; c", "\n".join(lines(build_request(pull=pull))))


if __name__ == "__main__":
    unittest.main()
