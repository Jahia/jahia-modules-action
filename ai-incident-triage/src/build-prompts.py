"""Build the agent prompt, in one of the action's two modes.

Usage: build-prompts.py <template-path> <log-dir>
Env (both modes):
       AGENT          - human-readable identity of the agent (CLI + model)
       RUN_URL        - URL of the workflow run performing this analysis

Issues mode (ISSUES_JSON set, ARTIFACTS_PATH empty) — the triage prompt covering ALL
selected issues in one agent invocation:
       ISSUES_JSON    - JSON array produced by the select-issues action (each item
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

Run mode (ARTIFACTS_PATH set) — the analysis of the integration-tests run that just
finished in the same job, from its artifacts on disk:
       ARTIFACTS_PATH - folder exported by the integration-tests action (holds results/)
       MODULE_ID      - id of the tested module
       TESTS_OUTCOME  - outcome of the tests step as GitHub saw it (success/failure)
       WORKSPACE      - checkout of the tested module (GITHUB_WORKSPACE)
       REPOSITORY     - owner/repo running the job (GITHUB_REPOSITORY)
       REF_NAME       - branch or tag being tested (GITHUB_REF_NAME)

Writes <log-dir>/run-context.json and <log-dir>/triage.prompt.md (same file name as the
issues mode, so the run step is identical), creates <log-dir>/analysis/ for the report,
then prints the single key "run" to stdout.
"""
import json
import os
import sys

template_path, log_dir = sys.argv[1], sys.argv[2]
os.makedirs(log_dir, exist_ok=True)

with open(template_path, encoding='utf-8') as fh:
    template = fh.read()

common = {
    '__AGENT__': os.environ.get('AGENT', 'Claude Code'),
    '__RUN_URL__': os.environ.get('RUN_URL', ''),
}


def render(replacements):
    prompt = template
    for placeholder, value in {**common, **replacements}.items():
        prompt = prompt.replace(placeholder, value)
    with open(os.path.join(log_dir, 'triage.prompt.md'), 'w', encoding='utf-8') as fh:
        fh.write(prompt)


artifacts_path = os.environ.get('ARTIFACTS_PATH', '')

if artifacts_path:
    artifacts_path = os.path.abspath(artifacts_path)
    if not os.path.isdir(artifacts_path):
        sys.exit(f'ARTIFACTS_PATH is not a directory: {artifacts_path}')
    analysis_dir = os.path.join(log_dir, 'analysis')
    os.makedirs(analysis_dir, exist_ok=True)
    report_file = os.path.join(analysis_dir, 'run-analysis.md')
    context = {
        'repository': os.environ.get('REPOSITORY', ''),
        'ref_name': os.environ.get('REF_NAME', ''),
        'module_id': os.environ.get('MODULE_ID', ''),
        'tests_outcome': os.environ.get('TESTS_OUTCOME', ''),
        'artifacts_path': artifacts_path,
        'workspace': os.environ.get('WORKSPACE', ''),
        'run_url': common['__RUN_URL__'],
    }
    # Keep the exact input alongside the run logs for auditability.
    with open(os.path.join(log_dir, 'run-context.json'), 'w', encoding='utf-8') as fh:
        json.dump(context, fh, indent=2)
    render({
        '__RUN_CONTEXT_JSON__': json.dumps(context, indent=2),
        '__REPORT_FILE__': report_file,
    })
    print('run')
    sys.exit(0)

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

render({
    '__REPORTING_INSTRUCTIONS__': POST_INSTRUCTIONS if post_comments else REVIEW_INSTRUCTIONS,
    '__ISSUES_JSON__': json.dumps(ordered, indent=2),
    '__MARKER__': marker,
})

print(' '.join(issue['key'] for issue in ordered))
