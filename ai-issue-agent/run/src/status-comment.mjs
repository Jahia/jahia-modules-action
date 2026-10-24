// Append the run's progress (elapsed, tool calls, last activity) to the session's TASK
// comment periodically, read off the stream file the agent step tees to disk — so the
// stats cost GitHub API calls and no model tokens. Port of ai-pr-review's sidecar, with
// one structural difference: the PR review owns a sticky status comment that exists before
// the agent starts, while the issue agent CREATES its task comment (marker
// `<!-- cortex-issue-agent-task run:<run id> -->`) as its first act — so this sidecar
// polls for the comment, and re-fetches the body on every tick because the agent keeps
// editing it in place (the stats tail below the progress marker is this sidecar's only
// territory; everything above it is the agent's).
//
// Spawned DETACHED by the "Start the task-comment progress updater" github-script step of
// action.yml, on github-script's own Node (process.execPath — a self-hosted runner
// guarantees no `node` on PATH); the matching stop step kills it, and the lifetime
// deadline below covers the kill that never comes (a hard-cancelled job must not leave an
// orphan PATCHing forever).
//
// Best-effort by contract: it writes only the one comment and its own log file, tolerates
// the stream file and the task comment not existing yet, and goes quiet after
// FAILURES_TOLERATED consecutive API errors.
import { appendFileSync } from 'node:fs'
import { open } from 'node:fs/promises'

const FAILURES_TOLERATED = 3
const PROGRESS_MARKER = '<!-- cortex-issue-agent-progress -->'

const repository = process.env.REPOSITORY ?? ''
const issueNumber = process.env.ISSUE_NUMBER ?? ''
const taskMarker = process.env.TASK_MARKER ?? ''
const streamFile = process.env.STREAM_FILE ?? ''
const logFile = process.env.UPDATER_LOG ?? ''
const api = `https://api.github.com/repos/${repository}`
// Floor, not a default: a sub-30s cadence spends API quota to animate a comment nobody
// is notified about (GitHub notifies no one on an edit).
const intervalMs = Math.max(30, Number(process.env.STATUS_UPDATE_SECONDS) || 90) * 1000
const deadline = Date.now() + (Number(process.env.JOB_TIMEOUT_MINUTES) || 30) * 60000

const started = Date.now()
let commentUrl = ''
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

// The one field that says what a tool call is actually doing, when there is one.
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

// Read only what the agent appended since last tick; a partial last line waits in
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
      try { note(JSON.parse(line)) } catch { /* a malformed line is the agent's problem */ }
    }
  } finally {
    await handle.close()
  }
}

const headers = () => ({
  Authorization: `Bearer ${process.env.GH_TOKEN}`,
  Accept: 'application/vnd.github+json',
  'User-Agent': 'jahia-ai-issue-agent',
  'Content-Type': 'application/json',
})

const request = async (url, options = {}) => {
  const response = await fetch(url, { headers: headers(), signal: AbortSignal.timeout(10000), ...options })
  if (!response.ok) throw new Error(`${options.method ?? 'GET'} ${url}: HTTP ${response.status}`)
  return response.json()
}

// The agent opens its task comment at its own pace; until then there is nothing to update.
async function findTaskComment() {
  for (let page = 1; page <= 10; page += 1) {
    const batch = await request(`${api}/issues/${issueNumber}/comments?per_page=100&page=${page}`)
    const match = batch.find((comment) => (comment.body ?? '').includes(taskMarker))
    if (match) return match.url
    if (batch.length < 100) return ''
  }
  return ''
}

async function updateComment() {
  if (!commentUrl) {
    commentUrl = await findTaskComment()
    if (!commentUrl) {
      log('no task comment carries the marker yet')
      return
    }
    log(`found the task comment: ${commentUrl}`)
  }
  const deniedText = denied ? ` (${denied} denied)` : ''
  // Absolute times, because they are what tells a hung run from a quiet one: a comment
  // whose "next update" time is well past means the run is hanging (or this updater died —
  // the job log then says so).
  const utc = (date) => date.toISOString().slice(0, 19).replace('T', ' ')
  const now = new Date()
  const next = new Date(now.getTime() + intervalMs)
  let stats = `⏱ ${elapsed()} elapsed · ${tools} tool calls${deniedText}`
  if (last) stats += `\nLast activity: \`${last}\``
  stats += `\nUpdated ${utc(now)} UTC · next update expected by ${utc(next).slice(11)} UTC`
  // Re-fetch on every tick: the agent edits this comment in place, so a body kept from the
  // last tick would overwrite the agent's own progress. Only the tail below the progress
  // marker belongs to this sidecar.
  const current = await request(commentUrl)
  const base = (current.body ?? '').split(PROGRESS_MARKER)[0].trimEnd()
  await request(commentUrl, {
    method: 'PATCH',
    body: JSON.stringify({ body: `${base}\n\n${PROGRESS_MARKER}\n${stats}` }),
  })
  log(`updated: ${tools} tool calls${deniedText}`)
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

if (!repository || !issueNumber || !taskMarker || !process.env.GH_TOKEN || !streamFile) {
  log('missing REPOSITORY/ISSUE_NUMBER/TASK_MARKER/GH_TOKEN/STREAM_FILE — nothing to do')
  process.exit(0)
}
log(`started: every ${intervalMs / 1000}s on ${repository}#${issueNumber}`)
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
