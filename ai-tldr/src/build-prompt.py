"""Build the TL;DR prompt for ONE issue or pull request.

Usage: build-prompt.py <template-path> <log-dir>
Env:   TARGET_URL   - URL of the issue or pull request to summarize
       MARKER       - hidden marker string every TL;DR comment carries
       AGENT        - human-readable identity of the agent (CLI + model)
       RUN_URL      - URL of the workflow run producing this TL;DR
       POST_COMMENT - "true": the workflow posts the file the agent writes;
                      anything else: review mode - the file only lands in the
                      run artifact

The agent never posts to GitHub itself: in BOTH modes it writes the comment to
<log-dir>/comments/<key>.comment.md, and posting (when POST_COMMENT is true) is
a deterministic step of this action. That keeps "what was said" reviewable and
"whether it was said" outside the model's control.

Writes <log-dir>/tldr.prompt.md, then prints the key (owner-repo-number, used
for file names) to stdout.
"""
import os
import re
import sys

template_path, log_dir = sys.argv[1], sys.argv[2]
target_url = os.environ['TARGET_URL']
marker = os.environ['MARKER']
post_comment = os.environ.get('POST_COMMENT', 'true') == 'true'

# Both shapes reach here: /issues/<n> for an issue, /pull/<n> for a pull request.
match = re.search(r'([^/]+)/([^/]+)/(?:issues|pull)/(\d+)/?$', target_url)
if not match:
    sys.exit(f'Unrecognized issue or pull request URL: {target_url}')
key = '-'.join(match.groups())

comments_dir = os.path.join(log_dir, 'comments')
os.makedirs(comments_dir, exist_ok=True)
comment_file = os.path.join(comments_dir, f'{key}.comment.md')

POST_INSTRUCTIONS = (
    'write the final comment (exact format below) to the file\n'
    '   `' + comment_file + '` using the Write tool, no matter the outcome. Do NOT post\n'
    '   anything to GitHub yourself — the workflow posts that file on your behalf as one\n'
    '   comment, then removes the label.')
REVIEW_INSTRUCTIONS = (
    'write the comment you WOULD have posted (exact format below) to the file\n'
    '   `' + comment_file + '` using the Write tool, no matter the outcome. Do NOT post\n'
    '   anything to GitHub yourself — this run is a REVIEW pass of the agent itself:\n'
    '   nothing is posted, a human reads the file from the run artifact.')

with open(template_path, encoding='utf-8') as fh:
    template = fh.read()

prompt = (template
          .replace('__REPORTING_INSTRUCTIONS__',
                   POST_INSTRUCTIONS if post_comment else REVIEW_INSTRUCTIONS)
          .replace('__TARGET_URL__', target_url)
          .replace('__AGENT__', os.environ.get('AGENT', 'Claude Code'))
          .replace('__RUN_URL__', os.environ.get('RUN_URL', ''))
          .replace('__MARKER__', marker))

os.makedirs(log_dir, exist_ok=True)
with open(os.path.join(log_dir, 'tldr.prompt.md'), 'w', encoding='utf-8') as fh:
    fh.write(prompt)

print(key)
