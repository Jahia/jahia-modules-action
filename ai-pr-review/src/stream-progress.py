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

When STATUS_COMMENT_MARKER is set (with GH_TOKEN and PR_URL), a background thread
also rewrites the PR's status comment with the run's progress every
STATUS_UPDATE_SECONDS — see StatusCommentUpdater.
"""
import json
import os
import re
import sys
import threading
import time
import urllib.request

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
# Which model each thread of the run is answering on: None for the main one, the spawning
# tool_use_id for a subagent's. Asking the agent to narrate its own model is not enough --
# a fallback, or a downgrade under load, is done TO it and it has no reason to notice. Every
# message states the model it came from, so the switch is read from the stream instead.
seen_models = {}


def elapsed():
    total = int(time.monotonic() - started)
    hours, rest = divmod(total, 3600)
    minutes, seconds = divmod(rest, 60)
    if hours:
        return f'{hours}:{minutes:02d}:{seconds:02d}'
    return f'{minutes}:{seconds:02d}'


class StatusCommentUpdater:
    """Rewrite the PR's status comment periodically with the run's progress.

    Purely mechanical: the stats come from the stream this script already parses,
    so an update costs GitHub API calls and no model tokens. It runs on a daemon
    thread so a slow or failing GitHub API can never stall the tee loop (a stalled
    loop fills the pipe buffer and blocks the agent itself), and it is best-effort
    throughout: it goes quiet after FAILURES_TOLERATED consecutive errors, and the
    comment's final state stays the calling workflow's job — deleted on success,
    rewritten into a failure note otherwise — which also sweeps away whatever
    stats the last update left.

    Off unless STATUS_COMMENT_MARKER, GH_TOKEN and PR_URL are all set. The marker
    both finds the comment and must survive every rewrite: it is how the sticky
    comment steps of the workflow find the comment after this run.
    """

    FAILURES_TOLERATED = 3

    def __init__(self):
        self.marker = os.environ.get('STATUS_COMMENT_MARKER', '').strip()
        self.token = os.environ.get('GH_TOKEN', '')
        match = re.search(r'/([^/]+)/([^/]+)/pull/(\d+)$', os.environ.get('PR_URL', ''))
        self.enabled = bool(self.marker and self.token and match)
        if not self.enabled:
            return
        self.owner, self.repo, self.number = match.groups()
        self.api = os.environ.get('GITHUB_API_URL', 'https://api.github.com').rstrip('/')
        try:
            interval = int(os.environ.get('STATUS_UPDATE_SECONDS', '90'))
        except ValueError:
            interval = 90
        # Floor, not a default: a sub-30s cadence spends API quota to animate a
        # comment nobody is notified about (GitHub notifies no one on an edit).
        self.interval = max(30, interval)
        self.tools = 0
        self.denied = 0
        self.last = ''
        self.comment_id = None
        self.base_body = ''
        threading.Thread(target=self._loop, daemon=True).start()

    def note(self, tag, text):
        """Called by emit() for every narrated line; must stay trivially cheap."""
        if not self.enabled:
            return
        if tag == 'tool':
            self.tools += 1
        elif tag == 'denied':
            self.denied += 1
        if tag in ('tool', 'say', 'task'):
            # Backticks swapped out so the text cannot escape its code span.
            self.last = text.replace('`', "'")[:160]

    def _request(self, method, path, payload=None):
        data = json.dumps(payload).encode('utf-8') if payload is not None else None
        request = urllib.request.Request(
            f'{self.api}{path}', data=data, method=method,
            headers={'Authorization': f'Bearer {self.token}',
                     'Accept': 'application/vnd.github+json',
                     'User-Agent': 'jahia-ai-pr-review'})
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.load(response)

    def _find_comment(self):
        """Locate the sticky comment by its marker; remember its text as the base."""
        for page in range(1, 11):
            comments = self._request(
                'GET', f'/repos/{self.owner}/{self.repo}/issues/{self.number}'
                       f'/comments?per_page=100&page={page}')
            for comment in comments:
                if self.marker in (comment.get('body') or ''):
                    self.comment_id = comment['id']
                    self.base_body = comment['body'].replace(self.marker, '').strip()
                    return True
            if len(comments) < 100:
                return False
        return False

    def _loop(self):
        failures = 0
        while True:
            time.sleep(self.interval)
            try:
                if self.comment_id is None and not self._find_comment():
                    # No comment carries the marker: the workflow chose not to post
                    # one (review mode), so there is nothing to update, ever.
                    return
                denied = f' ({self.denied} denied)' if self.denied else ''
                stats = f'⏱ {elapsed()} elapsed · {self.tools} tool calls{denied}'
                if self.last:
                    stats += f'\nLast activity: `{self.last}`'
                self._request(
                    'PATCH',
                    f'/repos/{self.owner}/{self.repo}/issues/comments/{self.comment_id}',
                    {'body': f'{self.base_body}\n\n{stats}\n{self.marker}'})
                failures = 0
            except Exception as error:  # noqa: BLE001 — best-effort by contract
                failures += 1
                if failures >= self.FAILURES_TOLERATED:
                    print(f'{elapsed():>7}  {"warn":<7} status-comment updates stopped '
                          f'({error})', flush=True)
                    return


status = StatusCommentUpdater()


def emit(tag, text):
    global last_line_at
    last_line_at = time.monotonic()
    status.note(tag, text)
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


def note_model(event):
    """Report the model a message came from, the first time and on every change."""
    model = (event.get('message') or {}).get('model')
    if not model:
        return
    # A subagent answering on its own model is not the main thread switching, so each
    # thread is tracked apart; the tool_use_id that spawned it names it in the log.
    parent = event.get('parent_tool_use_id')
    if seen_models.get(parent, ...) == model:
        return
    previous = seen_models.get(parent)
    seen_models[parent] = model
    where = f'subagent {parent}' if parent else 'main'
    if previous is None:
        emit('model', f'{where} · running on {model}')
    else:
        emit('model', f'{where} · SWITCHED from {previous} to {model}')


def render(event):
    if not isinstance(event, dict):
        return
    etype, subtype = event.get('type'), event.get('subtype')

    if etype == 'system' and subtype == 'init':
        tools = event.get('tools') or []
        emit('init', f"model {event.get('model')} · cwd {event.get('cwd')} · {len(tools)} tools")
        # The init model is what was requested; the first assistant message says what
        # actually answered. Recording it here keeps the two comparable, so a run that
        # starts on something other than the configured model says so on its first turn.
        seen_models[None] = event.get('model')

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
        note_model(event)
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
