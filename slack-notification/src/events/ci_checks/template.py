"""The message of a completed run of the checks of a pull request, in three states: passed, passed after a
retry, and failed. It opens on the header and the part of the pull request that `templates/` builds, then shows
the run and the gauge of its jobs. A run that passed after a retry adds its flaky jobs as the detail, and a
failure adds its first error and two buttons, and its thread lists every error."""

import os

from blocks import build_buttons, build_code, build_context, build_section, escape
from slack import SlackMessage
from templates import message, pull_request

from events.ci_checks.event import CiChecks, CiError, CiJob, CiState

# The color of the bar, the emoji of the header, the one of the text that the system shows, and the header
_STATES = {
    CiState.PASSED: ("#2EB67D", ":white_check_mark:", "✅", "CI checks passed"),
    CiState.UNSTABLE: ("#ECB22E", ":warning:", "⚠️", "CI checks passed after a retry"),
    CiState.FAILED: ("#E01E5A", ":x:", "❌", "CI checks failed"),
}
_FLAKY_SHOWN = 3
_THREAD_ERRORS = 10
# The most blocks that Slack accepts in a message
_MAX_BLOCKS = 50
_DETAIL_LINES = 3
# Slack refuses a long section, and an escape makes a line longer
_LINE_CHARS = 150
_TITLE_CHARS = 150


def render(checks: CiChecks) -> SlackMessage:
    state = checks.state
    color, emoji, icon, title = _STATES[state]
    body = [*pull_request.show(checks.pull), _show_run(checks)]
    detail, thread = [], ()
    if state == CiState.UNSTABLE:
        detail = _show_flaky(checks)
    elif state == CiState.FAILED:
        detail = _show_failure(checks)
        replies = _detail_failures(checks)
        # A failure with no failed job, such as a startup failure, has no detail for a thread
        thread = (replies,) if replies else ()
    return message.compose(color, emoji, icon, title, checks.pull.reference, body, detail, thread)


def _show_run(checks: CiChecks) -> dict:
    facts = "   |   ".join(
        [
            f"*<{checks.run_url}|{escape(checks.workflow)}>*",
            f"commit <{checks.commit_url}|{checks.commit}>",
            f"attempt {checks.attempt}",
            _format_duration(checks.duration_seconds),
        ]
    )
    # The squares of the jobs follow the line of a run with a job that failed or passed after a retry, and one block
    # carries the lines, because Slack puts a space between two blocks
    squares = [_draw_squares(checks)] if checks.failed or checks.flaky else []
    return build_context("\n".join([facts, *squares, _count(checks)]))


def _draw_squares(checks: CiChecks) -> str:
    # One square for each job, which a context block draws at the size of its text
    steady = checks.passed - len(checks.flaky)
    return (
        ":large_green_square:" * steady
        + ":large_yellow_square:" * len(checks.flaky)
        + ":large_red_square:" * len(checks.failed)
    )


def _count(checks: CiChecks) -> str:
    if checks.failed:
        return f"{checks.passed} passed · {len(checks.failed)} failed"
    if checks.flaky:
        return f"{checks.passed} passed · {len(checks.flaky)} only after retry"
    return "All jobs passed"


def _format_job(job: CiJob) -> str:
    return f"<{job.url}|{escape(job.name)}>" + (f" › {escape(job.step)}" if job.step else "")


def _show_flaky(checks: CiChecks) -> list[dict]:
    blocks = [build_section("*Flaky*")]
    for job in checks.flaky[:_FLAKY_SHOWN]:
        blocks += [
            build_section(f":warning: {_format_job(job)}"),
            build_context(f"failed on attempt {job.failed_attempt}, passed on attempt {checks.attempt}"),
        ]
    more = len(checks.flaky) - _FLAKY_SHOWN
    if more > 0:
        blocks.append(build_context(f"… and {more} more in <{checks.run_url}|the run>"))
    return [
        *blocks,
        build_context("_Nothing blocking: fix it when you can_"),
        build_buttons(("View run", checks.run_url)),
    ]


def _show_failure(checks: CiChecks) -> list[dict]:
    # The first failed job with errors, else the first failed job, then a note for each other one
    with_errors = [job for job in checks.failed if job.errors]
    job = with_errors[0] if with_errors else checks.failed[0] if checks.failed else None
    if not job:
        return [build_buttons(("View run", checks.run_url))]
    blocks = [build_section("*Failed*"), build_section(f":x: {_format_job(job)}")]
    if job.errors:
        error = job.errors[0]
        where = _locate(error, linked=True, named=True)
        blocks.append(build_code(_cut_detail(error.detail)))
        if where:
            blocks.append(build_context(f"in {where}" if error.file else where))
    others = len(with_errors) - 1
    # A failed job with no error of its own beside one that has errors is a gate
    gates = len(checks.failed) - len(with_errors) if with_errors else 0
    if others > 0:
        blocks.append(build_context(f"_+ {others} other failed job{'s' if others > 1 else ''}, in the thread_"))
    if gates > 0:
        blocks.append(build_context(f"_+ {gates} job{'s' if gates > 1 else ''} without errors (gate)_"))
    return [*blocks, build_buttons(("View logs", job.url), ("View run", checks.run_url), primary="View logs")]


def _detail_failures(checks: CiChecks) -> list[dict]:
    blocks = []
    budget = _THREAD_ERRORS
    for job in sorted(checks.failed, key=lambda one: not one.errors):
        blocks.append(build_section(f"*:x: {_format_job(job)}*" + ("" if job.errors else " · no error of its own")))
        for error in job.errors[:budget]:
            where = _locate(error, linked=True, named=False)
            blocks += [
                *([build_section(escape(error.title[:_TITLE_CHARS]))] if error.title else []),
                build_code(_cut_detail(error.detail)),
                *([build_context(where)] if where else []),
            ]
        budget -= min(budget, len(job.errors))
    overflow = sum(len(job.errors) for job in checks.failed) - _THREAD_ERRORS
    if overflow > 0:
        blocks.append(build_context(f"… and {overflow} more in <{checks.run_url}|the run>"))
    if len(blocks) > _MAX_BLOCKS:
        blocks = [*blocks[: _MAX_BLOCKS - 1], build_context(f"… more in <{checks.run_url}|the run>")]
    return blocks


def _cut_detail(detail: str) -> str:
    return "\n".join([line[:_LINE_CHARS] for line in detail.splitlines() if line.strip()][:_DETAIL_LINES])


def _locate(error: CiError, *, linked: bool, named: bool) -> str:
    # The file and the line of the error, or its title when `named`, then its count, or empty
    parts = []
    if error.file:
        place = f"{os.path.basename(error.file)}:{error.line}" if error.line else os.path.basename(error.file)
        parts.append(f"<{error.url}|{escape(place)}>" if linked and error.url else escape(place))
    elif named and error.title:
        parts.append(escape(error.title[:_TITLE_CHARS]))
    if error.occurrences > 1:
        parts.append(f"×{error.occurrences}")
    return " · ".join(parts)


def _format_duration(seconds: int) -> str:
    return f"{seconds // 60}m {seconds % 60:02d}s" if seconds >= 60 else f"{seconds}s"
