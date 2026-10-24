import { formatDuration } from './formatDuration'
import { STATE_MARKER_CLOSE, STATE_MARKER_OPEN, STATUS_MARKER } from './markers'
import type { AgentState } from './types'

// The whole status comment body: identity marker, machine state (one line of JSON inside
// an HTML comment), then the short human-readable summary derived from that state. The
// visible section is always regenerated — nothing is ever hand-appended to it.
export const renderStateBlock = (state: AgentState): string => {
  const json = JSON.stringify(state)
  if (json.includes(STATE_MARKER_CLOSE)) {
    // Only our own fields enter the state, so this is near-impossible — but a "-->"
    // smuggled through a URL would truncate the HTML comment and corrupt every later parse.
    throw new Error('state serialization contains "-->" and would break the comment')
  }
  const sessionCount = state.sessions.length
  const latest = state.sessions[sessionCount - 1]
  const statusLine =
    state.lock && latest
      ? `Session #${String(sessionCount)} in progress — [run](${state.lock.runUrl})`
      : latest?.outcome
        ? `Session #${String(sessionCount)} finished (${latest.outcome}) — ${formatDuration(latest.seconds ?? 0)}`
        : 'Idle — no agent session in flight'
  // "2026-10-23T14:00:00.000Z" -> "2026-10-23 14:00" (the seconds say nothing a reader needs)
  const instant = (iso: string): string => iso.slice(0, 16).replace('T', ' ')
  const inFlight = (runId: number): boolean => state.lock?.runId === runId
  const rows = state.sessions.map((session, index) => {
    const duration = session.seconds === null ? '—' : formatDuration(session.seconds)
    const outcome = session.outcome ?? (inFlight(session.runId) ? 'in progress' : 'unknown')
    return `| [#${String(index + 1)}](${session.runUrl}) | ${session.trigger} | ${instant(session.startedAt)} | ${duration} | ${outcome} |`
  })
  const lines = [
    STATUS_MARKER,
    STATE_MARKER_OPEN,
    json,
    STATE_MARKER_CLOSE,
    '',
    '🤖 **AI Issue Agent — overall status**',
    '',
    statusLine,
  ]
  if (rows.length > 0) {
    lines.push(
      '',
      '| Session | Trigger | Started (UTC) | Duration | Outcome |',
      '|---|---|---|---|---|',
      ...rows,
    )
  }
  lines.push(
    '',
    `**Budget used**: ${formatDuration(state.ledgerSeconds)} of ${formatDuration(state.budgetSeconds)} (cumulative, across all sessions)`,
  )
  if (state.budgetExhaustedNotedAt !== null) {
    lines.push(
      '',
      '⛔ The agent budget for this issue is exhausted — no further sessions will start.',
    )
  }
  lines.push(
    '',
    '_This comment tracks all agent activity on this issue; the agent runtime keeps it up to date._',
  )
  return lines.join('\n')
}
