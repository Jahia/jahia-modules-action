"""Fetch everything the review agent needs to read, before the agent starts.

Usage: prefetch-context.py <context-dir>
Env:   PR_URL         - URL of the pull request to review
       GH_TOKEN       - token `gh` authenticates with
       MARKER         - optional: the hidden marker of the reviews of the agent
                        (omit or leave empty to write no delta.patch)
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
import posixpath
import re
import subprocess
import sys

context_dir = sys.argv[1]
pr_url = os.environ['PR_URL']
marker = os.environ.get('MARKER', '').strip()
checkout_root = os.environ.get('CHECKOUT_ROOT', '').strip()

match = re.search(r'([^/]+)/([^/]+)/pull/(\d+)$', pr_url)
if not match:
    sys.exit(f'Unrecognized pull request URL: {pr_url}')
owner, repo, number = match.groups()
slug = f'{owner}/{repo}'

os.makedirs(context_dir, exist_ok=True)

index = []     # (filename, one-line description) for the README
failures = []  # (what, first line of the error) for the README

THREADS_QUERY = '''
query($owner: String!, $repo: String!, $number: Int!, $after: String) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      reviewThreads(first: 100, after: $after) {
        pageInfo { hasNextPage endCursor }
        nodes { isResolved comments(first: 1) { nodes { databaseId } } }
      }
    }
  }
}
'''

# An import of Claude Code: `@` after a space or a line start, then a relative path.
IMPORT = re.compile(r'(?:^|\s)@((?:\.{1,2}/)*[\w.-]+(?:/[\w.-]+)*)')


def run(args, timeout=120, allow_exit=(), stdin=None):
    """Run a command, returning (ok, output). Never raises: see the module docstring.

    `allow_exit` names the non-zero exits that still carry usable stdout. `gh pr checks`
    reports the state of the checks in its exit code -- 8 pending, 1 failing -- so treating
    every non-zero as a failure loses the CI state precisely when it is not green.

    Decoding replaces what it cannot read instead of raising. A diff is whatever bytes the
    branch holds -- a latin-1 properties file is enough -- and a UnicodeDecodeError here
    would escape the try below and kill the whole prefetch over one byte in one hunk.
    """
    try:
        done = subprocess.run(args, capture_output=True, timeout=timeout, input=stdin,
                              encoding='utf-8', errors='replace')
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    if done.returncode != 0 and done.returncode not in allow_exit:
        return False, (done.stderr or done.stdout).strip()
    return True, done.stdout


def first_line(text):
    return text.splitlines()[0] if text.strip() else 'no output'


def write(name, text):
    path = os.path.join(context_dir, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)
    print(f'  - {name} ({len(text)} bytes)', file=sys.stderr)


def fail(name, reason):
    failures.append((name, first_line(reason)))
    print(f'  ! {name}: {first_line(reason)}', file=sys.stderr)


def fetch(name, description, args, render=None, timeout=120, allow_exit=()):
    """Fetch one piece of context into <context-dir>/<name>, best-effort.

    Returns the raw output of the command, or None when the file could not be written."""
    ok, raw = run(args, timeout=timeout, allow_exit=allow_exit)
    out = raw
    if ok and render is not None:
        try:
            out = render(raw)
        except (ValueError, KeyError, TypeError) as exc:
            ok, out = False, f'could not render the response: {exc}'
    if not ok:
        fail(name, out)
        return None
    write(name, out)
    index.append((name, description))
    return raw


def render_reviews(raw):
    """Submitted reviews, oldest first, each with its id and the commit it read."""
    reviews = json.loads(raw)
    if not reviews:
        return '_No review has been submitted on this pull request yet._\n'
    out = []
    for review in reviews:
        author = (review.get('user') or {}).get('login', 'unknown')
        out.append(f"## {author} — {review.get('state', '?')} — {review.get('submitted_at', '?')}"
                   f" — review {review['id']} at commit {review.get('commit_id') or '?'}\n")
        out.append((review.get('body') or '_(no body)_').strip() + '\n')
    return '\n'.join(out)


def fetch_thread_states():
    """Map the id of the first comment of each review thread to its `isResolved`, or return None.

    Only GraphQL carries the resolution state: the REST comments have no such field."""
    states = {}
    cursor = []
    while True:
        ok, out = run(['gh', 'api', 'graphql', '-f', f'query={THREADS_QUERY}', '-f', f'owner={owner}',
                       '-f', f'repo={repo}', '-F', f'number={number}', *cursor])
        if ok:
            try:
                page = json.loads(out)['data']['repository']['pullRequest']['reviewThreads']
                for thread in page['nodes']:
                    first = thread['comments']['nodes']
                    if first:
                        states[first[0]['databaseId']] = thread['isResolved']
                more, end = page['pageInfo']['hasNextPage'], page['pageInfo']['endCursor']
            except (ValueError, KeyError, TypeError) as exc:
                ok, out = False, f'could not read the response: {exc}'
        if not ok:
            fail('thread resolution state', out)
            return None
        if not more:
            return states
        cursor = ['-f', f'after={end}']


def render_review_comments(raw, thread_states):
    """The inline review threads: the one source the agent's allowlist cannot reach.

    Each thread opens on its first comment, with its state and the review of that comment."""
    comments = json.loads(raw)
    if not comments:
        return '_No inline review comment on this pull request._\n'
    ids = {comment['id'] for comment in comments}
    replies = {}
    for comment in comments:
        if comment.get('in_reply_to_id') in ids:
            replies.setdefault(comment['in_reply_to_id'], []).append(comment)
    out = []
    for first in comments:
        if first.get('in_reply_to_id') in ids:
            continue
        resolved = (thread_states or {}).get(first['id'])
        state = 'state unknown' if resolved is None else ('resolved' if resolved else 'open')
        where = f"{first['path']}:{first.get('line') or first.get('original_line')}"
        out.append(f"## {where} — {state} — review {first.get('pull_request_review_id') or '?'}\n")
        if first.get('diff_hunk'):
            out.append('```diff\n' + first['diff_hunk'] + '\n```\n')
        for comment in [first] + replies.get(first['id'], []):
            author = (comment.get('user') or {}).get('login', 'unknown')
            out.append(f"### comment {comment['id']} by {author} — {comment.get('created_at', '?')}\n")
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


def fetch_changed_files(fallback):
    """Each changed file as (path, additions, deletions): `gh pr view` stops at 100 files, REST does not.

    On a failure, returns the `fallback` entries of pr.json, and names the gap."""
    ok, out = run(['gh', 'api', f'repos/{slug}/pulls/{number}/files', '--paginate'])
    if ok:
        try:
            return [(entry['filename'], entry['additions'], entry['deletions'])
                    for entry in json.loads(out)]
        except (ValueError, KeyError, TypeError) as exc:
            out = f'could not read the response: {exc}'
    fail('changed files', f'{first_line(out)}; the list below may stop at 100 files')
    return [(entry['path'], entry.get('additions'), entry.get('deletions')) for entry in fallback]


def keep_changed_files(diff, changed):
    """Keep the file sections of `diff` that name a file of the pull request."""
    suffixes = tuple(f' b/{path}' for path in changed)
    kept = []
    for section in re.split(r'(?m)^(?=diff --git )', diff):
        header = section.split('\n', 1)[0]
        # git quotes a path with unusual characters, which no suffix matches, so keep that section.
        if header.endswith(suffixes) or '"' in header:
            kept.append(section)
    return ''.join(kept)


def fetch_delta(reviews, head, login, changed):
    """Write delta.patch, the diff since the commit of the last review of `login` with the marker.

    Returns the note of README.md, or '' when no such review exists or the fetch failed."""
    marked = [review for review in reviews if review.get('commit_id')
              and (review.get('user') or {}).get('login') == login
              and marker in (review.get('body') or '')]
    if not marked:
        return ''
    review_id, since = marked[-1]['id'], marked[-1]['commit_id']
    read = f'Review {review_id}, the last review of `{login}` with the marker, read commit `{since}`.'
    compare = f'repos/{slug}/compare/{since}...{head}'
    # Page 2 of one commit drops the files and their patches, which only the first page carries.
    ok, status = run(['gh', 'api', f'{compare}?per_page=1&page=2', '--jq', '.status'])
    # A force-push can remove the commit of the review, and the compare then answers 404.
    rewritten = not ok and 'HTTP 404' in status
    if not ok and not rewritten:
        fail('delta.patch', status)
        return ''
    if rewritten or status.strip() not in ('ahead', 'identical'):
        return (f'{read} That commit is not an ancestor of the head, because the branch was '
                'rewritten, so this context has no `delta.patch`.')
    ok, diff = run(['gh', 'api', '-H', 'Accept: application/vnd.github.diff', compare], timeout=300)
    if not ok:
        fail('delta.patch', diff)
        return ''
    write('delta.patch', keep_changed_files(diff, changed))
    index.append(('delta.patch', 'The diff since the commit of the last review with the marker'))
    if status.strip() == 'identical':
        return f'{read} That commit is the head, so `delta.patch` is empty.'
    return (f'{read} `delta.patch` is the diff from that commit to the head `{head}`, in the files '
            'that the pull request changes only: a merge of the base adds no other file to it.')


def fetch_rules(base, changed):
    """Copy the rule files of the base branch under rules/, and return the lines of README.md or None.

    The rule files are the root CLAUDE.md and REVIEW.md, each CLAUDE.md above a changed file, and
    each file that one of them imports."""
    dirs = set()
    for path in changed:
        parent = posixpath.dirname(path)
        while parent:
            dirs.add(parent)
            parent = posixpath.dirname(parent)
    rule_files = ['CLAUDE.md', 'REVIEW.md'] + [f'{directory}/CLAUDE.md' for directory in sorted(dirs)]
    texts = {}
    wanted = rule_files
    # The rule files, then the files they import, five hops deep as Claude Code follows them.
    for _ in range(6):
        ok, found = fetch_blobs(base, wanted)
        if not ok:
            fail('rules/', found)
            return None
        texts.update(found)
        wanted = list(dict.fromkeys(target for path, text in found.items() if text
                                    for target in rule_imports(path, text) if target not in texts))
        if not wanted:
            break
    lines = []
    for path, text in texts.items():
        if text is None:
            continue
        # A path that the base branch holds is a path of git, so it never leaves rules/.
        write(f'rules/{path}', text)
        note = '' if path in rule_files else ', which a rule file imports'
        if path in changed:
            note += ', and this pull request changes it'
        lines.append(f'- `rules/{path}` — `{path}` on the base branch `{base}`{note}')
    return lines


def rule_imports(path, text):
    """The paths of the repository that a rule file imports with `@<path>`, from its directory."""
    found = []
    for target in IMPORT.findall(text):
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(path), target))
        if resolved != '..' and not resolved.startswith(('../', '/')):
            found.append(resolved)
    return found


def fetch_blobs(base, paths):
    """Return (ok, texts), where texts maps each path to its text on `base`, None when it has none.

    On a failure, the second value is the reason."""
    # One query for every path: an alias per path, and json.dumps writes a valid GraphQL string.
    fields = ' '.join(f'f{i}: object(expression: {json.dumps(f"{base}:{path}")}) {{ ... on Blob {{ text }} }}'
                      for i, path in enumerate(paths))
    query = f'query {{ repository(owner: {json.dumps(owner)}, name: {json.dumps(repo)}) {{ {fields} }} }}'
    ok, out = run(['gh', 'api', 'graphql', '--input', '-'], stdin=json.dumps({'query': query}))
    if ok:
        try:
            blobs = json.loads(out)['data']['repository']
            return True, {path: (blobs.get(f'f{i}') or {}).get('text') for i, path in enumerate(paths)}
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            out = f'could not read the response: {exc}'
    return False, out


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
        fail('checkout', out)
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
        fail('pr.md', overview)
        return
    ok, comments = run(['gh', 'pr', 'view', pr_url, '--comments'])
    if not ok:
        comments = f'_The conversation could not be read: {first_line(comments)}_\n'
    elif not comments.strip():
        comments = '_No conversation comment on this pull request._\n'
    write('pr.md', f'{overview}\n\n# Conversation\n\n{comments}')
    index.append(('pr.md', 'Title, description, state, labels, reviewers, then the conversation'))


fetch_pr()
metadata = fetch('pr.json',
                 'Machine-readable metadata: head/base refs, head SHA, changed files, commits',
                 ['gh', 'pr', 'view', pr_url, '--json',
                  'number,title,state,isDraft,author,headRefName,headRefOid,baseRefName,'
                  'files,commits,additions,deletions,url'])
try:
    pr = json.loads(metadata or '{}')
except ValueError:
    pr = {}
changed_files = fetch_changed_files(pr.get('files', []))
changed = [path for path, _, _ in changed_files]
reviews = fetch('reviews.md',
                'Every review already submitted, with its id, the commit it read and its body '
                '— look for yours among them',
                ['gh', 'api', f'repos/{slug}/pulls/{number}/reviews', '--paginate'],
                render=render_reviews)
thread_states = fetch_thread_states()
fetch('review-comments.md',
      'Every INLINE review thread already on the diff, with its state and the review of its first '
      'comment — never re-raise one of these',
      ['gh', 'api', f'repos/{slug}/pulls/{number}/comments', '--paginate'],
      render=lambda raw: render_review_comments(raw, thread_states))
fetch('linked-issues.md', 'The issues this pull request closes, in full: the acceptance criteria',
      ['gh', 'pr', 'view', pr_url, '--json', 'closingIssuesReferences'],
      render=render_linked_issues)
# exits 8 while checks are pending and 1 when one is failing -- both are the answer, not an error.
fetch('checks.md', 'CI state of the head commit',
      ['gh', 'pr', 'checks', pr_url], allow_exit=(1, 8))
fetch('diff.patch', 'The complete diff — read it from here, never from a command',
      ['gh', 'pr', 'diff', pr_url], timeout=300)
login = None
if marker:
    ok, out = run(['gh', 'api', 'user', '--jq', '.login'])
    if ok:
        login = out.strip()
    else:
        fail('login of the token user', out)
delta_note = ''
if reviews and login and pr.get('headRefOid'):
    delta_note = fetch_delta(json.loads(reviews), pr['headRefOid'], login, changed)
if pr.get('baseRefName'):
    rules = fetch_rules(pr['baseRefName'], changed)
else:
    rules = None
    fail('rules/', 'pr.json names no base branch')

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
if login:
    lines += ['', f'This run posts as `{login}`: the reviews of this agent are the reviews of '
              f'`{login}` whose body contains the marker.']
if delta_note:
    lines += ['', '## Delta since the last review', '', delta_note]
if rules is not None:
    lines += ['', '## Rules on the base branch', '',
              'The copies of the rule files that the base branch holds, which no change of this '
              'pull request reaches:', '']
    lines += rules or [f"- none: the base branch `{pr['baseRefName']}` holds no root `CLAUDE.md`, "
                       'no root `REVIEW.md` and no `CLAUDE.md` above a changed file']
if checkout_note:
    lines += ['', '## Checkout', '', checkout_note]
if failures:
    lines += ['', '## Not available', '',
              'These could NOT be fetched. Do not go hunting for them — note the gap in your',
              'review if it changes what you can assess:', '']
    lines += [f'- `{name}` — {reason}' for name, reason in failures]
if changed_files:
    lines += ['', '## Changed files', '']
    lines += [f'- `{path}` (+{additions}/-{deletions})' for path, additions, deletions in changed_files]
lines.append('')

with open(os.path.join(context_dir, 'README.md'), 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(lines))

print(f'Pre-fetched {len(index)} files, {len(failures)} unavailable', file=sys.stderr)
