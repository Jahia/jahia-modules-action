"""Build the call of the Cortex skill pr-review, in its ci mode, for ONE pull request.

Usage: build-prompt.py <log-dir>
Env:   PR_URL            - URL of the pull request to review
       MARKER            - hidden marker string, the first line of the review body
       AGENT             - human-readable identity of the agent (CLI + model)
       RUN_URL           - URL of the workflow run performing this review
       ALLOWED_TOOLS     - the allowed_tools input, to which this script adds the rules
                           that name a path of this run
       DISALLOWED_TOOLS  - the --disallowedTools value

Cortex owns the review: its method, its decision rules and the shape of the review file
(`.claude/skills/pr-review/references/ci.md` and `assets/ci-review.md` in Jahia/cortex).
This action owns the CI around it, so the prompt is one line, the call of that skill:

    /pr-review ci <pr-url> --context <dir> --out <file> --marker <marker>
                           --run-url <url> --agent <label> --collect <dir>

The tool surface is the one thing the action still tells the agent, because the action
decides it. It is rendered from the very strings the run passes to the CLI, so the text and
the flags cannot drift apart, and it goes to --append-system-prompt.

The agent never posts to GitHub itself: it writes the review file
<log-dir>/reviews/pr-<key>.review.json, and posting it (when post_review is true) is a
deterministic step of the action.

Writes <log-dir>/review.prompt.md (the call), <log-dir>/review.system.md (the tool
surface) and <log-dir>/allowed-tools.txt (the --allowedTools value), then prints the PR key (owner-repo-number, used for file names) to stdout.
"""
import os
import re
import shlex
import sys

log_dir = os.path.abspath(sys.argv[1])
pr_url = os.environ['PR_URL']

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
# Written by prefetch-context.py before this script runs.
context_dir = os.path.join(log_dir, 'context')

# shlex.quote: the marker is an HTML comment and the agent label holds spaces, so each
# value is quoted for the skill to read it as one argument.
CALL = ' '.join(['/pr-review', 'ci', shlex.quote(pr_url)] + [
    f'{flag} {shlex.quote(value)}' for flag, value in (
        ('--context', context_dir),
        ('--out', review_file),
        ('--marker', os.environ['MARKER']),
        ('--run-url', os.environ.get('RUN_URL', '')),
        ('--agent', os.environ.get('AGENT', 'Claude Code')),
        ('--collect', collect_dir),
    )])


def split_tools(value):
    """Split an --allowedTools/--disallowedTools value into (plain tools, shell commands).

    Entries are comma-separated, but a `Bash(...)` entry may itself contain commas, so
    the split tracks parenthesis depth rather than calling str.split(',').
    """
    entries, depth, current = [], 0, ''
    for char in value:
        if char == ',' and depth == 0:
            entries.append(current.strip())
            current = ''
            continue
        depth += (char == '(') - (char == ')')
        current += char
    entries.append(current.strip())

    plain, shell = [], []
    for entry in (e for e in entries if e):
        match = re.fullmatch(r'Bash\((.*)\)', entry)
        if match:
            # `git log:*` and `git log --oneline` both describe one command prefix.
            shell.append(match.group(1).rstrip('*').rstrip(':').strip())
        else:
            plain.append(entry)
    return plain, shell


# The rules that name a path of this run: the one directory the agent writes in, and the
# check of the review file that the ci mode runs. `/` + an absolute path gives the `//<path>`
# form that Claude Code reads from the filesystem root.
allowed_tools = ','.join(filter(None, [
    os.environ.get('ALLOWED_TOOLS', ''),
    f'Edit(/{log_dir}/**)',
    f'Bash(python3 -m json.tool {review_file})',
]))
allowed_plain, allowed_shell = split_tools(allowed_tools)
denied_plain, denied_shell = split_tools(os.environ.get('DISALLOWED_TOOLS', ''))


def bullets(commands):
    """One command prefix per line, so a long list stays readable in the log."""
    return [f'  - `{command}`' for command in commands]


surface = [
    '# The tool surface of this CI run',
    '',
    'You run under an allowlist. A refusal is FINAL: it does not mean the tool is missing,',
    'and there is no way around it — a denied call means "use another route from this list".',
    'Never spend turns probing the permission surface; it is stated here in full.',
    '',
    '**You may use:**',
    '',
]
if allowed_plain:
    surface.append(f"- Tools: {', '.join(allowed_plain)}.")
surface += ['- These shell commands, and NOTHING else. Each entry is a command prefix — any',
            '  arguments are allowed after it:']
surface += bullets(allowed_shell)
surface += [
    '- A pipeline or a `;`-chain runs only when EVERY command in it is allowed:',
    '  `gh pr diff … | head -200` works, `… | jq …` and `… | python3 -c …` do not.',
    '',
    '**Denied — never retry these, in any spelling:**',
    '',
]
if denied_plain:
    surface.append(f"- Tools: {', '.join(denied_plain)}.")
surface.append('- These shell commands:')
surface += bullets(denied_shell)
surface += [
    '',
    'Three consequences of working from inside the cortex harness. On these three points THIS',
    'section wins — it is what the CLI enforces:',
    '',
    f'- Every file you write goes under `{log_dir}`, where the review file and `--collect` are.',
    '  A write in the working directory, the cortex checkout, is refused, through Write and',
    '  through a shell redirection alike, so a scratch file goes under that directory too.',
    '  `python3 -m json.tool` runs on the review file, in the one form that the list names.',
    '- cortex routes every `gh` write through `tools/gh-wrapper/bin/gh-wrapper`. You make no',
    '  write, and the list above carries the reads under both spellings, so either route',
    '  works. Use the one the list names; never retry a denied call through the other.',
    '- cortex denies `cd`, and it is not on the list above, so a directory is reached by',
    '  naming it: Read, Grep and Glob all take an absolute path. `git` is NOT available',
    '  inside the pre-fetched checkout — read the history from `diff.patch` and `pr.json`',
    '  instead, and the files themselves with Read/Grep/Glob.',
]

os.makedirs(log_dir, exist_ok=True)
with open(os.path.join(log_dir, 'review.prompt.md'), 'w', encoding='utf-8') as fh:
    fh.write(CALL + '\n')
with open(os.path.join(log_dir, 'review.system.md'), 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(surface) + '\n')
with open(os.path.join(log_dir, 'allowed-tools.txt'), 'w', encoding='utf-8') as fh:
    fh.write(allowed_tools + '\n')

print(key)
