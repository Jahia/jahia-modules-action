"""Build one deterministic triage prompt per selected issue.

Usage: build-prompts.py <template-path> <log-dir>
Env:   ISSUES_JSON  - JSON array produced by the select-issues action (each item
                      carries its own "repository" as owner/repo)
       MARKER       - hidden marker string for triage comments

Writes <log-dir>/selected-issues.json and <log-dir>/prompts/issue-<key>.prompt.md
(key = owner-repo-number, since issue numbers collide across repositories), then
prints the space-separated, deterministically ordered list of keys to stdout.
Every prompt also embeds a snapshot of ALL selected issues, so the agent can spot
a shared root cause impacting several repositories at once.
"""
import json
import os
import sys

template_path, log_dir = sys.argv[1], sys.argv[2]
marker = os.environ['MARKER']
issues = json.loads(os.environ['ISSUES_JSON'])  # fail fast on malformed input

prompts_dir = os.path.join(log_dir, 'prompts')
os.makedirs(prompts_dir, exist_ok=True)

# Keep the exact selection alongside the run logs for auditability.
with open(os.path.join(log_dir, 'selected-issues.json'), 'w', encoding='utf-8') as fh:
    json.dump(issues, fh, indent=2)

with open(template_path, encoding='utf-8') as fh:
    template = fh.read()

ordered = sorted(issues, key=lambda i: (i['repository'], int(i['number'])))
snapshot = '\n'.join(
    f"- {i['repository']}#{i['number']} — {i['title']} (latest failure: {i['latest_failure_at']})"
    for i in ordered)

keys = []
for issue in ordered:
    key = f"{issue['repository'].replace('/', '-')}-{issue['number']}"
    prompt = (template
              .replace('__ISSUE_JSON__', json.dumps(issue, indent=2))
              .replace('__REPOSITORY__', issue['repository'])
              .replace('__ORG_SNAPSHOT__', snapshot)
              .replace('__MARKER__', marker))
    with open(os.path.join(prompts_dir, f'issue-{key}.prompt.md'), 'w', encoding='utf-8') as fh:
        fh.write(prompt)
    keys.append(key)

print(' '.join(keys))
