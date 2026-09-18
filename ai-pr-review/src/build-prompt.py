"""Build the review prompt for ONE pull request.

Usage: build-prompt.py <template-path> <log-dir>
Env:   PR_URL            - URL of the pull request to review
       MARKER            - hidden marker string for review bodies
       AGENT             - human-readable identity of the agent (CLI + model)
       RUN_URL           - URL of the workflow run performing this review
       POST_REVIEW       - "true": the workflow submits the review file the
                           agent writes; anything else: review mode - the file
                           only lands in the run artifact
       ALLOWED_TOOLS     - the --allowedTools value the agent will run under
       DISALLOWED_TOOLS  - the --disallowedTools value

The prompt states the agent's tool surface, rendered from the very strings the
run passes to the CLI. The agent works from inside the cortex harness, whose
CLAUDE.md mandates routes -- `gh` through `gh-wrapper`, no `cd` -- that this
allowlist may or may not carry; a headless agent that guesses wrong reads the
denial as "the tool is gone" and spends its budget looking for a way around.
Rendering the two lists rather than restating them in the template is what
keeps the prompt and the CLI flags from drifting apart.

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
# Written by prefetch-context.py before this script runs.
context_dir = os.path.join(log_dir, 'context')


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


allowed_plain, allowed_shell = split_tools(os.environ.get('ALLOWED_TOOLS', ''))
denied_plain, denied_shell = split_tools(os.environ.get('DISALLOWED_TOOLS', ''))

def bullets(commands):
    """One command prefix per line, wrapped so a long list stays readable in the log."""
    return [f'  - `{command}`' for command in commands]


surface = [
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
    'Two consequences of working from inside the cortex harness, whose CLAUDE.md you have',
    'also been given. On these two points THIS section wins — it is what the CLI enforces:',
    '',
    '- cortex routes every `gh` write through `tools/gh-wrapper/bin/gh-wrapper`. You make no',
    '  write, and the list above carries the reads under both spellings, so either route',
    '  works. Use the one the list names; never retry a denied call through the other.',
    '- cortex denies `cd`, and it is not on the list above, so a directory is reached by',
    '  naming it: Read, Grep and Glob all take an absolute path. `git` is NOT available',
    '  inside the pre-fetched checkout — read the history from `diff.patch` and `pr.json`',
    '  instead, and the files themselves with Read/Grep/Glob.',
]
TOOL_SURFACE = '\n'.join(surface)

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
          .replace('__CONTEXT_DIR__', context_dir)
          .replace('__TOOL_SURFACE__', TOOL_SURFACE)
          .replace('__AGENT__', os.environ.get('AGENT', 'Claude Code'))
          .replace('__RUN_URL__', os.environ.get('RUN_URL', ''))
          .replace('__MARKER__', marker))

os.makedirs(log_dir, exist_ok=True)
with open(os.path.join(log_dir, 'review.prompt.md'), 'w', encoding='utf-8') as fh:
    fh.write(prompt)

print(key)
