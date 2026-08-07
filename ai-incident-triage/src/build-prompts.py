"""Build the triage prompt covering ALL selected issues in one agent invocation.

Usage: build-prompts.py <template-path> <log-dir>
Env:   ISSUES_JSON    - JSON array produced by the select-issues action (each item
                        carries its own "repository" as owner/repo)
       MARKER         - hidden marker string for triage comments
       POST_COMMENTS  - "true": the agent posts each comment on its issue;
                        anything else: review mode — the agent writes the comments
                        it WOULD have posted to <log-dir>/comments/ instead

The agent sees the whole selection at once (deliberate: cross-repository correlation
reveals shared root causes). Issues are deterministically ordered (repository, then
number) and each gains a "key" (owner-repo-number — issue numbers collide across
repositories) used for report file names. Writes <log-dir>/selected-issues.json and
<log-dir>/triage.prompt.md, then prints the space-separated key list to stdout.
"""
import json
import os
import sys

template_path, log_dir = sys.argv[1], sys.argv[2]
marker = os.environ['MARKER']
post_comments = os.environ.get('POST_COMMENTS', 'true') == 'true'
issues = json.loads(os.environ['ISSUES_JSON'])  # fail fast on malformed input

comments_dir = os.path.join(log_dir, 'comments')
if not post_comments:
    os.makedirs(comments_dir, exist_ok=True)

ordered = sorted(issues, key=lambda i: (i['repository'], int(i['number'])))
for issue in ordered:
    issue['key'] = f"{issue['repository'].replace('/', '-')}-{issue['number']}"

# Keep the exact selection alongside the run logs for auditability.
os.makedirs(log_dir, exist_ok=True)
with open(os.path.join(log_dir, 'selected-issues.json'), 'w', encoding='utf-8') as fh:
    json.dump(ordered, fh, indent=2)

POST_INSTRUCTIONS = (
    'post EXACTLY ONE comment on the issue being processed, no matter the outcome. Write\n'
    '   the body to a file first, then post it with:\n'
    '   `gh issue comment <number> --repo <repository> --body-file <file>`')
REVIEW_INSTRUCTIONS = (
    'do NOT post anything to any issue — this run is a REVIEW pass. For the issue being\n'
    '   processed, write the comment you WOULD have posted (exact same format below) to the\n'
    '   file `' + comments_dir + '/issue-<key>.comment.md` using the Write tool. A human\n'
    '   reviews these files in place of the issue comments. Write no other files. In this\n'
    '   mode, also do NOT restart any CI run — when the transient-infrastructure signatures\n'
    '   match, state in the stored comment that you would have restarted the run.')

with open(template_path, encoding='utf-8') as fh:
    template = fh.read()

prompt = (template
          .replace('__REPORTING_INSTRUCTIONS__',
                   POST_INSTRUCTIONS if post_comments else REVIEW_INSTRUCTIONS)
          .replace('__ISSUES_JSON__', json.dumps(ordered, indent=2))
          .replace('__MARKER__', marker))
with open(os.path.join(log_dir, 'triage.prompt.md'), 'w', encoding='utf-8') as fh:
    fh.write(prompt)

print(' '.join(issue['key'] for issue in ordered))
