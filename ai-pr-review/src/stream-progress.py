"""Tee a headless Claude Code stream-json run to disk while narrating it live.

Usage: claude … --output-format stream-json | python3 -u stream-progress.py <stream-file>

Reads the CLI's stream-json on stdin, writes every line verbatim to <stream-file>
(that file stays the raw record the transcript is rendered from), and prints one
compact, immediately-flushed line per interesting event to stdout — so the job log
shows what the agent is doing while it does it, instead of staying silent until the
run ends.

Writing the raw line always happens first and rendering can never raise: a display
bug must not cost us the session record. Always exits 0 — narrating must not mask
the agent's own exit code (the caller reads it from PIPESTATUS).
"""
import json
import sys
import time

stream_path = sys.argv[1]

# One heartbeat at most per this many seconds of otherwise silent thinking: a model
# that thinks for minutes would look hung without it, and a chatty one must not flood.
HEARTBEAT_SECONDS = 60

started = time.monotonic()
last_line_at = started
# tool_use_ids already reported as denied: their tool_result is that same denial
# coming back as an error, and reporting it twice reads like two distinct failures.
denied_ids = set()
# tool_use_id -> what that call was doing. A permission_denied event names the tool and the
# reason but not the call, and "Bash was denied" is useless next to the command that was.
pending_calls = {}


def elapsed():
    total = int(time.monotonic() - started)
    hours, rest = divmod(total, 3600)
    minutes, seconds = divmod(rest, 60)
    if hours:
        return f'{hours}:{minutes:02d}:{seconds:02d}'
    return f'{minutes}:{seconds:02d}'


def emit(tag, text):
    global last_line_at
    last_line_at = time.monotonic()
    print(f'{elapsed():>7}  {tag:<7} {text}', flush=True)


def compact(value, limit=220):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = ' '.join(text.split())
    return text if len(text) <= limit else text[:limit] + '…'


def describe_tool(tool_input):
    """The one field that says what a tool call is actually doing, when there is one."""
    if not isinstance(tool_input, dict):
        return compact(tool_input)
    for key in ('command', 'file_path', 'pattern', 'url', 'skill', 'description', 'prompt', 'path'):
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            return compact(value)
    return compact(tool_input)


def render(event):
    if not isinstance(event, dict):
        return
    etype, subtype = event.get('type'), event.get('subtype')

    if etype == 'system' and subtype == 'init':
        tools = event.get('tools') or []
        emit('init', f"model {event.get('model')} · cwd {event.get('cwd')} · {len(tools)} tools")

    elif etype == 'system' and subtype == 'thinking_tokens':
        # Pure counter events (tens of thousands per run) — never printed one for one,
        # only as a liveness sign when nothing else has been said for a while.
        if time.monotonic() - last_line_at >= HEARTBEAT_SECONDS:
            tokens = event.get('estimated_tokens')
            suffix = f' (≈{tokens} tokens into this thought)' if isinstance(tokens, int) else ''
            emit('…', f'still thinking{suffix}')

    elif etype == 'system' and subtype == 'permission_denied':
        tool_use_id = event.get('tool_use_id')
        if tool_use_id:
            denied_ids.add(tool_use_id)
        # The event's own message is permission boilerplate; the call is the news.
        call = pending_calls.pop(tool_use_id, None) or event.get('tool_name')
        emit('denied', f"{call} · reason: {event.get('decision_reason_type') or 'unknown'}")

    elif etype == 'system' and subtype == 'api_retry':
        delay = event.get('retry_delay_ms')
        delay_text = f' · retrying in {delay / 1000:.1f}s' if isinstance(delay, (int, float)) else ''
        emit('retry', f"HTTP {event.get('error_status')} {event.get('error')} · "
                      f"attempt {event.get('attempt')}/{event.get('max_retries')}{delay_text}")

    elif etype == 'system' and subtype == 'task_started':
        emit('task', f"started · {compact(event.get('description', ''), 160)}")

    elif etype == 'system' and subtype == 'task_notification':
        emit('task', f"{event.get('status')} · {compact(event.get('summary', ''), 160)}")

    elif etype == 'assistant':
        for block in (event.get('message') or {}).get('content') or []:
            if not isinstance(block, dict):
                continue
            kind = block.get('type')
            if kind == 'thinking':
                emit('think', compact(block.get('thinking', '')))
            elif kind == 'text':
                emit('say', compact(block.get('text', '')))
            elif kind == 'tool_use':
                call = f"{block.get('name')} · {describe_tool(block.get('input'))}"
                if block.get('id'):
                    pending_calls[block['id']] = call
                emit('tool', call)

    elif etype == 'user':
        for block in (event.get('message') or {}).get('content') or []:
            if not isinstance(block, dict) or block.get('type') != 'tool_result':
                continue
            pending_calls.pop(block.get('tool_use_id'), None)
            if block.get('tool_use_id') in denied_ids:
                continue
            content = block.get('content')
            if isinstance(content, list):
                content = ' '.join(part.get('text', '') for part in content
                                   if isinstance(part, dict) and part.get('type') == 'text')
            emit('err' if block.get('is_error') else 'ok', compact(content or '', 160))

    # 'result' is deliberately not rendered here: summarize-run.py reports the outcome,
    # the turn count, the duration and the cost from it right after this process ends.


with open(stream_path, 'w', encoding='utf-8') as stream_file:
    for raw in sys.stdin:
        stream_file.write(raw)
        stream_file.flush()
        raw = raw.strip()
        if not raw:
            continue
        try:
            render(json.loads(raw))
        except Exception as error:  # noqa: BLE001 — narrating must never kill the run
            print(f'{elapsed():>7}  {"?":<7} unrenderable stream line ({error})', flush=True)
