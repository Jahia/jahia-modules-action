"""Build the review prompt for ONE pull request.

Usage: build-prompt.py <template-path> <log-dir>
Env:   PR_URL       - URL of the pull request to review
       MARKER       - hidden marker string for review bodies
       AGENT        - human-readable identity of the agent (CLI + model)
       RUN_URL      - URL of the workflow run performing this review
       POST_REVIEW  - "true": the workflow submits the review file the agent
                      writes; anything else: review mode - the file only lands
                      in the run artifact

The agent never posts to GitHub itself: in BOTH modes it writes the review body
to <log-dir>/reviews/pr-<key>.review.md, and the posting (when post_review is
true) is a deterministic action step.

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
os.makedirs(reviews_dir, exist_ok=True)
review_file = os.path.join(reviews_dir, f'pr-{key}.review.json')
# Everything the agent gathers from resources it uses lands here (uploaded as the artifact).
collect_dir = os.path.join(log_dir, 'collected')
os.makedirs(collect_dir, exist_ok=True)

POST_INSTRUCTIONS = (
    'write the final review (exact JSON format below) to the file\n'
    '   `' + review_file + '` using the Write tool, no matter the outcome. Do NOT post\n'
    '   anything to GitHub yourself — the workflow submits that file on your behalf as ONE\n'
    '   pull-request review, with each finding attached as an inline comment on its line.')
REVIEW_INSTRUCTIONS = (
    'write the review you WOULD have delivered (exact JSON format below) to the file\n'
    '   `' + review_file + '` using the Write tool, no matter the outcome. Do NOT post\n'
    '   anything to GitHub yourself — this run is a REVIEW pass of the agent itself:\n'
    '   nothing is posted, a human reads the file from the run artifact.')

with open(template_path, encoding='utf-8') as fh:
    template = fh.read()

prompt = (template
          .replace('__REPORTING_INSTRUCTIONS__',
                   POST_INSTRUCTIONS if post_review else REVIEW_INSTRUCTIONS)
          .replace('__PR_URL__', pr_url)
          .replace('__COLLECT_DIR__', collect_dir)
          .replace('__AGENT__', os.environ.get('AGENT', 'Claude Code'))
          .replace('__RUN_URL__', os.environ.get('RUN_URL', ''))
          .replace('__MARKER__', marker))

os.makedirs(log_dir, exist_ok=True)
with open(os.path.join(log_dir, 'review.prompt.md'), 'w', encoding='utf-8') as fh:
    fh.write(prompt)

print(key)
