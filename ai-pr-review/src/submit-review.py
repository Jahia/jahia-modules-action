"""Submit (or render) the structured review file the agent produced.

Usage: submit-review.py post <review-file> <pr-url>
       submit-review.py render <review-file>

The review file is JSON: {"body": "<markdown>", "comments": [{"path", "line",
"side", "body"}]}. "post" submits ONE pull-request review of type COMMENT via
the GitHub API, with the findings attached as inline comments on the lines in
question. If GitHub rejects the payload (typically an anchor on a line that is
not part of the diff), the review is re-submitted body-only with the findings
folded into the body — a bad anchor never loses the review. "render" prints
the review as markdown (review mode: job summary and artifact reading).

"post" requires GH_TOKEN with pull-request write on the repository.
"""
import json
import re
import subprocess
import sys
from urllib.parse import quote

mode, path = sys.argv[1], sys.argv[2]
try:
    with open(path, encoding='utf-8') as fh:
        review = json.load(fh)
    body = review['body']
    comments = review.get('comments', [])
except (json.JSONDecodeError, KeyError, TypeError) as error:
    print(f'::error::The agent produced an invalid review file ({error}) — '
          'nothing was posted; the file is in the run artifact and the review '
          'request stays pending (re-request to retry)')
    sys.exit(1)


def fold(body, comments):
    """Merge the inline comments into the body (fallback and render layout)."""
    if not comments:
        return body
    lines = [body, '', '### Findings']
    for c in comments:
        lines.append('')
        lines.append(f"`{c['path']}:{c['line']}` — {c['body']}")
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


event = review.get('event', 'COMMENT')
if event not in ('APPROVE', 'COMMENT'):
    print(f'::warning::Unexpected review event {event!r} — submitting as COMMENT')
    event = 'COMMENT'
if event == 'APPROVE' and comments:
    print('::warning::APPROVE with findings attached — downgraded to COMMENT (approval requires zero findings)')
    event = 'COMMENT'

# The agent's confidence call, mirrored as a PR label after the review is submitted.
LABELS = {
    'not-needed': ('🤖 AI-only review OK', '0E8A16',
                   'The AI reviewer is confident this PR can merge with the AI review alone'),
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


payload = {'event': event, 'body': body}
if comments:
    payload['comments'] = [{'path': c['path'], 'line': int(c['line']),
                            'side': c.get('side', 'RIGHT'), 'body': c['body']}
                           for c in comments]
result = post(payload)
if result.returncode == 0:
    print(f'Review submitted ({event}) with {len(comments)} inline comment(s)')
    apply_label()
    sys.exit(0)
sys.stderr.write(result.stderr.decode(errors='replace')[-800:] + '\n')
if comments:
    print('::warning::GitHub rejected the review payload (usually an anchor outside the diff) — submitting body-only with the findings folded in')
    result = post({'event': event, 'body': fold(body, comments)})
    if result.returncode == 0:
        print('Review submitted body-only')
        apply_label()
        sys.exit(0)
    sys.stderr.write(result.stderr.decode(errors='replace')[-800:] + '\n')
print('::error::Could not submit the review — the review request stays pending')
sys.exit(1)
