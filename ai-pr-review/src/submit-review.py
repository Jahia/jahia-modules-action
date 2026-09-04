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


payload = {'event': 'COMMENT', 'body': body}
if comments:
    payload['comments'] = [{'path': c['path'], 'line': int(c['line']),
                            'side': c.get('side', 'RIGHT'), 'body': c['body']}
                           for c in comments]
result = post(payload)
if result.returncode == 0:
    print(f'Review submitted with {len(comments)} inline comment(s)')
    sys.exit(0)
sys.stderr.write(result.stderr.decode(errors='replace')[-800:] + '\n')
if comments:
    print('::warning::GitHub rejected the review payload (usually an anchor outside the diff) — submitting body-only with the findings folded in')
    result = post({'event': 'COMMENT', 'body': fold(body, comments)})
    if result.returncode == 0:
        print('Review submitted body-only')
        sys.exit(0)
    sys.stderr.write(result.stderr.decode(errors='replace')[-800:] + '\n')
print('::error::Could not submit the review — the review request stays pending')
sys.exit(1)
