"""The approval of a review, which turns the message of the review request to approved."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import events
from events import review_approved
from fakes import FakeGitHub
from notification import Inputs, Skip


def build_payload(state="approved"):
    return {
        "review": {"state": state, "user": {"login": "rev"}},
        "pull_request": {"number": 42},
        "repository": {"full_name": "Jahia/sitemap"},
    }


class TestTheApproval(unittest.TestCase):
    def test_an_event_is_registered_for_pull_request_review(self):
        self.assertIs(events.EVENTS["pull_request_review"], review_approved)

    def test_a_review_that_is_no_approval_raises_skip(self):
        for state in ("changes_requested", "commented"):
            with self.assertRaises(Skip):
                review_approved.read(build_payload(state), FakeGitHub({}), Inputs())

    def test_an_approval_gives_the_reviewer_a_header_on_the_green_bar_and_the_metadata_of_the_request(self):
        commit = {"commit": {"author": {"email": "rev@x.com"}}}
        github = FakeGitHub({("list_author_commits", "rev"): [commit]})
        [recipient] = review_approved.read(build_payload(), github, Inputs()).recipients
        self.assertEqual((recipient.login, recipient.emails), ("rev", ["rev@x.com"]))
        find = {
            "event_type": "review_requested",
            "event_payload": {"repository": "Jahia/sitemap", "number": 42, "reviewer": "rev"},
        }
        self.assertEqual(recipient.find, find)
        self.assertEqual(recipient.message.color, "#2EB67D")
        header = {
            "type": "header",
            "text": {"type": "plain_text", "text": ":white_check_mark: Approved", "emoji": True},
        }
        self.assertEqual(recipient.message.blocks, [header])
