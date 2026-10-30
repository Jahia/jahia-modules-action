"""The message of the checks in its three states: passed, passed with retries, and failed with its thread."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from events.ci_checks import template
from events.ci_checks.event import CiChecks, CiError, CiJob
from pull_request import PullRequest

PULL = "https://github.com/Jahia/sitemap/pull/42"
RUN = "https://github.com/Jahia/sitemap/actions/runs/1"


PR = PullRequest(
    "Jahia/sitemap",
    "https://github.com/Jahia/sitemap",
    42,
    "feat: a <b>",
    PULL,
    "open",
    "dev",
    "https://github.com/dev",
    3,
    "main",
    "feat/x",
)


def build_checks(**changes):
    checks = CiChecks(
        workflow="Validate",
        conclusion="success",
        pull=PR,
        commit="ec06bcc",
        commit_url="https://github.com/Jahia/sitemap/commit/ec06bcc",
        attempt=1,
        duration_seconds=87,
        run_url=RUN,
        passed=8,
    )
    return checks._replace(**changes)


def read(blocks):
    """Each block as one line: its type, then its text or the labels of its buttons."""
    lines = []
    for block in blocks:
        if block["type"] == "actions":
            text = " | ".join(button["text"]["text"] for button in block["elements"])
        elif block["type"] == "divider":
            text = ""
        elif block["type"] == "context":
            text = block["elements"][0]["text"]
        else:
            text = block["text"]["text"]
        lines.append(f"{block['type']}: {text}")
    return lines


FACTS = f"*<{RUN}|Validate>*   |   commit <https://github.com/Jahia/sitemap/commit/ec06bcc|ec06bcc>   |   attempt 1   |   1m 27s"


class TestTheMessageOfTheChecks(unittest.TestCase):
    def test_a_passed_run_shows_the_pull_request_and_the_run_with_no_gauge_on_a_green_bar(self):
        message = template.render(build_checks())
        self.assertEqual(message.color, "#2EB67D")
        self.assertEqual(message.fallback, "✅ CI checks passed · Jahia/sitemap#42")
        self.assertEqual(
            read(message.blocks),
            [
                "header: :white_check_mark: CI checks passed",
                f"section: *<https://github.com/Jahia/sitemap|Jahia/sitemap>*\n*feat: a &lt;b&gt;* <{PULL}|#42>",
                (
                    "context: :large_green_circle: *Open* · <https://github.com/dev|dev> wants to merge 3 commits into"
                    " `main` from `feat/x`"
                ),
                "divider: ",
                f"context: {FACTS}\nAll jobs passed",
            ],
        )
        self.assertEqual(message.thread, ())

    def test_a_run_that_passed_after_a_retry_shows_its_gauge_and_its_flaky_job_on_a_yellow_bar(self):
        flaky = CiJob("lint 2/6", "https://j/2", "Run the checks", (), 1)
        message = template.render(build_checks(attempt=2, duration_seconds=182, flaky=(flaky,)))
        self.assertEqual(message.color, "#ECB22E")
        lines = read(message.blocks)
        self.assertEqual(lines[0], "header: :warning: CI checks passed after a retry")
        self.assertIn(
            "attempt 2   |   3m 02s\n" + ":large_green_square:" * 7 + ":large_yellow_square:   8 passed", lines[4]
        )
        self.assertTrue(lines[4].endswith(":large_yellow_square:   8 passed · 1 only after retry"), lines[4])
        self.assertEqual(
            lines[5:],
            [
                "section: *Flaky*",
                "section: :warning: <https://j/2|lint 2/6> › Run the checks",
                "context: failed on attempt 1, passed on attempt 2",
                "context: _Nothing blocking: fix it when you can_",
                "actions: View run",
            ],
        )

    def test_a_failed_run_shows_its_gauge_its_first_error_and_two_buttons_and_details_every_job_in_its_thread(self):
        error = CiError(
            "suite ERROR test_x", "KeyError: 'K'\n\nline 2\nline 3\nline 4", "tests/test_y.py", 87, "https://f", 2
        )
        failed = (CiJob("lint", "https://j/3", "Gate"), CiJob("lint 2/6", "https://j/2", "Run the checks", (error,)))
        message = template.render(build_checks(conclusion="failure", passed=6, failed=failed))
        self.assertEqual(message.color, "#E01E5A")
        self.assertEqual(
            [read(message.blocks)[0], read(message.blocks)[4]],
            [
                "header: :x: CI checks failed",
                f"context: {FACTS}\n"
                + ":large_green_square:" * 6
                + ":large_red_square:" * 2
                + "   6 passed · 2 failed",
            ],
        )
        self.assertEqual(
            read(message.blocks)[5:],
            [
                "section: *Failed*",
                "section: :x: <https://j/2|lint 2/6> › Run the checks",
                "section: ```KeyError: 'K'\nline 2\nline 3```",
                "context: in <https://f|test_y.py:87> · ×2",
                "context: _+ 1 job without errors (gate)_",
                "actions: View logs | View run",
            ],
        )
        self.assertEqual(message.blocks[-1]["elements"][0]["url"], "https://j/2")
        self.assertEqual(
            read(message.thread[0]),
            [
                "section: *:x: <https://j/2|lint 2/6> › Run the checks*",
                "section: suite ERROR test_x",
                "section: ```KeyError: 'K'\nline 2\nline 3```",
                "context: <https://f|test_y.py:87> · ×2",
                "section: *:x: <https://j/3|lint> › Gate* · no error of its own",
            ],
        )

    def test_the_other_failed_jobs_with_errors_are_counted_and_left_to_the_thread(self):
        failed = tuple(CiJob(f"job {n}", f"https://j/{n}", "", (CiError("", f"error {n}"),)) for n in range(3))
        lines = read(template.render(build_checks(conclusion="failure", passed=0, failed=failed)).blocks)
        self.assertIn("context: _+ 2 other failed jobs, in the thread_", lines)

    def test_an_error_with_no_file_names_itself_and_the_thread_counts_the_errors_it_hides(self):
        errors = tuple(CiError("", f"error {n}") for n in range(12))
        failed = (CiJob("build", "https://j/1", "", (CiError("Compile", "cannot find symbol"), *errors)),)
        message = template.render(build_checks(conclusion="failure", passed=0, failed=failed))
        self.assertIn("context: Compile", read(message.blocks))
        self.assertEqual(read(message.thread[0])[-1], f"context: … and 3 more in <{RUN}|the run>")


class TestTheLimitsOfSlack(unittest.TestCase):
    def test_a_failure_with_no_failed_job_posts_no_thread(self):
        message = template.render(build_checks(conclusion="startup_failure", passed=0))
        self.assertEqual(message.thread, ())
        self.assertEqual(read(message.blocks)[-1], "actions: View run")

    def test_each_line_of_an_error_is_cut_so_a_section_stays_under_the_limit_of_slack(self):
        failed = (CiJob("a", "https://j/1", "", (CiError("", "x" * 5000),)),)
        message = template.render(build_checks(conclusion="failure", passed=0, failed=failed))
        self.assertTrue(all(len(block.get("text", {}).get("text", "")) < 3000 for block in message.blocks))
        self.assertIn("section: ```" + "x" * 150 + "```", read(message.blocks))

    def test_the_flaky_jobs_beyond_three_are_counted(self):
        flaky = tuple(CiJob(f"job {n}", f"https://j/{n}", "", (), 1) for n in range(5))
        lines = read(template.render(build_checks(attempt=2, flaky=flaky)).blocks)
        self.assertEqual(sum(line.startswith("section: :warning:") for line in lines), 3)
        self.assertIn(f"context: … and 2 more in <{RUN}|the run>", lines)

    def test_a_thread_keeps_to_the_fifty_blocks_of_slack(self):
        failed = tuple(CiJob(f"job {n}", f"https://j/{n}", "Gate") for n in range(80))
        message = template.render(build_checks(conclusion="failure", passed=0, failed=failed))
        self.assertEqual(len(message.thread[0]), 50)
        self.assertEqual(read(message.thread[0])[-1], f"context: … more in <{RUN}|the run>")


if __name__ == "__main__":
    unittest.main()
