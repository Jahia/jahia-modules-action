"""Submit (or render) the structured review file the agent produced.

Usage: submit-review.py post <review-file> <pr-url>
       submit-review.py render <review-file>
Env:   REVIEWED_SHA - optional, for post: the head that the prefetch read
       MARKER, STARTED_AT - optional, for post: find a review of this run after an error
       LANDED_PAUSE - optional, for post: the seconds between two of those searches, 10 by default

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
its commit the head that the prefetch read, so that the next re-review reads its
delta from that commit. If GitHub refuses the payload with a 422 (typically an
anchor on a line that is not part of the diff), the review is submitted again
body-only, with the findings folded into the body, so a bad anchor never loses
the review. After any other error, a review of this run that is already on the
pull request counts as submitted. GitHub can create the review after it answers
the error, so the search runs three times. "render" prints the review as markdown
(review mode: job summary and artifact reading).

"post" requires GH_TOKEN with pull-request write on the repository.
"""
import json
import os
import re
import subprocess
import sys
import time
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
    print(f"::warning::The review file asks for {review['event']!r}. The review is submitted as "
          'COMMENT, because it never approves and never blocks the pull request.')

# The human review of the agent, mirrored as a PR label after the review is submitted.
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
    # Bring an existing label to the current description, keep its color, and create it when missing.
    patched = gh(['-X', 'PATCH', f'repos/{owner}/{repo}/labels/{quote(name, safe="")}', '--input', '-'],
                 {'description': description})
    if patched.returncode != 0:
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


def anchor(comment):
    """The GitHub review comment of one finding; a multi-line one keeps its start."""
    entry = {'path': comment['path'], 'line': int(comment['line']),
             'side': comment.get('side', 'RIGHT'), 'body': comment['body']}
    if comment.get('start_line') is not None:
        entry['start_line'] = int(comment['start_line'])
        entry['start_side'] = comment.get('start_side', entry['side'])
    return entry


def landed():
    """True when a review of this run by the token account is on the pull request, after an error."""
    marker, started = os.environ.get('MARKER'), os.environ.get('STARTED_AT')
    if not marker or not started:
        return False
    login = subprocess.run(['gh', 'api', 'user', '--jq', '.login'], capture_output=True, text=True)
    if login.returncode != 0:
        return False
    pause = float(os.environ.get('LANDED_PAUSE', '10'))
    for search in range(3):
        if search:
            time.sleep(pause)
        listed = subprocess.run(['gh', 'api', endpoint, '--paginate'], capture_output=True)
        if listed.returncode != 0:
            continue
        try:
            # The verify step of action.yml also requires a review strictly after the start.
            if any((review.get('user') or {}).get('login') == login.stdout.strip()
                   and marker in (review.get('body') or '')
                   and (review.get('submitted_at') or '') > started
                   for review in json.loads(listed.stdout)):
                return True
        except (ValueError, TypeError, AttributeError):
            pass
    return False


reviewed = os.environ.get('REVIEWED_SHA')
pinned = {'commit_id': reviewed} if reviewed else {}
attempts = []
if comments:
    attempts.append(({'event': 'COMMENT', 'body': body, 'comments': [anchor(c) for c in comments], **pinned},
                     f'with {len(comments)} inline comment(s)'))
attempts.append(({'event': 'COMMENT', 'body': fold(body, comments), **pinned},
                 'body-only, with the findings folded in'))
for payload, form in attempts:
    result = post(payload)
    if result.returncode == 0:
        print(f'Review submitted (COMMENT) {form}')
        apply_label()
        sys.exit(0)
    error = result.stderr.decode(errors='replace')
    sys.stderr.write(error[-800:] + '\n' + result.stdout.decode(errors='replace')[-800:] + '\n')
    # Only a 422 says that GitHub created no review: after any other error, a retry can post twice.
    if 'HTTP 422' not in error:
        break
    print(f'::warning::GitHub refused the review payload {form} (HTTP 422)')
if 'HTTP 422' not in error and landed():
    print('GitHub answered an error, but the review of this run is on the pull request')
    apply_label()
    sys.exit(0)
print('::error::Could not submit the review. The review request stays pending, and a re-request retries.')
sys.exit(1)
