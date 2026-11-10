"""Submit (or render) the structured review file the agent produced.

Usage: submit-review.py post <review-file> <pr-url> [<pr.json of the context>]
       submit-review.py render <review-file>

The review file is the one the ci mode of the Cortex skill pr-review writes, in
the shape of its contract (`.claude/skills/pr-review/assets/ci-review.md` in
Jahia/cortex): {"contract": "v1", "event", "human_review", "body": "<markdown>",
"comments": [{"path", "line", "side", "start_line"?, "start_side"?, "body"}]}.
A file of any other contract version is refused, in both modes: Cortex takes
the next version when the shape changes, and guessing at a shape this script
does not know would post a wrong review.

"post" submits ONE pull-request review via the GitHub API, always as COMMENT,
with the findings attached as inline comments on the lines in question (a
comment of several lines keeps its start_line/start_side). The review names as
its commit the head that the prefetch read, from the pr.json of the context, so
that the next re-review reads its delta from that commit. If GitHub rejects
the payload (typically an anchor on a line that is not part of the diff), the review is
re-submitted body-only with the findings folded into the body, then on the head
of the pull request — a bad anchor never loses the review. "render" prints the
review as markdown (review mode: job summary and artifact reading).

"post" requires GH_TOKEN with pull-request write on the repository.
"""
import json
import re
import subprocess
import sys
from urllib.parse import quote

# The contract versions of the review file this script reads.
KNOWN_CONTRACTS = ('v1',)

mode, path = sys.argv[1], sys.argv[2]
try:
    with open(path, encoding='utf-8') as fh:
        review = json.load(fh)
    body = review['body']
    comments = review.get('comments', [])
    contract = review.get('contract')
except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as error:
    print(f'::error::The agent produced an invalid review file ({error}) — '
          'nothing was posted; the file is in the run artifact and the review '
          'request stays pending (re-request to retry)')
    sys.exit(1)
if contract not in KNOWN_CONTRACTS:
    print(f'::error title=Unknown review contract::The review file states contract {contract!r}, '
          f'and this action reads {", ".join(KNOWN_CONTRACTS)} — nothing was posted. The skill '
          'pr-review of the Cortex ref this run checked out writes another shape: pin cortex_ref '
          'to a ref that writes a known contract, or update ai-pr-review to read the new one. '
          'The file is in the run artifact and the review request stays pending.')
    sys.exit(1)


def fold(body, comments):
    """Merge the inline comments into the body (fallback and render layout)."""
    if not comments:
        return body
    lines = [body, '', '### Findings']
    for c in comments:
        lines.append('')
        where = (f"{c['start_line']}-{c['line']}" if c.get('start_line') is not None
                 else c['line'])
        lines.append(f"`{c['path']}:{where}` — {c['body']}")
    return '\n'.join(lines)


if mode == 'render':
    print(fold(body, comments))
    sys.exit(0)

pr_url = sys.argv[3]
owner, repo, number = re.search(r'([^/]+)/([^/]+)/pull/(\d+)$', pr_url).groups()
endpoint = f'repos/{owner}/{repo}/pulls/{number}/reviews'


def post(payload):
    return subprocess.run(['gh', 'api', '-X', 'POST', endpoint, '--input', '-'],
                          input=json.dumps(payload).encode(), capture_output=True)


if review.get('event', 'COMMENT') != 'COMMENT':
    print(f"::warning::The review file asks for {review['event']!r} — submitting as COMMENT, "
          'because the review never approves and never blocks the pull request')
event = 'COMMENT'

# The agent's confidence call, mirrored as a PR label after the review is submitted.
LABELS = {
    'not-needed': ('🤖 AI-only review OK', '0E8A16',
                   'The AI reviewer sees no need for a person to read this PR'),
    'recommended': ('🤖 Human review recommended', 'FBCA04',
                    'The AI reviewer suggests a human pass on this PR'),
    'required': ('🤖 Human review required', 'B60205',
                 'The AI reviewer wants a human decision on this PR'),
}
human = review.get('human_review', 'recommended')
if human not in LABELS:
    print(f'::warning::Unexpected human_review {human!r} — treating it as "recommended"')
    human = 'recommended'


def gh(args, data=None):
    body_bytes = json.dumps(data).encode() if data is not None else None
    return subprocess.run(['gh', 'api'] + args, input=body_bytes, capture_output=True)


def apply_label():
    """Mirror the recommendation as a PR label. Best-effort: never fails the review."""
    name, color, description = LABELS[human]
    # Create the label when the repo does not have it yet (422 when it already exists).
    gh(['-X', 'POST', f'repos/{owner}/{repo}/labels', '--input', '-'],
       {'name': name, 'color': color, 'description': description})
    # The POST leaves an existing label as it is, so the PATCH brings its description up to date.
    gh(['-X', 'PATCH', f'repos/{owner}/{repo}/labels/{quote(name, safe="")}', '--input', '-'],
       {'color': color, 'description': description})
    for key, (other, _, _) in LABELS.items():
        if key != human:
            gh(['-X', 'DELETE',
                f'repos/{owner}/{repo}/issues/{number}/labels/{quote(other, safe="")}'])
    added = gh(['-X', 'POST', f'repos/{owner}/{repo}/issues/{number}/labels', '--input', '-'],
               {'labels': [name]})
    if added.returncode == 0:
        print(f'Recommendation label applied: {name}')
    else:
        print('::warning::Could not apply the recommendation label: '
              + added.stderr.decode(errors='replace')[-200:])


def anchor(comment):
    """The GitHub review comment of one finding; a multi-line one keeps its start."""
    entry = {'path': comment['path'], 'line': int(comment['line']),
             'side': comment.get('side', 'RIGHT'), 'body': comment['body']}
    if comment.get('start_line') is not None:
        entry['start_line'] = int(comment['start_line'])
        entry['start_side'] = comment.get('start_side', entry['side'])
    return entry


def reviewed_head():
    """The head commit that the prefetch read, or None when the pr.json of the context has none."""
    try:
        with open(sys.argv[4], encoding='utf-8') as fh:
            return json.load(fh)['headRefOid']
    except (IndexError, OSError, ValueError, KeyError, TypeError):
        return None


reviewed = reviewed_head()
pinned = {'commit_id': reviewed} if reviewed else {}
folded = {'event': event, 'body': fold(body, comments)}
attempts = []
if comments:
    attempts.append(({'event': event, 'body': body, 'comments': [anchor(c) for c in comments], **pinned},
                     f'with {len(comments)} inline comment(s)'))
attempts.append(({**folded, **pinned}, 'body-only, with the findings folded in'))
if pinned:
    # A force-push during the run removes the commit that the prefetch read, and GitHub refuses it.
    attempts.append((folded, 'body-only, on the head of the pull request'))
for payload, form in attempts:
    result = post(payload)
    if result.returncode == 0:
        print(f'Review submitted ({event}) {form}')
        apply_label()
        sys.exit(0)
    sys.stderr.write(result.stderr.decode(errors='replace')[-800:] + '\n')
    print(f'::warning::GitHub rejected the review payload {form}')
print('::error::Could not submit the review — the review request stays pending')
sys.exit(1)
