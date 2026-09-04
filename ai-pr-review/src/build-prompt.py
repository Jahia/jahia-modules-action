"""Build the review prompt for ONE pull request.

Usage: build-prompt.py <template-path> <log-dir>
Env:   PR_URL       - URL of the pull request to review
       MARKER       - hidden marker string for review bodies
       AGENT        - human-readable identity of the agent (CLI + model)
       RUN_URL      - URL of the workflow run performing this review
       POST_REVIEW  - "true": the agent submits the review on the PR;
                      anything else: review mode - the agent writes the review
                      it WOULD have submitted to <log-dir>/reviews/ instead

Writes <log-dir>/review.prompt.md, then prints the PR key (owner-repo-number,
used for file names) to stdout.
"""
import os
import re
import sys

template_path, log_dir = sys.argv[1], sys.argv[2]
pr_url = os.environ['PR_URL']
marker = os.environ['MARKER']
post_review = os.environ.get('POST_REVIEW', 'true') == 'true'

match = re.search(r'([^/]+)/([^/]+)/pull/(\d+)$', pr_url)
if not match:
    sys.exit(f'Unrecognized pull request URL: {pr_url}')
key = '-'.join(match.groups())

reviews_dir = os.path.join(log_dir, 'reviews')
if not post_review:
    os.makedirs(reviews_dir, exist_ok=True)

POST_INSTRUCTIONS = (
    'submit EXACTLY ONE pull-request review of type COMMENT, no matter the outcome. Write\n'
    '   the review body to a file first, then submit it with:\n'
    '   `gh pr review ' + pr_url + ' --comment --body-file <file>`')
REVIEW_INSTRUCTIONS = (
    'do NOT submit or post anything on the pull request — this run is a REVIEW pass of the\n'
    '   agent itself. Write the review you WOULD have submitted (exact same format below) to\n'
    '   the file `' + reviews_dir + '/pr-' + key + '.review.md` using the Write tool. A human\n'
    '   reads that file in place of the PR review. Write no other files.')

with open(template_path, encoding='utf-8') as fh:
    template = fh.read()

prompt = (template
          .replace('__REPORTING_INSTRUCTIONS__',
                   POST_INSTRUCTIONS if post_review else REVIEW_INSTRUCTIONS)
          .replace('__PR_URL__', pr_url)
          .replace('__AGENT__', os.environ.get('AGENT', 'Claude Code'))
          .replace('__RUN_URL__', os.environ.get('RUN_URL', ''))
          .replace('__MARKER__', marker))

os.makedirs(log_dir, exist_ok=True)
with open(os.path.join(log_dir, 'review.prompt.md'), 'w', encoding='utf-8') as fh:
    fh.write(prompt)

print(key)
