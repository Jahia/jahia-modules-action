// Rewrite the PR's status comment periodically with the run's progress, read off the
// review.stream.jsonl file the narrator (stream-progress.py) tees to disk — so the stats
// cost GitHub API calls and no model tokens, and the narrator needs no change.
//
// Spawned DETACHED by the "Start the status-comment progress updater" github-script step
// of action.yml, on github-script's own Node (process.execPath — a self-hosted runner
// guarantees no `node` on PATH). That step resolves the sticky comment and passes
// COMMENT_URL and BASE_BODY; the matching stop step kills this process once the agent is
// done, and the lifetime deadline below is the backstop for the kill that never comes (a
// hard-cancelled job must not leave an orphan PATCHing forever).
//
// Best-effort by contract: it writes only the one comment and its own log file, tolerates
// the stream file not existing yet, goes quiet after FAILURES_TOLERATED consecutive API
// errors, and always preserves the marker — it is how the workflow's sticky-comment steps
// find the comment after this run.
import { appendFileSync } from 'node:fs'
import { open } from 'node:fs/promises'

const FAILURES_TOLERATED = 3

const commentUrl = process.env.COMMENT_URL
const baseBody = process.env.BASE_BODY ?? ''
const marker = process.env.STATUS_COMMENT_MARKER ?? ''
const streamFile = process.env.STREAM_FILE ?? ''
const logFile = process.env.UPDATER_LOG ?? ''
// Floor, not a default: a sub-30s cadence spends API quota to animate a comment nobody
// is notified about (GitHub notifies no one on an edit).
const intervalMs = Math.max(30, Number(process.env.STATUS_UPDATE_SECONDS) || 90) * 1000
const deadline = Date.now() + (Number(process.env.JOB_TIMEOUT_MINUTES) || 30) * 60000

const started = Date.now()
let offset = 0
let remainder = ''
let tools = 0
let denied = 0
let last = ''

const log = (text) => {
  if (!logFile) return
  try { appendFileSync(logFile, `${elapsed()} ${text}\n`) } catch { /* logging is optional */ }
}

function elapsed() {
  const total = Math.floor((Date.now() - started) / 1000)
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const seconds = total % 60
  const pad = (n) => String(n).padStart(2, '0')
  return hours ? `${hours}:${pad(minutes)}:${pad(seconds)}` : `${minutes}:${pad(seconds)}`
}

// Backticks swapped out so the text cannot escape the code span it is shown in.
const compact = (text) => text.replace(/\s+/g, ' ').replaceAll('`', "'").trim().slice(0, 160)

// The one field that says what a tool call is actually doing, when there is one
// (same key order as the narrator's describe_tool).
function describeTool(input) {
  if (typeof input !== 'object' || input === null) return compact(String(input ?? ''))
  for (const key of ['command', 'file_path', 'pattern', 'url', 'skill', 'description', 'prompt', 'path']) {
    if (typeof input[key] === 'string' && input[key].trim()) return compact(input[key])
  }
  return compact(JSON.stringify(input))
}

function note(event) {
  if (event?.type === 'assistant') {
    for (const block of event.message?.content ?? []) {
      if (block?.type === 'tool_use') {
        tools += 1
        last = compact(`${block.name} · ${describeTool(block.input)}`)
      } else if (block?.type === 'text' && block.text?.trim()) {
        last = compact(block.text)
      }
    }
  } else if (event?.type === 'system' && event.subtype === 'permission_denied') {
    denied += 1
  }
}

// Read only what the narrator appended since last tick; a partial last line waits in
// `remainder` for its other half. The file not existing yet (agent not started) is normal.
async function readNewEvents() {
  let handle
  try {
    handle = await open(streamFile, 'r')
  } catch {
    return
  }
  try {
    const { size } = await handle.stat()
    if (size <= offset) return
    const chunk = Buffer.alloc(size - offset)
    await handle.read(chunk, 0, chunk.length, offset)
    offset = size
    const lines = (remainder + chunk.toString('utf-8')).split('\n')
    remainder = lines.pop() ?? ''
    for (const line of lines) {
      if (!line.trim()) continue
      try { note(JSON.parse(line)) } catch { /* a malformed line is the narrator's problem */ }
    }
  } finally {
    await handle.close()
  }
}

async function updateComment() {
  const deniedText = denied ? ` (${denied} denied)` : ''
  let stats = `⏱ ${elapsed()} elapsed · ${tools} tool calls${deniedText}`
  if (last) stats += `\nLast activity: \`${last}\``
  const response = await fetch(commentUrl, {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${process.env.GH_TOKEN}`,
      Accept: 'application/vnd.github+json',
      'User-Agent': 'jahia-ai-pr-review',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ body: `${baseBody}\n\n${stats}\n${marker}` }),
    signal: AbortSignal.timeout(10000),
  })
  if (!response.ok) throw new Error(`PATCH ${commentUrl}: HTTP ${response.status}`)
  log(`updated: ${tools} tool calls${deniedText}`)
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

if (!commentUrl || !marker || !process.env.GH_TOKEN || !streamFile) {
  log('missing COMMENT_URL/STATUS_COMMENT_MARKER/GH_TOKEN/STREAM_FILE — nothing to do')
  process.exit(0)
}
log(`started: every ${intervalMs / 1000}s on ${commentUrl}`)
let failures = 0
while (Date.now() < deadline) {
  await sleep(intervalMs)
  try {
    await readNewEvents()
    await updateComment()
    failures = 0
  } catch (error) {
    failures += 1
    log(`update failed (${failures}/${FAILURES_TOLERATED}): ${error}`)
    if (failures >= FAILURES_TOLERATED) process.exit(0)
  }
}
log('lifetime deadline reached — exiting')
