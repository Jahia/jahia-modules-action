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


def run(args, timeout=120, allow_exit=()):
    """Run a command, returning (ok, output). Never raises: see the module docstring.

    `allow_exit` names the non-zero exits that still carry usable stdout. `gh pr checks`
    reports the state of the checks in its exit code -- 8 pending, 1 failing -- so treating
    every non-zero as a failure loses the CI state precisely when it is not green.

    Decoding replaces what it cannot read instead of raising. A diff is whatever bytes the
    branch holds -- a latin-1 properties file is enough -- and a UnicodeDecodeError here
    would escape the try below and kill the whole prefetch over one byte in one hunk.
    """
    try:
        done = subprocess.run(args, capture_output=True, timeout=timeout,
                              encoding='utf-8', errors='replace')
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    if done.returncode != 0 and done.returncode not in allow_exit:
        return False, (done.stderr or done.stdout).strip()
    return True, done.stdout


def first_line(text):
    return text.splitlines()[0] if text.strip() else 'no output'


def fetch(name, description, args, render=None, timeout=120, allow_exit=()):
    """Fetch one piece of context into <context-dir>/<name>, best-effort."""
    ok, out = run(args, timeout=timeout, allow_exit=allow_exit)
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
    # `gh repo clone` authenticates its own API calls, but the `git clone` it shells out to
    # goes through git's credential helper -- which on a bare runner asks for a username on
    # a terminal that is not there, and fails. This teaches git to use the gh token; without
    # it the clone fails on every private repository, and the review loses its checkout.
    ok, out = run(['gh', 'auth', 'setup-git'], timeout=60)
    if not ok:
        print(f'  ! git credential setup: {first_line(out)}', file=sys.stderr)
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
    # The clone is the one thing the agent reads that the run artifact does not carry -- it
    # is large, and it is reproducible. Reproducible only from its commit, though, so the
    # index records that: without it the artifact cannot say what the agent actually read.
    resolved, sha = run(['git', '-C', target, 'rev-parse', 'HEAD'], timeout=30)
    sha = sha.strip() if resolved else 'unknown'
    print(f'  - checkout at {target} ({sha[:12]})', file=sys.stderr)
    return (f'The pull request head is checked out at `{target}`, at commit `{sha}` '
            '(detached, blobless clone). Read, Grep and Glob work there; run git in it with '
            '`git -C` — never `cd`.\n\n'
            'This clone is NOT in the run artifact — it is large, and this commit reproduces '
            f'it: `git clone {slug} && git checkout {sha}`. Everything else in this directory '
            'is uploaded.')


print(f'Pre-fetching the context of {slug}#{number}', file=sys.stderr)

def fetch_pr():
    """Title, description and metadata, then the conversation.

    Two calls, because `gh pr view --comments` prints ONLY the comments when stdout is not
    a terminal: asking for the comments silently drops the description, which is the intent
    the whole review is measured against, and leaves the file empty on a PR nobody has
    commented on yet.
    """
    ok, overview = run(['gh', 'pr', 'view', pr_url])
    if not ok:
        failures.append(('pr.md', first_line(overview)))
        print(f'  ! pr.md: {first_line(overview)}', file=sys.stderr)
        return
    ok, comments = run(['gh', 'pr', 'view', pr_url, '--comments'])
    if not ok:
        comments = f'_The conversation could not be read: {first_line(comments)}_\n'
    elif not comments.strip():
        comments = '_No conversation comment on this pull request._\n'
    body = f'{overview}\n\n# Conversation\n\n{comments}'
    with open(os.path.join(context_dir, 'pr.md'), 'w', encoding='utf-8') as fh:
        fh.write(body)
    index.append(('pr.md', 'Title, description, state, labels, reviewers, then the conversation'))
    print(f'  - pr.md ({len(body)} bytes)', file=sys.stderr)


fetch_pr()
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
# exits 8 while checks are pending and 1 when one is failing -- both are the answer, not an error.
fetch('checks.md', 'CI state of the head commit',
      ['gh', 'pr', 'checks', pr_url], allow_exit=(1, 8))
fetch('diff.patch', 'The complete diff — read it from here, never from a command',
      ['gh', 'pr', 'diff', pr_url], timeout=300)

checkout_note = make_checkout(checkout_root) if checkout_root else ''

lines = [f'# Pre-fetched context for {slug}#{number}', '',
         'Every file below was fetched for you before you started. Read them instead of',
         'running the equivalent `gh` command: they are already here, they cost you no turn,',
         'and they include a source your tool surface cannot reach (`review-comments.md`).',
         '',
         'This whole directory is uploaded as the run artifact, so what you read here is what',
         'a human re-reading the run later sees. Nothing you need has to be copied elsewhere.',
         '']
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
