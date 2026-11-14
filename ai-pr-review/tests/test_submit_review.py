"""The submit step: one review on the head that the prefetch read, an approval only when the review is clean,
a second try only when GitHub refuses an anchor, a review of this run on the pull request within three searches
after any other error, and no earlier approval of the account left after a comment."""

import json
import unittest

from fakes import FakeGh

URL = "https://github.com/o/r/pull/1"
HEAD = "a" * 40
MARKER = "<!-- cortex-pr-review -->"
POST = "-X POST repos/o/r/pulls/1/reviews"
REFUSED = {"exit": 1, "err": "gh: Unprocessable Entity (HTTP 422)\n"}
GATEWAY = {"exit": 1, "err": "gh: HTTP 502\n"}
APPROVALS = "pulls/1/reviews?per_page=100"
DISMISS = "-X PUT repos/o/r/pulls/1/reviews/11/dismissals"
LABELS = [
    {"args": "labels"},
    {"args": "api user", "out": "jahia-ai\n"},
    {"args": APPROVALS, "out": ""},
]


def threads(*nodes):
    return {"args": "graphql", "out": json.dumps({"data": {"repository": {"pullRequest": {"reviewThreads": {
        "pageInfo": {"hasNextPage": False, "endCursor": None},
        "nodes": [{"isResolved": resolved, "comments": {"nodes": [{"author": {"login": login}}]}}
                  for resolved, login in nodes]}}}}})}
FINDING = {"path": "a.py", "line": 3, "side": "RIGHT", "body": "a finding"}


def review(event="COMMENT", comments=(), human_review="not-needed"):
    return {"contract": "v1", "event": event, "human_review": human_review,
            "body": f"{MARKER}\nLGTM.", "comments": list(comments)}


class TestTheSubmit(unittest.TestCase):
    def submit(self, scenario, review_file):
        self.gh = FakeGh(self, scenario + LABELS)
        path = self.gh.dir / "review.json"
        path.write_text(json.dumps(review_file), encoding="utf-8")
        return self.gh.run("submit-review.py", "post", str(path), URL,
                           env={"REVIEWED_SHA": HEAD, "MARKER": MARKER, "STARTED_AT": "2026-11-10T10:00:00Z",
                                "LANDED_PAUSE": "0"})

    def posts(self):
        return [json.loads(call["stdin"]) for call in self.gh.calls(POST)]

    def test_a_clean_approve_approves_the_head_that_the_prefetch_read(self):
        done = self.submit([{"args": POST, "out": "{}"}, threads((True, "jahia-ai"), (False, "author"))],
                           review(event="APPROVE"))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual([(post["event"], post["commit_id"]) for post in self.posts()], [("APPROVE", HEAD)])
        self.assertEqual(self.gh.calls(APPROVALS), [])

    def test_an_approve_with_an_open_thread_of_the_account_posts_as_comment(self):
        done = self.submit([{"args": POST, "out": "{}"}, threads((False, "jahia-ai"))], review(event="APPROVE"))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual([post["event"] for post in self.posts()], ["COMMENT"])
        self.assertIn("1 thread(s) of jahia-ai", done.stdout)

    def test_an_approve_that_asks_for_a_human_posts_as_comment(self):
        done = self.submit([{"args": POST, "out": "{}"}, threads()],
                           review(event="APPROVE", human_review="recommended"))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual([post["event"] for post in self.posts()], ["COMMENT"])
        self.assertEqual(self.gh.calls("graphql"), [])

    def test_an_approve_with_inline_comments_posts_as_comment(self):
        done = self.submit([{"args": POST, "out": "{}"}, threads()], review(event="APPROVE", comments=[FINDING]))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual([post["event"] for post in self.posts()], ["COMMENT"])

    def test_an_approve_with_unread_threads_posts_as_comment(self):
        done = self.submit([{"args": POST, "out": "{}"}, {"args": "graphql", **GATEWAY}], review(event="APPROVE"))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual([post["event"] for post in self.posts()], ["COMMENT"])

    def test_an_approve_on_a_later_page_of_threads_sees_an_open_thread(self):
        first = threads((True, "jahia-ai"))
        page = json.loads(first["out"])
        page["data"]["repository"]["pullRequest"]["reviewThreads"]["pageInfo"] = {"hasNextPage": True, "endCursor": "c1"}
        done = self.submit([{"args": POST, "out": "{}"}, {**threads((False, "jahia-ai")), "args": "after=c1"},
                            {"args": "graphql", "out": json.dumps(page)}], review(event="APPROVE"))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual([post["event"] for post in self.posts()], ["COMMENT"])

    def test_an_approve_with_an_unknown_login_posts_as_comment_and_fails_on_the_approvals(self):
        done = self.submit([{"args": POST, "out": "{}"}, {"args": "api user", **GATEWAY}], review(event="APPROVE"))
        self.assertEqual(done.returncode, 1)
        self.assertEqual([post["event"] for post in self.posts()], ["COMMENT"])
        self.assertIn("login of the token account is unknown", done.stdout)

    def test_a_refused_approve_posts_as_comment_and_dismisses(self):
        done = self.submit([{"args": POST, "stdin": '"APPROVE"', **REFUSED}, {"args": POST, "out": "{}"},
                            threads(), {"args": APPROVALS, "out": "11\n"}, {"args": DISMISS, "out": "{}"}],
                           review(event="APPROVE"))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual([post["event"] for post in self.posts()], ["APPROVE", "COMMENT"])
        self.assertEqual(len(self.gh.calls(DISMISS)), 1)

    def test_a_comment_that_fails_still_dismisses_the_earlier_approvals(self):
        done = self.submit([{"args": POST, **REFUSED}, {"args": APPROVALS, "out": "11\n"},
                            {"args": DISMISS, "out": "{}"}], review(comments=[FINDING]))
        self.assertEqual(done.returncode, 1)
        self.assertEqual(len(self.gh.calls(DISMISS)), 1)

    def test_an_approve_that_fails_to_post_dismisses_the_earlier_approvals(self):
        done = self.submit([{"args": POST, **GATEWAY}, threads(), {"args": "pulls/1/reviews --paginate", "out": "[]"},
                            {"args": APPROVALS, "out": "11\n"}, {"args": DISMISS, "out": "{}"}],
                           review(event="APPROVE"))
        self.assertEqual(done.returncode, 1)
        self.assertEqual([post["event"] for post in self.posts()], ["APPROVE"])
        self.assertEqual(len(self.gh.calls(DISMISS)), 1)

    def test_a_comment_dismisses_an_earlier_approval_of_the_account(self):
        done = self.submit([{"args": POST, "out": "{}"}, {"args": APPROVALS, "out": "11\n"},
                            {"args": DISMISS, "out": "{}"}], review())
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(len(self.gh.calls(DISMISS)), 1)
        self.assertIn('"jahia-ai"', self.gh.calls(APPROVALS)[0]["args"])

    def test_a_refused_dismissal_fails_after_the_comment(self):
        done = self.submit([{"args": POST, "out": "{}"}, {"args": APPROVALS, "out": "11\n"},
                            {"args": DISMISS, "exit": 1, "err": "gh: Forbidden (HTTP 403)\n"}], review())
        self.assertEqual(done.returncode, 1)
        self.assertEqual([post["event"] for post in self.posts()], ["COMMENT"])
        self.assertIn("review 11", done.stdout)

    def test_a_refused_anchor_posts_the_findings_in_the_body_on_the_same_head(self):
        done = self.submit([{"args": POST, "stdin": '"comments"', **REFUSED}, {"args": POST, "out": "{}"}],
                           review(comments=[FINDING]))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        first, second = self.posts()
        self.assertIn("comments", first)
        self.assertNotIn("comments", second)
        self.assertIn("a finding", second["body"])
        self.assertEqual(second["commit_id"], HEAD)

    def test_a_refused_head_fails_with_no_post_on_another_commit_and_no_search(self):
        done = self.submit([{"args": POST, **REFUSED}], review(comments=[FINDING]))
        self.assertEqual(done.returncode, 1)
        self.assertEqual([post["commit_id"] for post in self.posts()], [HEAD, HEAD])
        self.assertEqual(self.gh.calls("pulls/1/reviews --paginate"), [])

    def test_a_gateway_error_is_not_retried_and_a_review_of_this_run_counts(self):
        landed = [{"user": {"login": "jahia-ai"}, "body": f"{MARKER}\nLGTM.", "submitted_at": "2026-11-10T10:05:00Z"}]
        done = self.submit([{"args": POST, **GATEWAY},
                            {"args": "pulls/1/reviews --paginate", "out": json.dumps(landed)}],
                           review(comments=[FINDING]))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(len(self.posts()), 1)

    def test_a_review_that_github_creates_after_the_error_counts_at_a_later_search(self):
        landed = [{"user": {"login": "jahia-ai"}, "body": f"{MARKER}\nLGTM.", "submitted_at": "2026-11-10T10:05:00Z"}]
        done = self.submit([{"args": POST, **GATEWAY},
                            {"args": "pulls/1/reviews --paginate", "from_call": 2, "out": json.dumps(landed)},
                            {"args": "pulls/1/reviews --paginate", "out": "[]"}], review())
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(len(self.gh.calls("pulls/1/reviews --paginate")), 2)

    def test_a_review_of_another_account_with_the_marker_does_not_count(self):
        quoted = [{"user": {"login": "mallory"}, "body": f"{MARKER}\nquoted", "submitted_at": "2026-11-10T10:05:00Z"}]
        done = self.submit([{"args": POST, **GATEWAY},
                            {"args": "pulls/1/reviews --paginate", "out": json.dumps(quoted)}], review())
        self.assertEqual(done.returncode, 1)

    def test_a_gateway_error_with_no_review_of_this_run_fails(self):
        older = [{"body": f"{MARKER}\nan earlier run", "submitted_at": "2026-11-10T09:00:00Z"}]
        done = self.submit([{"args": POST, **GATEWAY},
                            {"args": "pulls/1/reviews --paginate", "out": json.dumps(older)}], review())
        self.assertEqual(done.returncode, 1)
        self.assertEqual(len(self.posts()), 1)
        self.assertEqual(len(self.gh.calls("pulls/1/reviews --paginate")), 3)


if __name__ == "__main__":
    unittest.main()
