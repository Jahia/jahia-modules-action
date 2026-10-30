"""The message of the checks in its three states: passed, passed with retries, and failed with its thread."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import test_pull_request
from events.ci_checks import template
from events.ci_checks.event import CiChecks, CiError, CiJob

PULL = "https://github.com/Jahia/sitemap/pull/42"
RUN = "https://github.com/Jahia/sitemap/actions/runs/1"
FACTS = f"*<{RUN}|Validate>*   |   commit <https://github.com/Jahia/sitemap/commit/ec06bcc|ec06bcc>   |   attempt 1   |   1m 27s"
PR = test_pull_request.read()


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
        elif block["type"] == "rich_text":
            lines += [f"rich: {line}" for line in read_rich(block)]
            continue
        elif block["type"] == "context":
            text = block["elements"][0]["text"]
        else:
            text = block["text"]["text"]
        lines.append(f"{block['type']}: {text}")
    return lines


def read_rich(block):
    """Each element of a rich text as one line: the words and links of a line, or a block of code in fences."""
    lines = []
    for element in block["elements"]:
        text = "".join(part["text"] for part in element["elements"])
        lines.append(f"```{text}```" if element["type"] == "rich_text_preformatted" else text)
    return lines


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

    def test_a_run_that_passed_after_a_retry_shows_each_flaky_job_with_its_step_on_a_yellow_bar(self):
        flaky = CiJob("lint 2/6", "https://j/2", "Run the checks", (), 1)
        message = template.render(build_checks(attempt=2, duration_seconds=182, flaky=(flaky,)))
        self.assertEqual(message.color, "#ECB22E")
        lines = read(message.blocks)
        self.assertEqual(lines[0], "header: :warning: CI checks passed after a retry")
        self.assertIn(
            "attempt 2   |   3m 02s\n" + ":large_green_square:" * 7 + ":large_yellow_square:   8 passed", lines[4]
        )
        self.assertEqual(
            lines[5:],
            [
                "divider: ",
                "rich: lint 2/6",
                "rich: Run the checks   failed on attempt 1, passed on attempt 2",
                "context: _Nothing blocking: fix it when you can_",
                "actions: View run",
            ],
        )

    def test_a_failed_run_shows_each_failed_job_with_its_step_and_its_first_error_and_details_every_error_in_its_thread(
        self,
    ):
        error = CiError(
            "suite ERROR test_x", "KeyError: 'K'\n\nline 2\nline 3\nline 4", "tests/test_y.py", 87, "https://f", 2
        )
        failed = (CiJob("lint", "https://j/3", "Gate"), CiJob("lint 2/6", "https://j/2", "Run the checks", (error,)))
        message = template.render(build_checks(conclusion="failure", passed=6, failed=failed))
        self.assertEqual(message.color, "#E01E5A")
        self.assertEqual(
            read(message.blocks)[4:],
            [
                f"context: {FACTS}\n"
                + ":large_green_square:" * 6
                + ":large_red_square:" * 2
                + "   6 passed · 2 failed",
                "divider: ",
                "rich: lint 2/6",
                "rich: Run the checks   in test_y.py:87   ×2",
                "rich: ```suite ERROR test_x\nKeyError: 'K'\nline 2\nline 3```",
                "rich: \n",
                "rich: lint",
                "rich: Gate   no error of its own, the job is a gate",
                "actions: View logs | View run",
            ],
        )
        self.assertEqual(message.blocks[-1]["elements"][0]["url"], "https://j/2")
        self.assertEqual(
            read(message.thread[0]),
            [
                "rich: lint 2/6",
                "rich: Run the checks   in test_y.py:87   ×2",
                "rich: ```suite ERROR test_x\nKeyError: 'K'\nline 2\nline 3```",
                "rich: \n",
                "rich: lint",
                "rich: Gate   no error of its own, the job is a gate",
            ],
        )

    def test_the_thread_shows_every_error_up_to_its_budget_then_the_step_of_each_job_left(self):
        errors = tuple(CiError("", f"error {n}") for n in range(12))
        failed = (CiJob("build", "https://j/1", "Compile", errors), CiJob("test", "https://j/2", "Test", errors[:1]))
        message = template.render(build_checks(conclusion="failure", passed=0, failed=failed))
        thread = read(message.thread[0])
        self.assertEqual(sum(line.startswith("rich: ```error") for line in thread), 10)
        self.assertEqual(thread[-3:], ["rich: test", "rich: Test", f"context: … and 3 more in <{RUN}|the run>"])

    def test_a_failed_job_with_no_error_beside_no_job_with_errors_is_no_gate(self):
        failed = (CiJob("build", "https://j/1", "Compile"),)
        lines = read(template.render(build_checks(conclusion="failure", passed=0, failed=failed)).blocks)
        self.assertIn("rich: Compile   no error in its annotations or its log", lines)

    def test_the_failed_jobs_beyond_five_are_left_to_the_thread(self):
        failed = tuple(CiJob(f"job {n}", f"https://j/{n}", "", (CiError("", f"error {n}"),)) for n in range(7))
        lines = read(template.render(build_checks(conclusion="failure", passed=0, failed=failed)).blocks)
        self.assertEqual(sum(line.startswith("rich: job ") for line in lines), 5)
        self.assertIn("context: … and 2 more failed jobs in the thread", lines)


class TestTheLimitsOfSlack(unittest.TestCase):
    def test_a_failure_with_no_failed_job_names_the_conclusion_and_posts_no_thread(self):
        message = template.render(build_checks(conclusion="startup_failure", passed=0))
        self.assertEqual(message.thread, ())
        lines = read(message.blocks)
        self.assertEqual(lines[4], f"context: {FACTS}\n0 passed · the run ended in `startup_failure`")
        self.assertEqual(lines[-1], "actions: View run")

    def test_each_line_of_an_error_is_cut_so_a_block_stays_under_the_limit_of_slack(self):
        failed = (CiJob("a", "https://j/1", "", (CiError("", "x" * 5000),)),)
        lines = read(template.render(build_checks(conclusion="failure", passed=0, failed=failed)).blocks)
        self.assertIn("rich: ```" + "x" * 150 + "```", lines)

    def test_the_flaky_jobs_beyond_three_are_counted(self):
        flaky = tuple(CiJob(f"job {n}", f"https://j/{n}", "", (), 1) for n in range(5))
        lines = read(template.render(build_checks(attempt=2, flaky=flaky)).blocks)
        self.assertEqual(sum(line.startswith("rich: job ") for line in lines), 3)
        self.assertIn(f"context: … and 2 more in <{RUN}|the run>", lines)


if __name__ == "__main__":
    unittest.main()
