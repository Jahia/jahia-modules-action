"""Build the call of the Cortex skill pr-review, in its ci mode, for ONE pull request.

Usage: build-prompt.py <log-dir>, with the environment that the prep step of action.yml sets.

It writes review.prompt.md (the call), review.system.md (the tool surface), allowed-tools.txt
and disallowed-tools.txt in <log-dir>, then prints the PR key (owner-repo-number), which names
the files of the run. README.md states the variables it reads, the call, and each permission rule
that it adds.
"""
import os
import re
import shlex
import subprocess
import sys

# The commands that `.claude/agents/review-inspector.md` of Cortex runs in the checkout.
GIT_READS = ('diff', 'log', 'show', 'grep', 'blame')
# Claude Code reads this run of backslashes in a rule as a single backslash of the command.
BACKSLASH = '\\' * 4
GIT_FENCES = ('*--output*', 'grep *O*', 'grep *--op*', "*'*", '*"*', f'*{BACKSLASH}*', '*$*', '*`*', '*{*')
# The characters of a checkout path that the git rules accept: none of them needs a quote or a backslash.
TYPABLE_PATH = re.compile(r'[A-Za-z0-9._/@+-]+')
# A deny rule such as `git -C * push *` refuses a `git -C` read that has the word `push` as an argument.
DENIED_GIT_WORD = re.compile(r'Bash\(git -C \* ([^\s*)]+)(?: \*)?\)')

log_dir = os.path.realpath(sys.argv[1])
pr_url = os.environ['PR_URL']
cortex_path = os.path.realpath(os.environ['CORTEX_PATH'])
# The deny rule of the cortex checkout would cover the log directory, and refuse every write
# of the agent.
if os.path.commonpath([log_dir, cortex_path]) == cortex_path:
    sys.exit(f'The log directory {log_dir} is inside the cortex checkout {cortex_path}')

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
if os.environ.get('REVIEW_ROUND'):
    CALL += f" --round {shlex.quote(os.environ['REVIEW_ROUND'])}"


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
            # `git log:*` and `git log *` are a prefix, which the prompt marks with ` …`;
            # `git branch -a` is the whole command.
            rule = match.group(1).strip()
            shell.append(f'{rule[:-2].rstrip()} …' if rule.endswith((':*', ' *')) else rule)
        else:
            plain.append(entry)
    return plain, shell


def compare_head(path: str, reviewed_sha: str) -> str:
    if not reviewed_sha:
        return 'the pre-fetch step read no reviewed head'
    result = subprocess.run(['git', '-C', path, 'rev-parse', '--show-toplevel', '--verify', 'HEAD'],
                            capture_output=True, text=True)
    if result.returncode:
        lines = [line.strip() for line in result.stderr.splitlines() if line.strip()]
        errors = [line for line in lines if line.startswith(('fatal:', 'error:'))]
        error = (errors or lines or [f'exit code {result.returncode}'])[-1]
        return f'git cannot read the head of the checkout {path}: {error}'
    top, _, head = result.stdout.rstrip('\n').rpartition('\n')
    # git searches the parent directories, so a plain directory gives the head of an enclosing repository.
    if os.path.realpath(top) != os.path.realpath(path):
        return f'the checkout {path} is no repository of its own: git reads the one at {top}'
    if head != reviewed_sha:
        return f'the checkout {path} is at {head}, not at the reviewed head {reviewed_sha}'
    return ''


# The checkout path as the README of the context names it, which is the text the agent types.
checkout = os.environ.get('CHECKOUT', '')
head_mismatch = compare_head(checkout, os.environ.get('REVIEWED_SHA', '')) if checkout else ''
typable = TYPABLE_PATH.fullmatch(checkout) is not None
if head_mismatch:
    print(f'::warning title=No git reads::{head_mismatch}', file=sys.stderr)
elif checkout and not typable:
    print(f'::warning title=No git reads::the agent cannot type the checkout path {checkout}', file=sys.stderr)
allow_git_reads = bool(checkout) and typable and not head_mismatch
# A literal path, because a `*` before the subcommand matches a global option that runs a program.
git_allowed = [f'Bash(git -C {checkout} {verb}:*)' for verb in GIT_READS] if allow_git_reads else []
git_denied = [f'Bash(git -C {checkout} {fence})' for fence in GIT_FENCES] if allow_git_reads else []

# `/` and an absolute path give the `//<path>` form, which Claude Code reads from the filesystem root.
allowed_tools = ','.join(filter(None, [
    os.environ.get('ALLOWED_TOOLS', ''),
    f'Edit(/{reviews_dir}/**)',
    f'Edit(/{collect_dir}/**)',
    f'Bash(python3 -m json.tool {review_file})',
    *git_allowed,
]))
allowed_plain, allowed_shell = split_tools(allowed_tools)
# An absolute path, because Claude Code 2.1.325 matches `Edit(./**)` in an --add-dir directory too.
disallowed_tools = ','.join(filter(None, [
    os.environ.get('DISALLOWED_TOOLS', ''),
    f'Edit(/{cortex_path}/**)',
    *git_denied,
]))
denied_plain, denied_shell = split_tools(disallowed_tools)
denied_shell = [command.replace(BACKSLASH, '\\') for command in denied_shell]
denied_git_words = list(dict.fromkeys(DENIED_GIT_WORD.findall(disallowed_tools)))
# Claude Code reads a rule that mixes a `*` with the trailing `:*` as a prefix that matches nothing.
for rule in re.findall(r'Bash\([^)]*\*[^)]*:\*\)', f'{allowed_tools},{disallowed_tools}'):
    print(f'::warning title=Dead permission rule::{rule} matches no command', file=sys.stderr)


def bullets(commands):
    """One shell command per line, so a long list stays readable in the log."""
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
surface += ['- These shell commands, and NOTHING else. An entry that ends on `…` is a command',
            '  prefix, and any arguments are allowed after it. An entry with no `…` is the whole',
            '  command:']
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
    f'- Every file you write goes under `{reviews_dir}`, the directory of the review file, or',
    f'  under `{collect_dir}`, the `--collect` directory, where a scratch file goes too. A write',
    '  anywhere else is refused, through Write and through a shell redirection alike. Write each',
    '  file with the Write tool: an `Edit(…)` path rule of the allow list admits Write under its',
    '  path, and the Edit tool itself is denied, so a fix of the review file writes the whole',
    '  file again.',
    '  `python3 -m json.tool` runs on the review file, in the one form that the list names.',
    '- cortex routes every `gh` write through `tools/gh-wrapper/bin/gh-wrapper`. You make no',
    '  write, and the list above carries the reads under both spellings, so either route',
    '  works. Use the one the list names; never retry a denied call through the other.',
    '- cortex denies `cd`, and it is not on the list above, so a directory is reached by',
    '  naming it: Read, Grep and Glob all take an absolute path.',
]
if allow_git_reads:
    surface += [
        f'  `git` runs in the pre-fetched checkout only as `git -C {checkout}`, with the path',
        '  written exactly so, followed by `diff`, `log`, `show`, `grep` or `blame`. Such a',
        '  command holds no quote, backslash, `$`, backtick or brace, and a `git grep` holds no',
        '  uppercase `O`, so search the files with Grep.',
    ]
    if denied_git_words:
        surface += [
            '  The deny list can also refuse a `git -C` read that has one of these words as an argument,',
            f"  so search such a word with Grep: {', '.join(f'`{word}`' for word in denied_git_words)}.",
        ]
    surface += [
        '  The clone is blobless, so `blame`, `log -p` and a `show` of an older commit fetch each',
        '  older file from GitHub, one by one: read `diff.patch` first.',
    ]
elif head_mismatch:
    surface += [
        f'  `git` reads no pull request: the run cannot show that the checkout at `{checkout}`',
        '  is at the reviewed head, so review none of its files. Read the change and its history',
        '  from `diff.patch` and `pr.json` instead.',
    ]
elif checkout:
    surface += [
        f'  `git` cannot run in the checkout at `{checkout}`, because no command of the list',
        '  can carry its path. Read, Grep and Glob open its files, at the reviewed head. Read the',
        '  history from `diff.patch` and `pr.json`.',
    ]
else:
    surface += [
        '  `git` reads no pull request: this run has no checkout of it. Read the history from',
        '  `diff.patch` and `pr.json` instead.',
    ]

os.makedirs(log_dir, exist_ok=True)
with open(os.path.join(log_dir, 'review.prompt.md'), 'w', encoding='utf-8') as fh:
    fh.write(CALL + '\n')
with open(os.path.join(log_dir, 'review.system.md'), 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(surface) + '\n')
with open(os.path.join(log_dir, 'allowed-tools.txt'), 'w', encoding='utf-8') as fh:
    fh.write(allowed_tools + '\n')
with open(os.path.join(log_dir, 'disallowed-tools.txt'), 'w', encoding='utf-8') as fh:
    fh.write(disallowed_tools + '\n')

print(key)
