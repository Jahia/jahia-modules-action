"""The message of a completed run of the checks of a pull request, in three states: passed, passed after a
retry, and failed. The three share one skeleton, and the graver the state, the longer the message: a
failure adds its first error and three buttons, and its thread lists every error."""

import os

from blocks import build_buttons, build_code, build_context, build_header, build_section, escape
from slack import SlackMessage

from events.ci_checks.event import CiChecks, CiError, CiJob, CiState

# The color of the bar, the emoji of the header and the one of the text that the system shows, by state
_STATES = {
    CiState.PASSED: ("#2EB67D", ":white_check_mark:", "✅"),
    CiState.UNSTABLE: ("#ECB22E", ":warning:", "⚠️"),
    CiState.FAILED: ("#E01E5A", ":x:", "❌"),
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
    color, emoji, icon = _STATES[state]
    total = checks.passed + len(checks.failed)
    title = {
        CiState.PASSED: f"CI checks passed · {checks.passed} of {total} jobs",
        CiState.UNSTABLE: "CI checks passed after a retry",
        CiState.FAILED: f"CI checks failed · {len(checks.failed)} of {total} jobs",
    }[state]
    facts = [
        f"`{escape(checks.branch)}`",
        f"<{checks.commit_url}|{checks.commit}>",
        escape(checks.workflow),
        f"attempt {checks.attempt}",
        _format_duration(checks.duration_seconds),
    ]
    blocks = [
        build_header(f"{emoji} {title}"),
        build_section(f"<{checks.pull_url}|{checks.reference}> *{escape(checks.pull_title)}*"),
        build_context(" · ".join(facts)),
    ]
    count = _count(checks)
    # One block carries the squares and the count, because Slack puts a space between two blocks
    blocks.append(build_context(f"{_draw_squares(checks)}\n*{count}*"))
    thread = ()
    if state == CiState.UNSTABLE:
        blocks += _show_flaky(checks)
    elif state == CiState.FAILED:
        blocks += _show_failure(checks)
        detail = _detail_failures(checks)
        # A failure with no failed job, such as a startup failure, has no detail for a thread
        thread = (detail,) if detail else ()
    return SlackMessage(color, f"{icon} {title} · {checks.reference}", blocks, thread)


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
        # A failed job with no error of its own beside one that has errors is a gate
        gate = any(job.errors for job in checks.failed) and not all(job.errors for job in checks.failed)
        return f"{checks.passed} passed · {len(checks.failed)} failed" + (" (incl. gate)" if gate else "")
    if checks.flaky:
        return f"{checks.passed} passed · {len(checks.flaky)} only after retry"
    return "All jobs passed"


def _format_job(job: CiJob) -> str:
    return f"<{job.url}|{escape(job.name)}>" + (f" › {escape(job.step)}" if job.step else "")


def _show_flaky(checks: CiChecks) -> list[dict]:
    blocks = []
    for job in checks.flaky[:_FLAKY_SHOWN]:
        blocks += [
            build_section(f"Flaky: {_format_job(job)}"),
            build_code(f"failed on attempt {job.failed_attempt}, passed on attempt {checks.attempt}"),
        ]
    more = len(checks.flaky) - _FLAKY_SHOWN
    if more > 0:
        blocks.append(build_context(f"… and {more} more in <{checks.run_url}|the run>"))
    return [
        *blocks,
        build_context("Nothing blocking: fix it when you can"),
        build_buttons(("View run", checks.run_url)),
    ]


def _show_failure(checks: CiChecks) -> list[dict]:
    job = next((one for one in checks.failed if one.errors), checks.failed[0]) if checks.failed else None
    blocks = []
    if job:
        blocks.append(build_section(f"✕ {_format_job(job)}"))
        if job.errors:
            error = job.errors[0]
            where = _locate(error, linked=False, named=True)
            blocks += [build_code(_cut_detail(error.detail)), *([build_context(where)] if where else [])]
    links = [("View run", checks.run_url), ("Open PR", checks.pull_url)]
    if job:
        links.insert(0, ("View logs", job.url))
    return [*blocks, build_buttons(*links, primary="View logs")]


def _detail_failures(checks: CiChecks) -> list[dict]:
    blocks = []
    budget = _THREAD_ERRORS
    for job in sorted(checks.failed, key=lambda one: not one.errors):
        blocks.append(build_section(f"*✕ {_format_job(job)}*" + ("" if job.errors else " · no error of its own")))
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
