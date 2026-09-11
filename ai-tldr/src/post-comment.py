"""Post (or render) the TL;DR comment the agent wrote.

Usage: post-comment.py post   <comment-file> <target-url>
       post-comment.py render <comment-file>

Env (post): GH_TOKEN - token the comment is posted with

Deliberately not `gh issue comment`: the body goes over the API as a JSON
string, so nothing in the markdown can be re-interpreted by a shell.

The marker line is what the guard reads to refuse a second TL;DR in a row, so a
file missing it is refused here rather than posted unrecognizable.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

MARKER = os.environ.get('MARKER', '<!-- cortex-tldr -->')
MAX_WORDS = int(os.environ.get('MAX_WORDS', '400'))


def read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read().strip()


def render(path):
    print(read(path))


def post(path, target_url):
    body = read(path)
    if not body:
        sys.exit('The agent produced an empty comment file — nothing to post')

    if MARKER not in body:
        # Prepending it keeps the run useful while still making the omission visible.
        print(f'::warning::The comment is missing the marker {MARKER} — prepending it')
        body = f'{MARKER}\n{body}'

    # A TL;DR that grew into an essay defeats the label; post it, but say so loudly.
    words = len(re.sub(r'<!--.*?-->', '', body, flags=re.S).split())
    if words > MAX_WORDS:
        print(f'::warning::The TL;DR is {words} words (soft limit {MAX_WORDS}) — the prompt asks for ~120')

    match = re.search(r'([^/]+)/([^/]+)/(?:issues|pull)/(\d+)/?$', target_url)
    if not match:
        sys.exit(f'Unrecognized issue or pull request URL: {target_url}')
    owner, repo, number = match.groups()

    request = urllib.request.Request(
        f'https://api.github.com/repos/{owner}/{repo}/issues/{number}/comments',
        data=json.dumps({'body': body}).encode('utf-8'),
        headers={
            'Authorization': f"Bearer {os.environ['GH_TOKEN']}",
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
            'Content-Type': 'application/json',
            'User-Agent': 'jahia-modules-action/ai-tldr',
        },
        method='POST')
    try:
        with urllib.request.urlopen(request) as response:
            print(f"Posted the TL;DR: {json.load(response)['html_url']} ({words} words)")
    except urllib.error.HTTPError as error:
        sys.exit(f'Could not post the comment ({error.code}): {error.read().decode("utf-8", "replace")}')


if sys.argv[1] == 'render':
    render(sys.argv[2])
else:
    post(sys.argv[2], sys.argv[3])
