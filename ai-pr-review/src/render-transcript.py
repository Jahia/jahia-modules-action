"""Render a headless Claude Code stream-json log as a human-readable transcript.

Usage: render-transcript.py <stream-file> <output-file>

Events are rendered in session order: assistant text in full, tool calls with
their input, tool results, and the final result. Unlike the console trace
(summarize-run.py, which compacts everything to one line per event), this is
the file to read when asking what happened during the session.
Always exits 0 — rendering must not mask the agent's own exit code.
"""
import json
import sys

stream_path, out_path = sys.argv[1], sys.argv[2]


def clip(value, limit):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
    if len(text) <= limit:
        return text
    return text[:limit] + f'\n… [truncated — {len(text)} chars total, see review.stream.jsonl]'


lines = []
try:
    with open(stream_path, encoding='utf-8') as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                lines += ['[unparseable stream line] ' + raw[:200], '']
                continue
            etype = event.get('type')
            if etype == 'system' and event.get('subtype') == 'init':
                lines += [f"=== session {event.get('session_id')} | model {event.get('model')} | cwd {event.get('cwd')} ===", '']
            elif etype == 'assistant':
                for block in event.get('message', {}).get('content', []) or []:
                    if block.get('type') == 'text':
                        lines += ['--- assistant ---', block.get('text', ''), '']
                    elif block.get('type') == 'tool_use':
                        lines += [f"--- tool call: {block.get('name')} ---",
                                  clip(block.get('input', {}), 4000), '']
            elif etype == 'user':
                for block in event.get('message', {}).get('content', []) or []:
                    if isinstance(block, dict) and block.get('type') == 'tool_result':
                        content = block.get('content')
                        if isinstance(content, list):
                            content = '\n'.join(c.get('text', '') for c in content
                                                if isinstance(c, dict))
                        prefix = 'tool result (error)' if block.get('is_error') else 'tool result'
                        lines += [f'--- {prefix} ---', clip(content or '', 4000), '']
            elif etype == 'result':
                lines += ['=== result ===',
                          f"outcome={event.get('subtype')} turns={event.get('num_turns')} "
                          f"duration_ms={event.get('duration_ms')} cost_usd={event.get('total_cost_usd')}",
                          '', clip(event.get('result', ''), 20000)]
except OSError as error:
    lines += [f'[could not read stream file: {error}]']

with open(out_path, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(lines) + '\n')
print(f'Transcript written: {out_path}')
