"""Render a GitHub release body as the Slack payload announcing that release.

Usage: render_slack_payload.py <repository> <release-tag> <major-tag> < body.md

Reads the release body (GitHub-flavoured Markdown) on stdin and prints, on a
single line, the JSON payload for an incoming webhook: a header section naming
the release and the major tag that now points at it, then the converted notes.

Slack's mrkdwn is not Markdown — bold is *one* star, links are <url|label> and
headings do not exist — so the body is translated rather than passed through.
"""
import json
import re
import sys

# A section block's text tops out at 3000 characters; stay clear of the edge so
# the truncation footer always fits.
SECTION_LIMIT = 2800

repository, release_tag, major_tag = sys.argv[1], sys.argv[2], sys.argv[3]
release_url = f'https://github.com/{repository}/releases/tag/{release_tag}'


def to_mrkdwn(body):
    text = body.replace('\r\n', '\n').replace('\r', '\n')
    # The generated-notes marker and any other HTML comment are invisible on
    # GitHub but would show up verbatim in Slack.
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    # Escape before emitting any link of our own, or the < and > we are about to
    # write get escaped too and the links arrive as text.
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    text = re.sub(r'(?m)^#{1,6}\s*(.+?)\s*$', r'*\1*', text)
    # Before the list bullets below, which would otherwise consume the stars.
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text, flags=re.S)
    text = re.sub(r'\[([^\]]+)\]\((https?://[^\s)]+)\)', r'<\2|\1>', text)
    # Bare pull-request and compare URLs carry no information in their path that
    # a reader needs; label them so a line of notes stays readable.
    text = re.sub(
        r'(?<![|<])https://github\.com/([\w.-]+/[\w.-]+)/pull/(\d+)',
        lambda m: f'<https://github.com/{m[1]}/pull/{m[2]}|#{m[2]}>', text)
    text = re.sub(
        r'(?<![|<])https://github\.com/([\w.-]+/[\w.-]+)/compare/(\S+)',
        lambda m: f'<https://github.com/{m[1]}/compare/{m[2]}|{m[2]}>', text)
    text = re.sub(r'(?m)^\s*[*-]\s+', '• ', text)
    # The header block already says which release this is.
    text = re.sub(r"(?m)^\*What's Changed\*\s*$", '', text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()


notes = to_mrkdwn(sys.stdin.read())
if len(notes) > SECTION_LIMIT:
    notes = (notes[:SECTION_LIMIT].rsplit('\n', 1)[0]
             + f'\n\n… <{release_url}|read the full release notes>')

blocks = [{
    'type': 'section',
    'text': {
        'type': 'mrkdwn',
        'text': f':rocket: *<{release_url}|{repository} {release_tag}>* released'
                f' — the `{major_tag}` tag now points to it.',
    },
}]
if notes:
    blocks.append({'type': 'section', 'text': {'type': 'mrkdwn', 'text': notes}})

print(json.dumps({'blocks': blocks}))
