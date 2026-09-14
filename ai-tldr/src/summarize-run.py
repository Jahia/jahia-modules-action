"""Summarize one headless Claude Code run from its stream-json output.

Usage: summarize-run.py <stream-file> <label> <exit-code>

Prints a deterministic trace of everything the agent did (tool calls, messages,
final result) to stdout, writes the final result event next to the stream file
(<name>.result.json), and appends one row to $GITHUB_STEP_SUMMARY.
Always exits 0 — reporting must not mask the agent's own exit code.
"""
import json
import os
import sys

stream_path, key, exit_code = sys.argv[1], sys.argv[2], sys.argv[3]


def compact(value, limit=300):
    text = value if isinstance(value, str) else json.dumps(value)
    text = ' '.join(text.split())
    return text if len(text) <= limit else text[:limit] + '…'


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
                print(f'[warn] unparseable stream line: {compact(line, 120)}')
except OSError as error:
    print(f'[warn] could not read stream file: {error}')

result = None
print(f'--- Agent trace ({key}) ---')
for event in events:
    etype = event.get('type')
    if etype == 'system' and event.get('subtype') == 'init':
        print(f"[init] model={event.get('model')} cwd={event.get('cwd')}")
    elif etype == 'assistant':
        for block in event.get('message', {}).get('content', []) or []:
            if block.get('type') == 'text':
                print(f"[say ] {compact(block.get('text', ''))}")
            elif block.get('type') == 'tool_use':
                print(f"[tool] {block.get('name')} {compact(block.get('input', {}))}")
    elif etype == 'result':
        result = event

if result is None:
    outcome, turns, duration, cost = 'no result (crash/kill)', 'n/a', 'n/a', 'n/a'
    print(f'[end ] no result event found, agent exit code {exit_code}')
else:
    outcome = result.get('subtype', 'unknown')
    if result.get('is_error'):
        outcome = f'error ({outcome})'
    turns = result.get('num_turns', 'n/a')
    ms = result.get('duration_ms')
    duration = f'{round(ms / 1000)}s' if isinstance(ms, (int, float)) else 'n/a'
    usd = result.get('total_cost_usd')
    cost = f'{usd:.4f}' if isinstance(usd, (int, float)) else 'n/a'
    print(f'[end ] {outcome} turns={turns} duration={duration} cost=${cost} exit={exit_code}')
    print(f'[result] {compact(result.get("result", ""), 2000)}')
    result_path = stream_path.replace('.stream.jsonl', '.result.json')
    with open(result_path, 'w', encoding='utf-8') as fh:
        json.dump(result, fh, indent=2)

summary_path = os.environ.get('GITHUB_STEP_SUMMARY')
if summary_path:
    with open(summary_path, 'a', encoding='utf-8') as fh:
        fh.write(f'| {key} | {outcome} | {turns} | {duration} | {cost} | {exit_code} |\n')
