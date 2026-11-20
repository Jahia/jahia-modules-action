"""Fetch the text of each selected bug into one file per ticket, for the agent to read.

Usage: fetch-tickets.py <log-dir>
Env:   BUGS_JSON  - JSON array produced by the select-bugs action
       MARKER     - hidden marker of the score comment, left out of the ticket text
       GH_TOKEN   - token able to read every selected issue (read by gh)

Writes <log-dir>/selected-bugs.json and <log-dir>/tickets/<key>.json. The agent then needs no
network and no GitHub token. The body and the comments are cut at the sizes the rubric was
calibrated on.
"""
import json
import os
import subprocess
import sys

BODY_LIMIT, COMMENT_LIMIT, COMMENT_COUNT = 7000, 1500, 15
QUERY = '''
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    visibility
    issue(number: $number) {
      title url body createdAt
      issueType { name }
      labels(first: 50) { nodes { name } }
      comments(last: 30) { totalCount nodes { author { login } createdAt body } }
    }
  }
}'''


def fetch(repository, number):
    owner, name = repository.split('/')
    out = subprocess.run(
        ['gh', 'api', 'graphql', '-f', f'query={QUERY}', '-f', f'owner={owner}', '-f', f'name={name}',
         '-F', f'number={number}'],
        check=True, capture_output=True, text=True).stdout
    return json.loads(out)['data']['repository']


def ticket(bug, repo, marker):
    issue = repo['issue']
    comments = [c for c in issue['comments']['nodes'] if marker not in (c['body'] or '')]
    return {
        'ref': f'{bug["repository"]}#{bug["number"]}',
        'url': issue['url'],
        'title': issue['title'],
        'type': (issue['issueType'] or {}).get('name'),
        'visibility': repo['visibility'],
        'labels': [label['name'] for label in issue['labels']['nodes']],
        'created': issue['createdAt'][:10],
        'body': (issue['body'] or '')[:BODY_LIMIT],
        'comments_total': issue['comments']['totalCount'],
        'comments': [{'by': (c['author'] or {}).get('login'), 'at': c['createdAt'][:10],
                      'body': (c['body'] or '')[:COMMENT_LIMIT]} for c in comments[-COMMENT_COUNT:]],
    }


def main():
    log_dir = sys.argv[1]
    marker = os.environ['MARKER']
    bugs = json.loads(os.environ['BUGS_JSON'])
    tickets_dir = os.path.join(log_dir, 'tickets')
    os.makedirs(tickets_dir, exist_ok=True)
    with open(os.path.join(log_dir, 'selected-bugs.json'), 'w', encoding='utf-8') as fh:
        json.dump(bugs, fh, indent=2)
    fetched = []
    for bug in bugs:
        try:
            data = ticket(bug, fetch(bug['repository'], bug['number']), marker)
        except (subprocess.CalledProcessError, KeyError, TypeError) as error:
            # The bug keeps its empty field, so the next run tries it again.
            print(f'::warning::{bug["repository"]}#{bug["number"]}: could not read the ticket ({error})')
            continue
        with open(os.path.join(tickets_dir, f'{bug["key"]}.json'), 'w', encoding='utf-8') as fh:
            json.dump(data, fh, indent=1)
        fetched.append(bug['key'])
    print(' '.join(fetched))


if __name__ == '__main__':
    main()
