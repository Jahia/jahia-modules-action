"""The prefetch: the diff since the last own review, the files of that diff, and the rule files of the
base branch, as the context directory gives them to the review agent."""

import json
import pathlib
import unittest

from fakes import FakeGh

URL = "https://github.com/o/r/pull/1"
HEAD = "a" * 40
SINCE = "b" * 40
MARKER = "<!-- cortex-pr-review -->"
PR_DIFF = ("diff --git a/src/a.py b/src/a.py\n--- a/src/a.py\n+++ b/src/a.py\n"
           "@@ -1,1 +1,2 @@\n x\n+added by the pr\n")
DELTA = ("diff --git a/src/a.py b/src/a.py\n--- a/src/a.py\n+++ b/src/a.py\n"
         "@@ -1,1 +1,2 @@\n x\n+added by the pr\n"
         "@@ -10,1 +11,1 @@\n-x = 2\n+x = 1\n"
         "diff --git a/src/new.py b/src/new.py\ndeleted file mode 100644\n--- a/src/new.py\n+++ /dev/null\n"
         "@@ -1 +0,0 @@\n-removed by the last push\n"
         "diff --git a/other.txt b/other.txt\n--- a/other.txt\n+++ b/other.txt\n@@ -1 +1 @@\n-a\n+b\n")
THREADED = [
    {"id": 101, "path": "src/a.py", "line": 2, "user": {"login": "jahia-ai"}, "pull_request_review_id": 11,
     "created_at": "2026-11-10T10:00:00Z", "body": "a finding"},
    {"id": 102, "path": "src/a.py", "line": 2, "user": {"login": "author"}, "in_reply_to_id": 101,
     "pull_request_review_id": 13, "created_at": "2026-11-10T10:30:00Z", "body": "fixed"},
]
RESOLVED = {"data": {"repository": {"pullRequest": {"reviewThreads": {
    "pageInfo": {"hasNextPage": False, "endCursor": None},
    "nodes": [{"isResolved": True, "comments": {"nodes": [{"databaseId": 101}]}}]}}}}}
OWN = {
    "id": 11,
    "user": {"login": "jahia-ai"},
    "state": "COMMENTED",
    "commit_id": SINCE,
    "submitted_at": "2026-11-10T10:00:00Z",
    "body": f"{MARKER}\nfirst review",
}
FORGED = {
    "id": 12,
    "user": {"login": "mallory"},
    "state": "COMMENTED",
    "commit_id": HEAD,
    "submitted_at": "2026-11-10T11:00:00Z",
    "body": f"{MARKER}\nquoted",
}
NO_THREAD = {"data": {"repository": {"pullRequest": {"reviewThreads": {
    "pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": []}}}}}


def rules(reviews=(OWN, FORGED), status="ahead\n", status_exit=0, files_exit=0,
          earlier=(["src/a.py", None], ["src/new.py", None]), earlier_exit=0, diff_exit=0, comments=(),
          threads=NO_THREAD, files=("src/a.py",), blobs=()):
    pr = {"number": 1, "headRefOid": HEAD, "baseRefName": "main",
          "files": [{"path": "src/a.py", "additions": 1, "deletions": 0}]}
    return [
        {"args": f"compare/main...{SINCE}", "exit": earlier_exit, "err": "gh: HTTP 502\n",
         "out": "" if earlier_exit else json.dumps(list(earlier))},
        {"args": f"compare/main...{HEAD}", "exit": diff_exit, "err": "gh: HTTP 502\n",
         "out": "" if diff_exit else PR_DIFF},
        {"args": "pr diff", "out": PR_DIFF},
        {"args": "fetch --no-tags origin"},
        {"args": "checkout --detach FETCH_HEAD"},
        {"args": "rev-parse HEAD", "out": f"{HEAD}\n"},
        {"args": "repo clone"},
        {"args": "auth setup-git"},
        {"args": f"pr view {URL} --json number", "out": json.dumps(pr)},
        {"args": f"pr view {URL} --json closingIssuesReferences", "out": '{"closingIssuesReferences": []}'},
        {"args": f"pr view {URL} --comments", "out": ""},
        {"args": f"pr view {URL}", "out": "title: a change\n"},
        {"args": "pr checks", "out": "all checks pass\n"},
        {"args": "pulls/1/files", "exit": files_exit, "err": "gh: HTTP 502\n",
         "out": "" if files_exit else json.dumps([{"filename": path, "additions": 1, "deletions": 0}
                                                  for path in files])},
        {"args": "pulls/1/reviews", "out": json.dumps(list(reviews))},
        {"args": "pulls/1/comments", "out": json.dumps(list(comments))},
        {"args": "reviewThreads", "out": json.dumps(threads)},
        {"args": "api user", "out": "jahia-ai\n"},
        {"args": f"compare/{SINCE}...{HEAD}?per_page=1&page=2", "out": status, "exit": status_exit,
         "err": "gh: Not Found (HTTP 404)\n" if status_exit else ""},
        {"args": f"compare/{SINCE}...{HEAD}", "out": DELTA},
        *blobs,
        {"args": "graphql --input", "stdin": "main:AGENTS.md",
         "out": json.dumps({"data": {"repository": {"f0": {"text": "the rules of the agents\n"}}}})},
        {"args": "graphql --input", "stdin": "main:CLAUDE.md",
         "out": json.dumps({"data": {"repository": {"f0": {"text": "see @./AGENTS.md and @../../escape.md\n"},
                                                    "f1": None, "f2": None}}})},
    ]


class TestThePrefetch(unittest.TestCase):
    def prefetch(self, scenario, checkout=False):
        self.gh = FakeGh(self, scenario)
        self.context = self.gh.dir / "context"
        env = {"PR_URL": URL, "MARKER": MARKER}
        if checkout:
            env["CHECKOUT_ROOT"] = str(self.gh.dir / "sources")
        done = self.gh.run("prefetch-context.py", str(self.context), env=env)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.readme = (self.context / "README.md").read_text(encoding="utf-8")
        return done

    def test_the_diff_and_the_checkout_are_pinned_to_the_head_that_the_step_prints(self):
        done = self.prefetch(rules(), checkout=True)
        self.assertEqual((self.context / "diff.patch").read_text(encoding="utf-8"), PR_DIFF)
        self.assertEqual(done.stdout.strip(), HEAD)
        self.assertEqual(self.gh.calls("pr diff"), [])
        self.assertEqual(len(self.gh.calls(f"fetch --no-tags origin {HEAD}")), 1)

    def test_a_failed_compare_of_the_head_gives_no_diff_of_another_head(self):
        self.prefetch(rules(diff_exit=1))
        self.assertEqual(len(self.gh.calls(f"compare/main...{HEAD}")), 2)
        self.assertFalse((self.context / "diff.patch").exists())
        self.assertEqual(self.gh.calls("pr diff"), [])
        self.assertIn("- `diff.patch` — the compare of the head of `pr.json` failed twice: gh: HTTP 502", self.readme)

    def test_the_delta_keeps_the_files_of_the_pull_request_since_the_own_review(self):
        self.prefetch(rules())
        delta = (self.context / "delta.patch").read_text(encoding="utf-8")
        self.assertIn("+added by the pr", delta)
        self.assertIn("+x = 1", delta)
        self.assertIn("-removed by the last push", delta)
        self.assertNotIn("other.txt", delta)
        self.assertIn(f"read commit `{SINCE}`", self.readme)
        self.assertIn("This run posts as `jahia-ai`", self.readme)
        self.assertEqual(len(self.gh.calls(f"compare/main...{SINCE}?per_page=1 ")), 1)

    def test_a_list_of_3000_changed_files_keeps_every_file_of_the_delta_and_says_why(self):
        self.prefetch(rules(files=[f"f{i}.py" for i in range(3000)]))
        self.assertIn("other.txt", (self.context / "delta.patch").read_text(encoding="utf-8"))
        self.assertIn("`changed files` — GitHub lists 3000 files at most", self.readme)

    def test_a_cut_list_of_the_files_at_the_reviewed_commit_keeps_every_file(self):
        self.prefetch(rules(earlier=[[f"f{i}.py", None] for i in range(300)]))
        self.assertIn("other.txt", (self.context / "delta.patch").read_text(encoding="utf-8"))

    def test_an_unread_list_of_the_files_at_the_reviewed_commit_keeps_every_file_and_says_why(self):
        self.prefetch(rules(earlier_exit=1))
        self.assertIn("other.txt", (self.context / "delta.patch").read_text(encoding="utf-8"))
        self.assertIn("`files at the reviewed commit` — gh: HTTP 502", self.readme)

    def test_each_thread_gives_its_state_the_review_of_its_first_comment_and_its_replies(self):
        self.prefetch(rules(comments=THREADED, threads=RESOLVED))
        threads = (self.context / "review-comments.md").read_text(encoding="utf-8")
        self.assertIn("## src/a.py:2 — resolved — review 11", threads)
        self.assertIn("### comment 101 by jahia-ai", threads)
        self.assertIn("### comment 102 by author", threads)
        self.assertEqual(threads.count("## src/a.py:2"), 1)

    def test_a_review_of_another_account_with_the_marker_gives_no_delta(self):
        self.prefetch(rules(reviews=(FORGED,)))
        self.assertFalse((self.context / "delta.patch").exists())
        self.assertNotIn("## Delta since the last review", self.readme)

    def test_a_compare_that_answers_404_reads_as_a_rewrite(self):
        self.prefetch(rules(status="", status_exit=1))
        self.assertFalse((self.context / "delta.patch").exists())
        self.assertIn("the branch was rewritten", self.readme)
        self.assertNotIn("## Not available", self.readme)

    def test_an_identical_compare_writes_an_empty_delta_with_no_diff_call(self):
        self.prefetch(rules(status="identical\n"))
        self.assertEqual((self.context / "delta.patch").read_text(encoding="utf-8"), "")
        self.assertEqual([call for call in self.gh.calls(f"compare/{SINCE}") if "page=2" not in call["args"]], [])

    def test_a_partial_list_of_files_keeps_every_file_of_the_delta(self):
        self.prefetch(rules(files_exit=1))
        self.assertIn("other.txt", (self.context / "delta.patch").read_text(encoding="utf-8"))
        self.assertIn("`changed files`", self.readme)

    def test_the_rules_query_100_paths_at_a_time_and_keep_the_batches_that_answer(self):
        # 150 directories and the 2 root files make 2 batches, and the second one fails twice.
        self.prefetch(rules(files=[f"d{i:03}/x.py" for i in range(150)],
                            blobs=[{"args": "graphql --input", "stdin": "main:d149/CLAUDE.md", "exit": 1,
                                    "err": "gh: HTTP 502\n"}]))
        batches = [call for call in self.gh.calls("graphql --input") if "main:d" in call["stdin"]]
        self.assertEqual(len(batches), 3)
        self.assertTrue((self.context / "rules" / "CLAUDE.md").exists())
        self.assertIn("- `rules/` — 52 rule paths from `d098/CLAUDE.md`: gh: HTTP 502", self.readme)

    def test_the_rules_copy_each_file_that_a_rule_file_imports_inside_the_repository(self):
        self.prefetch(rules())
        rules_dir = self.context / "rules"
        self.assertEqual(sorted(str(p.relative_to(rules_dir)) for p in rules_dir.rglob("*") if p.is_file()),
                         ["AGENTS.md", "CLAUDE.md"])
        self.assertIn("`rules/AGENTS.md` — `AGENTS.md` on the base branch `main`, which a rule file imports",
                      self.readme)


if __name__ == "__main__":
    unittest.main()
