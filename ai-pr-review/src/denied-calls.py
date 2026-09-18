"""Collect every call the permission layer refused, from one run's stream-json.

Usage: denied-calls.py <stream-file> <output-file> [--label <run label>]
Env:   ALLOWED_TOOLS - optional: the --allowedTools value the run used, so the
                       report can say which part of a refused command is the
                       one that is not allowed

Writes <output-file> (markdown, lands in the run artifact) and appends the same
table to $GITHUB_STEP_SUMMARY. Always exits 0: reporting must not mask the
agent's own exit code.

This is a deterministic pass over the stream, not something the agent reports
about itself. An agent that has just been refused is the least reliable witness
to what it was refused -- on the run this was built from it concluded that Bash
had been removed entirely -- and asking it to keep its own tally spends the
budget the allowlist is already costing. Every refusal is in the stream as a
`permission_denied` event, so the tally is a read, not a memory.

The point is the next allowlist: a refusal that keeps recurring across runs is a
tool the review needs and does not have.
"""
import json
import os
import re
import shlex
import sys

stream_path, out_path = sys.argv[1], sys.argv[2]
label = sys.argv[sys.argv.index('--label') + 1] if '--label' in sys.argv else ''

# Commands that are a driver plus a verb: the useful prefix is two tokens, not one.
# `gh` alone says nothing -- `gh api` is refused where `gh pr view` is allowed.
DRIVERS = {'gh', 'git', 'npm', 'npx', 'yarn', 'pnpm', 'mvn', 'docker', 'python3', 'python',
           'pip', 'pip3', 'cargo', 'go', 'kubectl', 'helm', 'mise'}
# `gh pr` is not a prefix either: `gh pr view` is allowed where `gh pr merge` is denied.
# These are the gh nouns whose verb carries the permission, so they take a third token.
GH_NOUNS = {'pr', 'issue', 'repo', 'release', 'run', 'workflow', 'cache', 'secret', 'label'}
PIPE_TOKENS = {'|', '||', '&&', ';', '&'}


def split_entries(value):
    """Split an --allowedTools value on top-level commas (a Bash(...) entry holds its own)."""
    entries, depth, current = [], 0, ''
    for char in value:
        if char == ',' and depth == 0:
            entries.append(current.strip())
            current = ''
            continue
        depth += (char == '(') - (char == ')')
        current += char
    entries.append(current.strip())
    return [entry for entry in entries if entry]


allowed_prefixes = set()
for entry in split_entries(os.environ.get('ALLOWED_TOOLS', '')):
    match = re.fullmatch(r'Bash\((.*)\)', entry)
    if match:
        allowed_prefixes.add(match.group(1).rstrip('*').rstrip(':').strip())


def is_gh(token):
    """`gh`, or the cortex wrapper that forwards to it."""
    name = token.rsplit('/', 1)[-1]
    return name == 'gh' or name.endswith('gh-wrapper')


def prefix_of(tokens):
    """The command prefix an allowlist rule would name, e.g. `gh pr view` or `jq`."""
    tokens = [t for t in tokens if not re.match(r'^\d*[<>]', t)]  # drop redirections
    if not tokens:
        return ''
    if is_gh(tokens[0]) and len(tokens) > 2 and tokens[1] in GH_NOUNS:
        return ' '.join(tokens[:3])
    if (is_gh(tokens[0]) or tokens[0] in DRIVERS) and len(tokens) > 1 \
            and not tokens[1].startswith('-'):
        return ' '.join(tokens[:2])
    return tokens[0]


def subcommands(command):
    """The individual commands in a pipeline or chain, as token lists.

    A refusal reported as `subcommandResults` means ONE stage of a pipeline was not
    allowed -- naming the whole line would send the reader looking at the wrong command.
    The split is on TOKENS, not on the raw text: a `--jq` argument is full of `|` and
    splitting the string turns one refused command into a page of nonsense prefixes.
    """
    try:
        tokens = shlex.split(command)
    except ValueError:  # unbalanced quotes -- the command is still worth one line
        tokens = command.split()
    parts, current = [], []
    for token in tokens:
        if token in PIPE_TOKENS:
            if current:
                parts.append(current)
            current = []
            continue
        current.append(token)
    if current:
        parts.append(current)
    return parts


events = []
try:
    with open(stream_path, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
except OSError as error:
    print(f'[warn] could not read the stream file: {error}')

# tool_use_id -> (tool name, what the call was doing). A permission_denied event names the
# tool and the reason, never the call, and "Bash was denied" is useless next to the command.
calls = {}
denials = []
for event in events:
    if event.get('type') == 'assistant':
        for block in (event.get('message') or {}).get('content') or []:
            if isinstance(block, dict) and block.get('type') == 'tool_use' and block.get('id'):
                value = block.get('input') or {}
                detail = value.get('command') if isinstance(value, dict) else None
                if not detail:
                    detail = json.dumps(value, ensure_ascii=False) if value else ''
                calls[block['id']] = (block.get('name', '?'), ' '.join(str(detail).split()))
    elif event.get('type') == 'system' and event.get('subtype') == 'permission_denied':
        tool, detail = calls.get(event.get('tool_use_id'), (event.get('tool_name', '?'), ''))
        denials.append((tool, detail, event.get('decision_reason_type') or 'unknown'))

# Same command refused five times is one gap, not five.
tally = {}
for item in denials:
    tally[item] = tally.get(item, 0) + 1

lines = [f'## Calls the permission layer refused{f" — {label}" if label else ""}', '']
if not denials:
    lines += ['None. Every tool call the agent made was allowed.', '']
else:
    lines += [f'{len(denials)} refused call(s), {len(tally)} distinct.', '',
              '| # | Tool | Refused call | Reason |', '|---|---|---|---|']
    for (tool, detail, reason), count in sorted(tally.items(), key=lambda kv: -kv[1]):
        shown = detail if len(detail) <= 160 else detail[:160] + '…'
        # A raw pipe would end the table column, and a shell command is mostly pipes.
        shown = shown.replace('|', '\\|') or '(no detail)'
        lines.append(f'| {count} | `{tool}` | `{shown}` | {reason} |')

    # The actionable half: what would have to be allowed for these to run.
    wanted = {}
    for (tool, detail, _reason), count in tally.items():
        if tool != 'Bash' or not detail:
            wanted.setdefault(tool, 0)
            wanted[tool] += count
            continue
        for part in subcommands(detail):
            prefix = prefix_of(part)
            if prefix and prefix not in allowed_prefixes:
                wanted[f'Bash({prefix}:*)'] = wanted.get(f'Bash({prefix}:*)', 0) + count
    if wanted:
        lines += ['', '### Not on the allowlist', '',
                  'One line per thing the agent reached for and did not have. Allowing one is a',
                  'deliberate call, not a formality — the deny list exists to keep this agent',
                  'review-only, and some of these are refused on purpose.', '']
        for name, count in sorted(wanted.items(), key=lambda kv: -kv[1]):
            lines.append(f'- `{name}` — reached for {count}×')
lines.append('')
report = '\n'.join(lines)

try:
    with open(out_path, 'w', encoding='utf-8') as fh:
        fh.write(report)
except OSError as error:
    print(f'[warn] could not write {out_path}: {error}')

summary_path = os.environ.get('GITHUB_STEP_SUMMARY')
if summary_path:
    try:
        with open(summary_path, 'a', encoding='utf-8') as fh:
            fh.write('\n' + report)
    except OSError as error:
        print(f'[warn] could not append to the job summary: {error}')

print(f'[denied] {len(denials)} refused call(s), {len(tally)} distinct -> {out_path}')
