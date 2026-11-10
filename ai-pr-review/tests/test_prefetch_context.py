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
         "@@ -10,1 +11,1 @@\n-old line\n+added by main\n"
         "@@ -20,2 +21,1 @@\n y\n-removed by the pr\n"
         "diff --git a/other.txt b/other.txt\n--- a/other.txt\n+++ b/other.txt\n@@ -1 +1 @@\n-a\n+b\n")
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


def rules(reviews=(OWN, FORGED), status="ahead\n", status_exit=0, files_exit=0):
    pr = {"number": 1, "headRefOid": HEAD, "baseRefName": "main",
          "files": [{"path": "src/a.py", "additions": 1, "deletions": 0}]}
    return [
        {"args": f"pr view {URL} --json number", "out": json.dumps(pr)},
        {"args": f"pr view {URL} --json closingIssuesReferences", "out": '{"closingIssuesReferences": []}'},
        {"args": f"pr view {URL} --comments", "out": ""},
        {"args": f"pr view {URL}", "out": "title: a change\n"},
        {"args": "pr checks", "out": "all checks pass\n"},
        {"args": "pulls/1/files", "exit": files_exit, "err": "gh: HTTP 502\n",
         "out": json.dumps([{"filename": "src/a.py", "additions": 1, "deletions": 0}]) if not files_exit else ""},
        {"args": "pulls/1/reviews", "out": json.dumps(list(reviews))},
        {"args": "pulls/1/comments", "out": "[]"},
        {"args": "reviewThreads", "out": json.dumps(NO_THREAD)},
        {"args": f"compare/main...{HEAD}", "out": PR_DIFF},
        {"args": "api user", "out": "jahia-ai\n"},
        {"args": f"compare/{SINCE}...{HEAD}?per_page=1&page=2", "out": status, "exit": status_exit,
         "err": "gh: Not Found (HTTP 404)\n" if status_exit else ""},
        {"args": f"compare/{SINCE}...{HEAD}", "out": DELTA},
        {"args": "graphql --input", "stdin": "main:AGENTS.md",
         "out": json.dumps({"data": {"repository": {"f0": {"text": "the rules of the agents\n"}}}})},
        {"args": "graphql --input", "stdin": "main:CLAUDE.md",
         "out": json.dumps({"data": {"repository": {"f0": {"text": "see @./AGENTS.md and @../../escape.md\n"},
                                                    "f1": None, "f2": None}}})},
    ]


class TestThePrefetch(unittest.TestCase):
    def prefetch(self, scenario):
        self.gh = FakeGh(self, scenario)
        self.context = self.gh.dir / "context"
        done = self.gh.run("prefetch-context.py", str(self.context), env={"PR_URL": URL, "MARKER": MARKER})
        self.assertEqual(done.returncode, 0, done.stderr)
        self.readme = (self.context / "README.md").read_text(encoding="utf-8")
        return done

    def test_the_diff_is_pinned_to_the_head_that_the_step_prints(self):
        done = self.prefetch(rules())
        self.assertEqual((self.context / "diff.patch").read_text(encoding="utf-8"), PR_DIFF)
        self.assertEqual(done.stdout.strip(), HEAD)
        self.assertEqual(self.gh.calls("pr diff"), [])

    def test_the_delta_keeps_the_hunks_of_the_pull_request_since_the_own_review(self):
        self.prefetch(rules())
        delta = (self.context / "delta.patch").read_text(encoding="utf-8")
        self.assertIn("+added by the pr", delta)
        self.assertIn("-removed by the pr", delta)
        self.assertNotIn("added by main", delta)
        self.assertNotIn("other.txt", delta)
        self.assertIn(f"read commit `{SINCE}`", self.readme)
        self.assertIn("This run posts as `jahia-ai`", self.readme)

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

    def test_a_partial_list_of_files_keeps_every_hunk_of_the_delta(self):
        self.prefetch(rules(files_exit=1))
        delta = (self.context / "delta.patch").read_text(encoding="utf-8")
        self.assertIn("added by main", delta)
        self.assertIn("other.txt", delta)
        self.assertIn("`changed files`", self.readme)

    def test_the_rules_copy_each_file_that_a_rule_file_imports_inside_the_repository(self):
        self.prefetch(rules())
        rules_dir = self.context / "rules"
        self.assertEqual(sorted(str(p.relative_to(rules_dir)) for p in rules_dir.rglob("*") if p.is_file()),
                         ["AGENTS.md", "CLAUDE.md"])
        self.assertIn("`rules/AGENTS.md` — `AGENTS.md` on the base branch `main`, which a rule file imports",
                      self.readme)


if __name__ == "__main__":
    unittest.main()
