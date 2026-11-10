"""The submit step: one COMMENT review on the head that the prefetch read, a second try only when GitHub
refuses an anchor, and a review of this run already on the pull request after any other error."""

import json
import unittest

from fakes import FakeGh

URL = "https://github.com/o/r/pull/1"
HEAD = "a" * 40
MARKER = "<!-- cortex-pr-review -->"
POST = "-X POST repos/o/r/pulls/1/reviews"
REFUSED = {"exit": 1, "err": "gh: Unprocessable Entity (HTTP 422)\n"}
GATEWAY = {"exit": 1, "err": "gh: HTTP 502\n"}
LABELS = [{"args": "labels"}, {"args": "api user", "out": "jahia-ai\n"}]
FINDING = {"path": "a.py", "line": 3, "side": "RIGHT", "body": "a finding"}


def review(event="COMMENT", comments=()):
    return {"contract": "v1", "event": event, "human_review": "not-needed",
            "body": f"{MARKER}\nLGTM.", "comments": list(comments)}


class TestTheSubmit(unittest.TestCase):
    def submit(self, scenario, review_file):
        self.gh = FakeGh(self, scenario + LABELS)
        path = self.gh.dir / "review.json"
        path.write_text(json.dumps(review_file), encoding="utf-8")
        return self.gh.run("submit-review.py", "post", str(path), URL,
                           env={"REVIEWED_SHA": HEAD, "MARKER": MARKER, "STARTED_AT": "2026-11-10T10:00:00Z"})

    def posts(self):
        return [json.loads(call["stdin"]) for call in self.gh.calls(POST)]

    def test_an_approve_posts_as_comment_on_the_head_that_the_prefetch_read(self):
        done = self.submit([{"args": POST, "out": "{}"}], review(event="APPROVE"))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual([(post["event"], post["commit_id"]) for post in self.posts()], [("COMMENT", HEAD)])

    def test_a_refused_anchor_posts_the_findings_in_the_body_on_the_same_head(self):
        done = self.submit([{"args": POST, "stdin": '"comments"', **REFUSED}, {"args": POST, "out": "{}"}],
                           review(comments=[FINDING]))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        first, second = self.posts()
        self.assertIn("comments", first)
        self.assertNotIn("comments", second)
        self.assertIn("a finding", second["body"])
        self.assertEqual(second["commit_id"], HEAD)

    def test_a_refused_head_fails_with_no_post_on_another_commit(self):
        done = self.submit([{"args": POST, **REFUSED}, {"args": "pulls/1/reviews --paginate", "out": "[]"}],
                           review(comments=[FINDING]))
        self.assertEqual(done.returncode, 1)
        self.assertEqual([post["commit_id"] for post in self.posts()], [HEAD, HEAD])

    def test_a_gateway_error_is_not_retried_and_a_review_of_this_run_counts(self):
        landed = [{"user": {"login": "jahia-ai"}, "body": f"{MARKER}\nLGTM.", "submitted_at": "2026-11-10T10:05:00Z"}]
        done = self.submit([{"args": POST, **GATEWAY},
                            {"args": "pulls/1/reviews --paginate", "out": json.dumps(landed)}],
                           review(comments=[FINDING]))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(len(self.posts()), 1)

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


if __name__ == "__main__":
    unittest.main()
