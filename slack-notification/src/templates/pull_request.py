"""The part of the message of an event of a pull request: the repository, the title and the state of the pull
request, as its page on GitHub shows them, then a separator."""

from blocks import build_context, build_divider, build_section, escape
from pull_request import PullRequest

# The circle of the state of a pull request, its label, and the verb of its line
_STATES = {
    "open": (":large_green_circle:", "Open", "wants to merge"),
    "draft": (":white_circle:", "Draft", "wants to merge"),
    "merged": (":large_purple_circle:", "Merged", "merged"),
    "closed": (":red_circle:", "Closed", "wanted to merge"),
}


def show(pull: PullRequest) -> list[dict]:
    circle, label, verb = _STATES[pull.state]
    commits = "commit" if pull.commits == 1 else "commits"
    return [
        # One section carries the repository and the title, because Slack puts a wide space between blocks
        build_section(
            f"*<{pull.repository_url}|{escape(pull.repository)}>*\n*{escape(pull.title)}* <{pull.url}|#{pull.number}>"
        ),
        build_context(
            f"{circle} *{label}* · <{pull.author_url}|{escape(pull.author)}> {verb} {pull.commits} {commits}"
            f" into `{escape(pull.base)}` from `{escape(pull.head)}`"
        ),
        build_divider(),
    ]
