"""Build one deterministic triage prompt per selected issue.

Usage: build-prompts.py <template-path> <log-dir>
Env:   ISSUES_JSON  - JSON array produced by the select-issues action
       REPOSITORY   - owner/repo holding the incident issues
       MARKER       - hidden marker string for triage comments

Writes <log-dir>/selected-issues.json and <log-dir>/prompts/issue-<n>.prompt.md,
then prints the space-separated, ascending list of issue numbers to stdout.
"""
import json
import os
import sys

template_path, log_dir = sys.argv[1], sys.argv[2]
repository = os.environ['REPOSITORY']
marker = os.environ['MARKER']
issues = json.loads(os.environ['ISSUES_JSON'])  # fail fast on malformed input

prompts_dir = os.path.join(log_dir, 'prompts')
os.makedirs(prompts_dir, exist_ok=True)

# Keep the exact selection alongside the run logs for auditability.
with open(os.path.join(log_dir, 'selected-issues.json'), 'w', encoding='utf-8') as fh:
    json.dump(issues, fh, indent=2)

with open(template_path, encoding='utf-8') as fh:
    template = fh.read()

numbers = []
for issue in sorted(issues, key=lambda i: int(i['number'])):
    number = int(issue['number'])
    prompt = (template
              .replace('__ISSUE_JSON__', json.dumps(issue, indent=2))
              .replace('__REPOSITORY__', repository)
              .replace('__MARKER__', marker))
    with open(os.path.join(prompts_dir, f'issue-{number}.prompt.md'), 'w', encoding='utf-8') as fh:
        fh.write(prompt)
    numbers.append(str(number))

print(' '.join(numbers))
