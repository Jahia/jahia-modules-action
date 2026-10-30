"""The message of a completed run of the checks of a pull request, in three states: passed, passed after a
retry, and failed. It opens on the header and the part of the pull request that `templates/` builds, then shows
the run: its facts and the count of its jobs, behind a gauge when a job failed or passed after a retry. A retry
adds each flaky job, and a failure adds each failed job with its first error and two buttons. The thread of a
failure lists every error."""

import os

from blocks import (
    build_buttons,
    build_code,
    build_context,
    build_divider,
    build_line,
    build_link,
    build_rich_text,
    build_word,
    escape,
)
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
_JOBS_SHOWN = 5
_THREAD_ERRORS = 10
_DETAIL_LINES = 3
# Slack refuses a long block, so each line of an error is cut
_LINE_CHARS = 150
_TITLE_CHARS = 150


def render(checks: CiChecks) -> SlackMessage:
    state = checks.state
    color, emoji, icon, title = _STATES[state]
    body = [*pull_request.show(checks.pull), _show_run(checks)]
    thread = ()
    if state == CiState.UNSTABLE:
        body += _show_retry(checks)
    elif state == CiState.FAILED:
        body += _show_failure(checks)
        thread = _show_thread(checks)
    return message.compose(color, emoji, icon, title, checks.pull.reference, body, thread)


# The run: its facts, then the gauge of its jobs and their count


def _show_run(checks: CiChecks) -> dict:
    facts = "   |   ".join(
        [
            f"*<{checks.run_url}|{escape(checks.workflow)}>*",
            f"commit <{checks.commit_url}|{checks.commit}>",
            f"attempt {checks.attempt}",
            _format_duration(checks.duration_seconds),
        ]
    )
    # One block carries both lines, because Slack puts a wide space between blocks
    count = _format_count(checks)
    count = f"{_draw_squares(checks)}   {count}" if checks.failed or checks.flaky else count
    return build_context(f"{facts}\n{count}")


def _draw_squares(checks: CiChecks) -> str:
    # One square for each job, which a context block draws at the size of its text
    steady = checks.passed - len(checks.flaky)
    return (
        ":large_green_square:" * steady
        + ":large_yellow_square:" * len(checks.flaky)
        + ":large_red_square:" * len(checks.failed)
    )


def _format_count(checks: CiChecks) -> str:
    if checks.failed:
        return f"{checks.passed} passed · {len(checks.failed)} failed"
    if checks.flaky:
        return f"{checks.passed} passed · {len(checks.flaky)} only after retry"
    if checks.state == CiState.FAILED:
        # A run can fail with no failed job, such as on a startup failure
        return f"{checks.passed} passed · the run ended in `{checks.conclusion}`"
    return "All jobs passed"


# The detail of a retry: each flaky job, its step in bold and the attempts


def _show_retry(checks: CiChecks) -> list[dict]:
    groups = [
        [
            build_line(build_link(job.url, job.name)),
            build_line(
                build_word(job.step or "unknown step", bold=True),
                build_word(f"   failed on attempt {job.failed_attempt}, passed on attempt {checks.attempt}"),
            ),
        ]
        for job in checks.flaky[:_FLAKY_SHOWN]
    ]
    blocks = [build_divider(), build_rich_text(*_separate(groups))]
    more = len(checks.flaky) - _FLAKY_SHOWN
    if more > 0:
        blocks.append(build_context(f"… and {more} more in <{checks.run_url}|the run>"))
    return [
        *blocks,
        build_context("_Nothing blocking: fix it when you can_"),
        build_buttons(("View run", checks.run_url)),
    ]


# The detail of a failure: each failed job, its step in bold and its first error, the jobs with errors first


def _show_failure(checks: CiChecks) -> list[dict]:
    if not checks.failed:
        return [build_divider(), build_buttons(("View run", checks.run_url))]
    jobs = _sort(checks.failed)
    gate = any(job.errors for job in jobs)
    groups = [_show_job(job, job.errors[:1], gate) for job in jobs[:_JOBS_SHOWN]]
    blocks = [build_divider(), build_rich_text(*_separate(groups))]
    more = len(jobs) - _JOBS_SHOWN
    if more > 0:
        blocks.append(build_context(f"… and {more} more failed job{'s' if more > 1 else ''} in the thread"))
    return [*blocks, build_buttons(("View logs", jobs[0].url), ("View run", checks.run_url), primary="View logs")]


# The thread of a failure: each failed job with every error, up to a budget of errors


def _show_thread(checks: CiChecks) -> tuple[list[dict], ...]:
    # A failure with no failed job, such as a startup failure, has no thread
    if not checks.failed:
        return ()
    groups, budget = [], _THREAD_ERRORS
    gate = any(job.errors for job in checks.failed)
    for job in _sort(checks.failed):
        errors = job.errors[:budget]
        budget -= len(errors)
        groups.append(_show_job(job, errors, gate))
    blocks = [build_rich_text(*_separate(groups))]
    overflow = sum(len(job.errors) for job in checks.failed) - _THREAD_ERRORS
    if overflow > 0:
        blocks.append(build_context(f"… and {overflow} more in <{checks.run_url}|the run>"))
    return (blocks,)


# A failed job: the job, its step in bold, then each error, its place and its text in a block of code


def _show_job(job: CiJob, errors: tuple[CiError, ...], gate: bool) -> list[dict]:
    elements = [build_line(build_link(job.url, job.name))]
    step = build_word(job.step or "unknown step", bold=True)
    if not job.errors:
        # A job with no error of its own beside a job with errors is a gate, such as a job that needs the others
        note = "no error of its own, the job is a gate" if gate else "no error in its annotations or its log"
        return [*elements, build_line(step, build_word(f"   {note}"))]
    for index, error in enumerate(errors):
        # The place of the first error shares the line of the step
        place = _show_place(error)
        line = [step, *place] if index == 0 else place
        elements += [build_line(*line)] if line else []
        detail = _cut_detail(error.detail)
        elements.append(build_code(f"{error.title[:_TITLE_CHARS]}\n{detail}" if error.title else detail))
    # A thread whose budget of errors is spent shows the step of the job alone
    return elements if errors else [*elements, build_line(step)]


def _show_place(error: CiError) -> list[dict]:
    # The file and the line of the error, then its count, or nothing
    parts = []
    if error.file:
        place = f"{os.path.basename(error.file)}:{error.line}" if error.line else os.path.basename(error.file)
        parts += [build_word("   in "), build_link(error.url, place) if error.url else build_word(place)]
    if error.occurrences > 1:
        parts.append(build_word(f"   ×{error.occurrences}"))
    return parts


def _sort(jobs: tuple[CiJob, ...]) -> list[CiJob]:
    # The jobs with errors come first, and a gate last
    return sorted(jobs, key=lambda job: not job.errors)


def _separate(groups: list[list[dict]]) -> list[dict]:
    # A line that contains a newline draws the blank line between the groups
    elements = []
    for group in groups:
        elements += [build_line(build_word("\n"))] if elements else []
        elements += group
    return elements


def _cut_detail(detail: str) -> str:
    return "\n".join([line[:_LINE_CHARS] for line in detail.splitlines() if line.strip()][:_DETAIL_LINES])


def _format_duration(seconds: int) -> str:
    return f"{seconds // 60}m {seconds % 60:02d}s" if seconds >= 60 else f"{seconds}s"
