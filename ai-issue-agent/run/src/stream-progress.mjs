// Tee a headless Claude Code stream-json run to disk while narrating it live.
//
// Usage: claude … --output-format stream-json | node stream-progress.mjs <stream-file>
//
// Reads the CLI's stream-json on stdin, writes every line verbatim to <stream-file> (that
// file stays the raw record the sidecar and the denied-calls tally read), and prints one
// compact line per interesting event to stdout — so the job log shows what the agent is
// doing while it does it, instead of staying silent until the run ends. JS port of
// ai-pr-review/src/stream-progress.py, on github-script's Node (a self-hosted runner
// guarantees no `node` on PATH, so the caller passes the binary the context step captured).
//
// Writing the raw line always happens first and rendering can never throw out: a display
// bug must not cost us the session record. Always exits 0 — narrating must not mask the
// agent's own exit code (the caller reads it from PIPESTATUS).
import { openSync, writeSync } from 'node:fs'
import { createInterface } from 'node:readline'

const streamPath = process.argv[2]

// One heartbeat at most per this many ms of otherwise silent thinking: a model that thinks
// for minutes would look hung without it, and a chatty one must not flood.
const HEARTBEAT_MS = 60000

const started = Date.now()
let lastLineAt = started
// tool_use_ids already reported as denied: their tool_result is that same denial coming
// back as an error, and reporting it twice reads like two distinct failures.
const deniedIds = new Set()
// tool_use_id -> what that call was doing. A permission_denied event names the tool and the
// reason but not the call, and "Bash was denied" is useless next to the command that was.
const pendingCalls = new Map()
// Which model each thread of the run is answering on: '' for the main one, the spawning
// tool_use_id for a subagent's. Asking the agent to narrate its own model is not enough —
// a fallback, or a downgrade under load, is done TO it and it has no reason to notice.
const seenModels = new Map()

const elapsed = () => {
  const total = Math.floor((Date.now() - started) / 1000)
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const seconds = total % 60
  const pad = (n) => String(n).padStart(2, '0')
  return hours ? `${hours}:${pad(minutes)}:${pad(seconds)}` : `${minutes}:${pad(seconds)}`
}

const emit = (tag, text) => {
  lastLineAt = Date.now()
  process.stdout.write(`${elapsed().padStart(7)}  ${tag.padEnd(7)} ${text}\n`)
}

const compact = (value, limit = 220) => {
  const text = typeof value === 'string' ? value : JSON.stringify(value)
  const squashed = (text ?? '').split(/\s+/).join(' ').trim()
  return squashed.length <= limit ? squashed : `${squashed.slice(0, limit)}…`
}

// The one field that says what a tool call is actually doing, when there is one.
const describeTool = (input) => {
  if (typeof input !== 'object' || input === null) return compact(input)
  for (const key of ['command', 'file_path', 'pattern', 'url', 'skill', 'description', 'prompt', 'path']) {
    if (typeof input[key] === 'string' && input[key].trim()) return compact(input[key])
  }
  return compact(input)
}

// Report the model a message came from, the first time and on every change. A subagent
// answering on its own model is not the main thread switching, so each thread is tracked
// apart; the tool_use_id that spawned it names it in the log.
const noteModel = (event) => {
  const model = event.message?.model
  if (!model) return
  const thread = event.parent_tool_use_id ?? ''
  if (seenModels.get(thread) === model) return
  const previous = seenModels.get(thread)
  seenModels.set(thread, model)
  const where = thread ? `subagent ${thread}` : 'main'
  emit('model', previous ? `${where} · SWITCHED from ${previous} to ${model}` : `${where} · running on ${model}`)
}

const render = (event) => {
  if (typeof event !== 'object' || event === null) return
  const { type, subtype } = event

  if (type === 'system' && subtype === 'init') {
    emit('init', `model ${event.model} · cwd ${event.cwd} · ${(event.tools ?? []).length} tools`)
    // The init model is what was requested; the first assistant message says what actually
    // answered, so a run starting on something else says so on its first turn.
    seenModels.set('', event.model)
  } else if (type === 'system' && subtype === 'thinking_tokens') {
    // Pure counter events (tens of thousands per run) — never printed one for one, only as
    // a liveness sign when nothing else has been said for a while.
    if (Date.now() - lastLineAt >= HEARTBEAT_MS) {
      const tokens = event.estimated_tokens
      emit('…', `still thinking${Number.isInteger(tokens) ? ` (≈${tokens} tokens into this thought)` : ''}`)
    }
  } else if (type === 'system' && subtype === 'permission_denied') {
    if (event.tool_use_id) deniedIds.add(event.tool_use_id)
    // The event's own message is permission boilerplate; the call is the news.
    const call = pendingCalls.get(event.tool_use_id) ?? event.tool_name
    pendingCalls.delete(event.tool_use_id)
    emit('denied', `${call} · reason: ${event.decision_reason_type ?? 'unknown'}`)
  } else if (type === 'system' && subtype === 'api_retry') {
    const delay = typeof event.retry_delay_ms === 'number' ? ` · retrying in ${(event.retry_delay_ms / 1000).toFixed(1)}s` : ''
    emit('retry', `HTTP ${event.error_status} ${event.error} · attempt ${event.attempt}/${event.max_retries}${delay}`)
  } else if (type === 'system' && subtype === 'task_started') {
    emit('task', `started · ${compact(event.description ?? '', 160)}`)
  } else if (type === 'system' && subtype === 'task_notification') {
    emit('task', `${event.status} · ${compact(event.summary ?? '', 160)}`)
  } else if (type === 'assistant') {
    noteModel(event)
    for (const block of event.message?.content ?? []) {
      if (typeof block !== 'object' || block === null) continue
      if (block.type === 'thinking') emit('think', compact(block.thinking ?? ''))
      else if (block.type === 'text') emit('say', compact(block.text ?? ''))
      else if (block.type === 'tool_use') {
        const call = `${block.name} · ${describeTool(block.input)}`
        if (block.id) pendingCalls.set(block.id, call)
        emit('tool', call)
      }
    }
  } else if (type === 'user') {
    for (const block of event.message?.content ?? []) {
      if (typeof block !== 'object' || block === null || block.type !== 'tool_result') continue
      pendingCalls.delete(block.tool_use_id)
      if (deniedIds.has(block.tool_use_id)) continue
      let content = block.content
      if (Array.isArray(content)) {
        content = content
          .filter((part) => typeof part === 'object' && part !== null && part.type === 'text')
          .map((part) => part.text ?? '')
          .join(' ')
      }
      emit(block.is_error ? 'err' : 'ok', compact(content ?? '', 160))
    }
  } else if (type === 'result') {
    // ai-pr-review hands this to summarize-run.py; here the one line IS the summary.
    const duration = typeof event.duration_ms === 'number' ? ` · ${Math.round(event.duration_ms / 1000)}s` : ''
    const cost = typeof event.total_cost_usd === 'number' ? ` · $${event.total_cost_usd.toFixed(2)}` : ''
    emit('result', `${subtype} · ${event.num_turns} turns${duration}${cost}`)
  }
}

const streamFd = openSync(streamPath, 'w')
const lines = createInterface({ input: process.stdin, crlfDelay: Infinity })
lines.on('line', (raw) => {
  writeSync(streamFd, `${raw}\n`)
  if (!raw.trim()) return
  try {
    render(JSON.parse(raw))
  } catch (error) {
    emit('?', `unrenderable stream line (${error})`)
  }
})
