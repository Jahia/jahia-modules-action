"""Summarize one headless Claude Code run from its stream-json output.

Usage: summarize-run.py <stream-file> <label> <exit-code> [--no-trace]

Prints a deterministic trace of everything the agent did (tool calls, messages,
final result) to stdout, writes the final result event next to the stream file
(<name>.result.json), and appends one row to $GITHUB_STEP_SUMMARY.
With --no-trace, only the outcome is reported: use it when stream-progress.py has
already narrated the run live and replaying it here would just double the log.
Always exits 0 — reporting must not mask the agent's own exit code.
"""
import json
import os
import sys

stream_path, key, exit_code = sys.argv[1], sys.argv[2], sys.argv[3]
trace = '--no-trace' not in sys.argv[4:]


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
# Every model that actually answered, in the order each was first seen. The run is
# configured with one, but a fallback or a downgrade under load substitutes another without
# the agent being told -- so the summary reports what answered rather than what was asked
# for, and a reader weighing the review can see when it was not written by a single model.
# A subagent answering on its own model is a delegation, not the main thread switching, so
# the two are counted apart: folded together they would read as a switch that never happened.
models = []
subagent_models = []
if trace:
    print(f'--- Agent trace ({key}) ---')
for event in events:
    etype = event.get('type')
    if etype == 'result':
        result = event
        continue
    if etype == 'assistant':
        model = event.get('message', {}).get('model')
        seen = subagent_models if event.get('parent_tool_use_id') else models
        if model and model not in seen:
            seen.append(model)
    if not trace:
        continue
    if etype == 'system' and event.get('subtype') == 'init':
        print(f"[init] model={event.get('model')} cwd={event.get('cwd')}")
    elif etype == 'assistant':
        for block in event.get('message', {}).get('content', []) or []:
            if block.get('type') == 'text':
                print(f"[say ] {compact(block.get('text', ''))}")
            elif block.get('type') == 'tool_use':
                print(f"[tool] {block.get('name')} {compact(block.get('input', {}))}")

models_text = ' → '.join(models) if models else 'unknown'
if subagent_models:
    models_text += f" (subagents: {', '.join(subagent_models)})"
print(f'[model] {models_text}' + (' — the main thread SWITCHED models' if len(models) > 1 else ''))

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
        fh.write(f'| {key} | {outcome} | {models_text} | {turns} | {duration} | {cost} | '
                 f'{exit_code} |\n')
