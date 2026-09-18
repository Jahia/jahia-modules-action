"""Fetch everything the review agent needs to read, before the agent starts.

Usage: prefetch-context.py <context-dir>
Env:   PR_URL         - URL of the pull request to review
       GH_TOKEN       - token `gh` authenticates with
       CHECKOUT_ROOT  - optional: directory to place the PR checkout under
                        (omit or leave empty to skip the checkout)

Writes <context-dir>/*, whose index is <context-dir>/README.md -- the file the
prompt points the agent at, and which also names what could NOT be fetched.

Why this step exists rather than the agent running the same commands: the agent
runs under an allowlist, so every fetch it makes costs turns, and the ones the
allowlist refuses cost far more than that -- a denial it cannot interpret sends
it looking for a way around. This step runs with a plain shell, so it also
reaches the one source the agent's surface will never carry: `gh api
.../pulls/N/comments`, the inline review threads.

Every fetch is best-effort on purpose: a review missing the CI state is worth
far more than no review at all, so a failure is recorded in the index and the
run goes on.
"""
import json
import os
import re
import subprocess
import sys

context_dir = sys.argv[1]
pr_url = os.environ['PR_URL']
checkout_root = os.environ.get('CHECKOUT_ROOT', '').strip()

match = re.search(r'([^/]+)/([^/]+)/pull/(\d+)$', pr_url)
if not match:
    sys.exit(f'Unrecognized pull request URL: {pr_url}')
owner, repo, number = match.groups()
slug = f'{owner}/{repo}'

os.makedirs(context_dir, exist_ok=True)

index = []     # (filename, one-line description) for the README
failures = []  # (what, first line of the error) for the README


def run(args, timeout=120):
    """Run a command, returning (ok, output). Never raises: see the module docstring."""
    try:
        done = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    if done.returncode != 0:
        return False, (done.stderr or done.stdout).strip()
    return True, done.stdout


def first_line(text):
    return text.splitlines()[0] if text.strip() else 'no output'


def fetch(name, description, args, render=None, timeout=120):
    """Fetch one piece of context into <context-dir>/<name>, best-effort."""
    ok, out = run(args, timeout=timeout)
    if ok and render is not None:
        try:
            out = render(out)
        except (ValueError, KeyError, TypeError) as exc:
            ok, out = False, f'could not render the response: {exc}'
    if not ok:
        failures.append((name, first_line(out)))
        print(f'  ! {name}: {first_line(out)}', file=sys.stderr)
        return None
    with open(os.path.join(context_dir, name), 'w', encoding='utf-8') as fh:
        fh.write(out)
    index.append((name, description))
    print(f'  - {name} ({len(out)} bytes)', file=sys.stderr)
    return out


def render_reviews(raw):
    """Submitted reviews, in the order GitHub returns them, as readable markdown."""
    reviews = json.loads(raw)['reviews']
    if not reviews:
        return '_No review has been submitted on this pull request yet._\n'
    out = []
    for review in reviews:
        author = (review.get('author') or {}).get('login', 'unknown')
        out.append(f"## {author} — {review.get('state', '?')} — {review.get('submittedAt', '?')}\n")
        out.append((review.get('body') or '_(no body)_').strip() + '\n')
    return '\n'.join(out)


def render_review_comments(raw):
    """The inline review threads: the one source the agent's allowlist cannot reach."""
    comments = json.loads(raw)
    if not comments:
        return '_No inline review comment on this pull request._\n'
    out = []
    for comment in comments:
        where = f"{comment['path']}:{comment.get('line') or comment.get('original_line')}"
        author = (comment.get('user') or {}).get('login', 'unknown')
        head = f"## {where} — {author} — {comment.get('created_at', '?')}"
        if comment.get('in_reply_to_id'):
            head += f" (reply to comment {comment['in_reply_to_id']})"
        out.append(head + '\n')
        if comment.get('diff_hunk'):
            out.append('```diff\n' + comment['diff_hunk'] + '\n```\n')
        out.append((comment.get('body') or '').strip() + '\n')
    return '\n'.join(out)


def render_linked_issues(raw):
    """The issues this PR closes -- the acceptance criteria -- each fetched in full."""
    refs = json.loads(raw)['closingIssuesReferences']
    if not refs:
        return '_This pull request closes no issue._\n'
    out = []
    for ref in refs:
        num = ref['number']
        ok, body = run(['gh', 'issue', 'view', str(num), '--repo', slug,
                        '--json', 'title,body,state,labels,comments'])
        if not ok:
            out.append(f"## #{num} — {ref.get('title', '?')}\n\n_Could not be read: {body}_\n")
            continue
        issue = json.loads(body)
        labels = ', '.join(label['name'] for label in issue.get('labels', [])) or 'none'
        out.append(f"## #{num} — {issue['title']} ({issue['state']}, labels: {labels})\n")
        out.append((issue.get('body') or '_(no description)_').strip() + '\n')
        for comment in issue.get('comments', []):
            author = (comment.get('author') or {}).get('login', 'unknown')
            out.append(f"### comment by {author}\n\n{(comment.get('body') or '').strip()}\n")
    return '\n'.join(out)


def make_checkout(root):
    """Check the PR head out for the agent, returning the note the README carries.

    The agent cannot do this itself: cortex denies `cd`, so it has no way into a clone
    it creates. Blobless keeps the clone cheap -- file contents arrive on first read.
    """
    target = os.path.join(root, repo)
    if os.path.exists(target):
        return f'A checkout already exists at `{target}`.'
    os.makedirs(root, exist_ok=True)
    ok, out = run(['gh', 'repo', 'clone', slug, target, '--',
                   '--filter=blob:none', '--no-tags'], timeout=300)
    if ok:
        ok, out = run(['git', '-C', target, 'fetch', '--no-tags', 'origin',
                       f'pull/{number}/head'], timeout=300)
    if ok:
        ok, out = run(['git', '-C', target, 'checkout', '--detach', 'FETCH_HEAD'], timeout=120)
    if not ok:
        failures.append(('checkout', first_line(out)))
        print(f'  ! checkout: {first_line(out)}', file=sys.stderr)
        return ('No checkout is available (it could not be created: '
                f'{first_line(out)}). Review from `diff.patch` alone.')
    print(f'  - checkout at {target}', file=sys.stderr)
    return (f'The pull request head is checked out at `{target}` (detached, blobless clone). '
            'Read, Grep and Glob work there; run git in it with `git -C` — never `cd`.')


print(f'Pre-fetching the context of {slug}#{number}', file=sys.stderr)

fetch('pr.md', 'Title, description, state, labels, reviewers, and every conversation comment',
      ['gh', 'pr', 'view', pr_url, '--comments'])
metadata = fetch('pr.json',
                 'Machine-readable metadata: head/base refs, head SHA, changed files, commits',
                 ['gh', 'pr', 'view', pr_url, '--json',
                  'number,title,state,isDraft,author,headRefName,headRefOid,baseRefName,'
                  'files,commits,additions,deletions,url'])
fetch('reviews.md', 'Every review already submitted, with its body — look for yours among them',
      ['gh', 'pr', 'view', pr_url, '--json', 'reviews'], render=render_reviews)
fetch('review-comments.md',
      'Every INLINE review comment already on the diff — never re-raise one of these',
      ['gh', 'api', f'repos/{slug}/pulls/{number}/comments', '--paginate'],
      render=render_review_comments)
fetch('linked-issues.md', 'The issues this pull request closes, in full: the acceptance criteria',
      ['gh', 'pr', 'view', pr_url, '--json', 'closingIssuesReferences'],
      render=render_linked_issues)
fetch('checks.md', 'CI state of the head commit',
      ['gh', 'pr', 'checks', pr_url])
fetch('diff.patch', 'The complete diff — read it from here, never from a command',
      ['gh', 'pr', 'diff', pr_url], timeout=300)

checkout_note = make_checkout(checkout_root) if checkout_root else ''

lines = [f'# Pre-fetched context for {slug}#{number}', '',
         'Every file below was fetched for you before you started. Read them instead of',
         'running the equivalent `gh` command: they are already here, they cost you no turn,',
         'and they include a source your tool surface cannot reach (`review-comments.md`).', '']
lines += [f'- `{name}` — {description}' for name, description in index]
if checkout_note:
    lines += ['', '## Checkout', '', checkout_note]
if failures:
    lines += ['', '## Not available', '',
              'These could NOT be fetched. Do not go hunting for them — note the gap in your',
              'review if it changes what you can assess:', '']
    lines += [f'- `{name}` — {reason}' for name, reason in failures]
if metadata:
    try:
        files = json.loads(metadata).get('files', [])
        lines += ['', '## Changed files', '']
        lines += [f"- `{entry['path']}` (+{entry['additions']}/-{entry['deletions']})"
                  for entry in files]
    except (ValueError, KeyError, TypeError):
        pass
lines.append('')

with open(os.path.join(context_dir, 'README.md'), 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(lines))

print(f'Pre-fetched {len(index)} files, {len(failures)} unavailable', file=sys.stderr)
